"""P-BAND: line extraction, overlap de-duplication, the registered label, and assembly."""

from __future__ import annotations

import pytest

from labbs2026.thai_marks import p_band_analysis as pb

L1 = "ผู้ปกครองต้องพาเด็กไปรับวัคซีนตามกำหนดเวลาที่โรงพยาบาลแจ้งไว้"
L2 = "เจ้าหน้าที่สาธารณสุขจะออกเยี่ยมบ้านทุกสัปดาห์เพื่อติดตามผล"
L3 = "คณะกรรมการประชุมกันเพื่อพิจารณางบประมาณประจำปีอย่างละเอียด"
L4 = "แผนภูมิแสดงสัดส่วนผู้ป่วยนอกที่เข้ารับบริการในแต่ละภูมิภาค"
L5 = "โรงเรียนจัดกิจกรรมวันเด็กแห่งชาติให้นักเรียนทุกระดับชั้นเข้าร่วม"
L6 = "สำนักงานเขตประกาศผลการสอบคัดเลือกเข้ารับราชการตามกำหนดการเดิม"


def test_output_lines_drop_figure_blocks_even_when_they_span_lines() -> None:
    raw = f"{L1}\n<figure>\nอธิบายภาพ\n{L2} inside\n</figure>\n{L3}\n"
    assert pb.output_lines(raw) == [L1, L3]
    unclosed = f"{L1}\n<figure>\n{L2}"
    assert pb.output_lines(unclosed) == [L1]


def test_output_lines_strip_markdown_and_blank_lines() -> None:
    assert pb.output_lines(f"\n# {L1}\n\n**{L2}**\n") == [L1, L2]


def test_dedup_removes_a_line_in_the_overlap_but_keeps_a_repeat_elsewhere() -> None:
    # band 0 ends with L2 (its tail); band 1 starts with L2 again (the overlap) and later repeats L1
    band0 = "\n".join([L1, L3, L4, L5, L6, L2])
    band1 = "\n".join([L2, L3.replace("ประจำปี", "ประจำปี "), L5, L6, L4, L1])
    # L2 is in band 1's head and band 0's tail: dropped. L1 is in band 1's *last* line (not its head):
    # kept although band 0 has it, because it is not in the overlap zone.
    text = pb.dedup_text([band0, band1])
    lines = text.split("\n")
    assert lines.count(L2) == 1
    assert lines.count(L1) == 2


def test_dedup_leaves_a_clean_page_unchanged_and_concat_keeps_duplicates() -> None:
    band0, band1 = f"{L1}\n{L2}", f"{L3}\n{L4}"
    assert pb.dedup_text([band0, band1]) == pb.concat_text([band0, band1])
    overlapped = [f"{L1}\n{L2}\n{L3}", f"{L3}\n{L4}\n{L5}"]
    assert pb.concat_text(overlapped).count(L3) == 2
    assert pb.dedup_text(overlapped).count(L3) == 1


def test_short_lines_are_never_deduplicated() -> None:
    bands = [f"{L1}\n{L2}\n0.5", f"0.5\n{L3}\n{L4}"]
    assert pb.dedup_text(bands).split("\n").count("0.5") == 2


def test_the_label_follows_the_registered_thresholds() -> None:
    assert pb.reading(0.003, 0.0005, 0.006, -0.001) == "helps"
    assert pb.reading(0.003, -0.001, 0.007, 0.0) == "not_distinguishable"   # interval spans 0
    assert pb.reading(0.001, 0.0002, 0.002, 0.0) == "not_distinguishable"   # too small
    assert pb.reading(0.003, 0.0005, 0.006, -0.01) == "not_distinguishable"  # precision loss over 0.5 points
    assert pb.reading(-0.003, -0.006, -0.0005, 0.0) == "hurts"
    assert pb.reading(-0.003, -0.006, 0.001, 0.0) == "not_distinguishable"


def _page(page_id, reference, whole, bands, **extra):
    base = {"id": page_id, "category": "Test", "reference": reference, "whole_raw": whole,
            "band_raws": bands, "whole_tokens": 100, "whole_seconds": 10.0, "whole_looped": False,
            "band_tokens": 160, "band_seconds": 16.0, "band_looped": 0}
    return {**base, **extra}


def test_analyze_scores_variants_and_costs_deterministically() -> None:
    reference = "\n".join([L1, L2, L3, L4])
    # the whole-page read misses L4 entirely; the bands read it (and repeat L3 in the overlap)
    pages = [_page(f"P{i}", reference, "\n".join([L1, L2, L3]),
                   [f"{L1}\n{L2}\n{L3}", f"{L3}\n{L4}", "\n"]) for i in range(8)]
    out = pb.analyze(pages)
    assert out["pages"] == 8
    whole, concat, dedup = (out["micro"][v] for v in pb.VARIANTS)
    assert dedup["recall"] > whole["recall"]
    assert concat["precision"] < dedup["precision"]  # the overlap duplicate is charged
    assert out["contrasts_vs_whole"]["bands_dedup"]["delta"] > 0
    assert out["cost"]["generated_tokens"]["ratio"] == pytest.approx(1.6)
    assert out["pages_better_equal_worse"] == [8, 0, 0]
    assert pb.analyze(pages) == out


def test_assemble_pages_requires_every_band_of_every_page() -> None:
    whole = {"A": {"category": "c", "reference": "R", "raw_output": "w", "generated_tokens": 5,
                   "seconds_generate": 1.0, "reached_max_new_tokens": False}}

    def rec(tile):
        return {"id": "A", "tile": tile, "raw_output": f"b{tile}", "generated_tokens": 2,
                "seconds_generate": 0.5, "reached_max_new_tokens": tile == 2}

    reads = [rec(2), rec(0), rec(1)]
    (page,) = pb.assemble_pages(whole, reads, ["A"])
    assert page["band_raws"] == ["b0", "b1", "b2"] and page["band_looped"] == 1
    assert page["band_tokens"] == 6
    with pytest.raises(ValueError, match="bands"):
        pb.assemble_pages(whole, reads[:2], ["A"])
    with pytest.raises(ValueError, match="duplicate"):
        pb.assemble_pages(whole, reads + [rec(0)], ["A"])
    with pytest.raises(ValueError, match="outside"):
        pb.assemble_pages(whole, reads + [{**rec(0), "id": "Z"}], ["A"])


def test_subgroups_are_reported_per_variant_without_a_label() -> None:
    reference = "\n".join([L1, L2, L3, L4])
    pages = [_page(f"P{i}", reference, "\n".join([L1, L2, L3]), [f"{L1}\n{L2}\n{L3}", f"{L3}\n{L4}", "\n"])
             for i in range(4)]
    out = pb.analyze(pages, subgroups={"left": {"P0", "P1"}, "right": {"P2", "P3"}, "none": {"X"}})
    assert set(out["subgroups"]) == {"left", "right"}
    assert out["subgroups"]["left"]["pages"] == 2
    assert out["subgroups"]["left"]["bands_dedup"]["recall"] > out["subgroups"]["left"]["whole"]["recall"]
