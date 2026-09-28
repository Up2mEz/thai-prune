from labbs2026.output_diagnostics.structure import deloop, loop_period, structural_normalize
from labbs2026.output_diagnostics.taxonomy import bag_overlap, diagnose
from labbs2026.thai_marks.normalize import normalize_text


def test_table_in_figure_is_kept_but_picture_description_dropped():
    raw = ("<figure><table><caption>หัวเรื่อง</caption><tr><td>ชื่อ</td><td>ค่า</td></tr></table></figure>"
           "<figure>ภาพคนยืน</figure>ข้อความ")
    assert normalize_text(raw) == "ข้อความ"                       # T1: the reading is gone
    assert structural_normalize(raw) == "ชื่อ ค่า ข้อความ"         # table kept, caption and picture dropped


def test_invented_table_tags_are_table_like():
    raw = "<figure><table><row><cell>กระทรวง</cell></row><row><cell>2023</cell></row></table></figure>"
    assert structural_normalize(raw) == "กระทรวง 2023"


def test_list_markers_removed_on_both_sides_but_bold_kept_as_text():
    assert structural_normalize("* หนึ่ง\n- สอง\n+ สาม\n1) สี่\n2. ห้า") == "หนึ่ง สอง สาม สี่ ห้า"
    assert structural_normalize("**ตัวหนา** a*b") == "ตัวหนา a b"
    # an in-text hyphen survives
    assert structural_normalize("พ.ศ. 2563 - 2564") == "พ.ศ. 2563 - 2564"


def test_loop_period_finds_long_period_loop_t1_misses():
    unit = "ภายใต้หัวข้อ ผลสัมฤทธิ์ของงาน มีรายการ 1) ลดเวลา 2) ลดขั้นตอน 3) เพิ่มคุณค่า 4) จัดเก็บ " * 1
    body = "ต้นฉบับ" * 5 + unit * 6 + unit[:40]
    period, start = loop_period(body)
    assert period == len(unit)
    assert deloop(body) == body[: start + period]
    assert loop_period("ไม่มีการวนซ้ำเลย ข้อความปกติ") is None


def test_bag_overlap_is_order_insensitive():
    assert bag_overlap("กขค งจ", "งจ กขค") == (1.0, 1.0)
    r, p = bag_overlap("กข", "กขคง")
    assert r == 1.0 and p == 0.5


def test_diagnose_labels():
    ref = "ต้นเบปด์น้ำ ชื่อวงศ์ APOCYNACEAE"
    assert diagnose(ref, f"<figure><table><tr><td>{ref}</td></tr></table></figure>")["primary_cause"] == "format_loss"
    looped = diagnose("ก ข ค", "ก ข ค " + "วนซ้ำอีกแล้วนะ " * 20)
    assert looped["primary_cause"] == "loop" and looped["cer_t1"] > 10
    assert looped["cer_structural_delooped"] < looped["cer_t1"]
    assert diagnose("หนึ่งสองสามสี่ห้าหก", "หนึ่ง")["primary_cause"] == "omission"
    assert diagnose("แถวแรก แถวสอง แถวสาม", "แถวสาม แถวแรก แถวสอง")["primary_cause"] == "reading_order"
    assert diagnose("ไม้เอก", "ไมเอก")["primary_cause"] == "misread"
    # near-repeats (each copy slightly different) escape an exact loop test but not precision
    ref = "ข้อความหน้าแรกของเอกสาร"
    hyp = ref + " " + " ".join(f"ย่อหน้าซ้ำรอบที่{i} มีรายการยาวมากมาย" for i in range(12))
    assert diagnose(ref, hyp)["primary_cause"] == "overgeneration"
