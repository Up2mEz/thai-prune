"""P-ZOOM page selection: which pages, which absent lines, which control lines."""

from __future__ import annotations

from labbs2026.thai_marks.attribution import reference_lines, whole_line_causes
from labbs2026.thai_marks.p_zoom import has_mark, mark_count, select_pages

KEPT = "ผู้ปกครองต้องพาเด็กไปรับวัคซีนตามกำหนดเวลาที่โรงพยาบาลแจ้งไว้"
KEPT2 = "เจ้าหน้าที่สาธารณสุขจะออกเยี่ยมบ้านทุกสัปดาห์เพื่อติดตามผล"
KEPT3 = "คณะกรรมการประชุมกันเพื่อพิจารณางบประมาณประจำปีอย่างละเอียด"
LOST = "แผนภูมิแสดงสัดส่วนผู้ป่วยนอกที่เข้ารับบริการในแต่ละภูมิภาค"
NO_MARK = "ABCDEFGHIJKL MNOPQRST"


def _record(reference_lines_: list[str], output_lines: list[str], *, id_="P1",
            task="Full-page OCR", prompt="BENCHMARK_QUESTION") -> dict:
    return {"id": id_, "task": task, "prompt_kind": prompt,
            "reference": "\n".join(reference_lines_), "raw_output": "\n".join(output_lines)}


def test_mark_helpers() -> None:
    assert has_mark("ที่") and not has_mark("ABC")
    assert mark_count("ที่นี่") == 4  # two upper vowels, two tone marks


def test_selects_a_page_whose_marked_line_is_absent() -> None:
    record = _record([KEPT, LOST, KEPT2], [KEPT, KEPT2])
    (page,) = select_pages([record], control_per_page=1)
    lines = reference_lines(record["reference"])
    assert page["id"] == "P1"
    assert [lines[i] for i in page["absent_lines"]] == [LOST]
    assert page["absent_marks"] == mark_count(LOST) > 0
    assert page["control_lines"] and set(page["control_lines"]).isdisjoint(page["absent_lines"])


def test_a_page_with_every_line_kept_or_no_marked_absence_is_not_selected() -> None:
    assert select_pages([_record([KEPT, KEPT2], [KEPT, KEPT2])]) == []
    # the absent line carries no Thai mark: out of scope for a mark probe
    record = _record([KEPT, NO_MARK, KEPT2], [KEPT, KEPT2])
    assert "line_missing" in whole_line_causes(record["reference"], record["raw_output"])
    assert select_pages([record]) == []


def test_other_tasks_and_prompts_are_ignored() -> None:
    absent = ([KEPT, LOST, KEPT2], [KEPT, KEPT2])
    assert select_pages([_record(*absent, task="Text recognition")]) == []
    assert select_pages([_record(*absent, prompt="TYPHOON_CARD")]) == []


def test_control_lines_are_seeded_and_independent_of_record_order() -> None:
    reference = [KEPT, LOST, KEPT2, KEPT3]
    output = [KEPT, KEPT2, KEPT3]
    records = [_record(reference, output, id_=name) for name in ("B2", "A1")]
    first = select_pages(records, control_per_page=2)
    again = select_pages(list(reversed(records)), control_per_page=2)
    assert first == again and [p["id"] for p in first] == ["A1", "B2"]
    assert all(len(p["control_lines"]) == 2 for p in first)
    lines = reference_lines(records[0]["reference"])
    assert all(lines[i] in (KEPT, KEPT2, KEPT3) for i in first[0]["control_lines"])


def test_a_page_with_too_few_kept_lines_gets_fewer_controls() -> None:
    (page,) = select_pages([_record([KEPT, LOST], [KEPT])], control_per_page=2)
    assert len(page["control_lines"]) == 1
