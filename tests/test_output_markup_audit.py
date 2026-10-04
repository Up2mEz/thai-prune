from labbs2026.output_diagnostics.markup import audit, summarize


def test_audit_counts_markup_and_thai_loss():
    raw = ("# หัวข้อ\n* รายการ\n**ตัวหนา**\n| ก | ข |\n```\nโค้ด\n```\n$x^2$ &amp;\n"
           "<figure><table><tr><td>ตาราง</td></tr></table></figure><figure>ภาพ</figure>")
    a = audit(raw)
    assert a["headings"] == 1 and a["list_markers"] == 1 and a["bold"] == 2
    assert a["pipe_rows"] == 1 and a["code_fences"] == 2 and a["latex"] == 1 and a["entities"] == 1
    assert a["figure_blocks"] == 2 and a["tags"]["figure"] == 4 and a["tags"]["td"] == 2
    # T1 drops both figures (8 Thai chars); the structure-aware rule keeps the table text
    assert a["thai_lost_t1"] == len("ตาราง") + len("ภาพ")
    assert a["thai_lost_structural"] == len("ภาพ")


def test_summarize_shares():
    s = summarize(["ข้อความธรรมดา", "<figure>ข้อความในภาพ</figure>"])
    assert s["outputs"] == 2 and s["with_any_tag"] == 1 and s["with_figure"] == 1
    assert s["outputs_losing_over_10pct_thai_t1"] == 1
    assert 0 < s["thai_lost_t1_share"] < 1
