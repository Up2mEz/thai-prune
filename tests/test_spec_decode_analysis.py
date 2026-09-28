import pytest

from labbs2026.spec_decode.analysis import item_rows, summarize


def _rec(item_id, task, ref_ids, pld_ids, ref_s, pld_s, *, hit=False, text="ข้อความปกติ", warmup=False, margin=None):
    ident = {"PLD5": {}}
    if margin is not None:
        ident["PLD5"]["ref_margin"] = {"margin_logits": margin}
    return {
        "id": item_id, "task": task, "warmup": warmup,
        "ref_extra": {"seconds_to_first_token": 1.0},
        "arms": {
            "REF": {"new_token_ids": ref_ids, "seconds_generate": ref_s, "reached_max_new_tokens": hit,
                    "text": text, "generated_tokens": len(ref_ids), "target_forwards": len(ref_ids)},
            "PLD5": {"new_token_ids": pld_ids, "seconds_generate": pld_s, "reached_max_new_tokens": hit,
                     "generated_tokens": len(pld_ids), "target_forwards": max(1, len(pld_ids) // 2)},
        },
        "identity": ident,
    }


def test_populations_identity_and_speed():
    # a unit longer than 100 characters: no 20-character substring fits 3 times in 200
    unit = "ย่อหน้าที่ซ้ำกันไปเรื่อย ๆ มีหัวข้อ ผลสัมฤทธิ์ของงานหลังการปรับปรุง รายการที่หนึ่ง ลดเวลา รายการที่สอง ลดขั้นตอน รายการที่สาม เพิ่มคุณค่า "
    loop_text = "ต้นฉบับ " + unit * 5
    records = [
        _rec("w", "A", [1, 2], [1, 2], 2.0, 1.0, warmup=True),
        _rec("a", "A", [1, 2, 3, 4], [1, 2, 3, 4], 4.0, 2.0),                      # headline, 2x
        _rec("b", "B", [1, 2, 3, 4], [1, 2, 9, 4], 4.0, 4.0, margin=0.05),         # headline, near tie
        _rec("c", "A", [5] * 10, [5] * 11, 10.0, 1.0, hit=True),                    # degenerate; overshoot only
        _rec("d", "B", [1, 2, 3], [1, 2, 3], 3.0, 1.5, text=loop_text),             # T1 rule misses, loop-aware catches
    ]
    rows = item_rows(records, max_new_tokens=10)
    assert [r["id"] for r in rows] == ["a", "b", "c", "d"]
    assert [r["headline"] for r in rows] == [True, True, False, True]
    assert [r["headline_loop_aware"] for r in rows] == [True, True, False, False]
    assert rows[2]["PLD5"]["identical"]                    # overshoot cut to the budget
    assert rows[1]["PLD5"]["divergence_class"] == "near_tie"
    s = summarize(rows, resamples=200)
    assert s["populations"] == {"all": 4, "headline": 3, "headline_loop_aware": 2, "degenerate": 1}
    assert s["PLD5"]["identity_rate"] == pytest.approx(0.75)
    assert s["PLD5"]["mismatch_classes"] == {"near_tie": 1, "large_margin": 0, "length_only": 0}
    assert s["PLD5"]["headline_loop_aware"]["geomean_speedup"]["estimate"] == pytest.approx((2.0 * 1.0) ** 0.5)
    assert s["PLD5"]["degenerate"]["geomean_speedup"]["estimate"] == pytest.approx(10.0)
