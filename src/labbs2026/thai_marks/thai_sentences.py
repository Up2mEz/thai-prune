"""Meaningful synthetic Thai text for E5b (`docs/stage0/E5B_MEANINGFUL_TEXT_DRAFT.md`).

Sentences are built from a small hand-written lexicon of phrases (time, subject, verb with its
object, place). Every combination is grammatical and sensible, but the sentences are templated,
not natural prose. A stream of phrases is packed into lines with a space between phrases, the way
Thai text breaks at phrase boundaries. No benchmark text is involved; deterministic given a seed.
"""

from __future__ import annotations

import random

from labbs2026.thai_marks.synthetic_pages import MARGIN_X, PAGE, n_marks

TIMES = ("ทุกเช้า", "ในวันหยุด", "เมื่อวานนี้", "ตอนเย็น", "หลังเลิกงาน", "เมื่อฝนหยุดตก",
         "ก่อนเที่ยง", "ในฤดูหนาว", "เมื่อต้นเดือน", "ทุกวันอาทิตย์")
SUBJECTS = ("คุณครู", "ชาวบ้าน", "แม่ค้า", "คุณหมอ", "พนักงานบริษัท", "นักท่องเที่ยว",
            "ผู้ใหญ่บ้าน", "ชาวประมง", "ช่างไม้", "เพื่อนบ้าน", "นักเรียนชั้นปีที่สอง", "ลุงข้างบ้าน")
PREDICATES = (  # verb with its object
    "ซื้อผักสดและผลไม้", "ขายข้าวสารและน้ำปลา", "อ่านหนังสือพิมพ์ฉบับเช้า", "เขียนจดหมายถึงเพื่อนเก่า",
    "ซ่อมหลังคาบ้านที่รั่ว", "ปลูกต้นไม้ริมคลอง", "ดูแลผู้ป่วยสูงอายุ", "ตรวจเอกสารสำคัญ",
    "ส่งพัสดุไปต่างจังหวัด", "เตรียมอาหารเช้าให้ครอบครัว", "ทำความสะอาดห้องเรียนใหม่", "เก็บผลไม้ในสวน",
    "จัดงานบุญที่วัด", "สอนเด็กเล็กให้อ่านออกเขียนได้", "ขับรถผ่านสี่แยกไฟแดง", "ล้างจานและกวาดพื้นบ้าน",
    "นั่งรอรถเมล์ที่ป้าย", "ช่วยกันยกของขึ้นรถ", "ตัดผ้าเย็บเสื้อใหม่", "นับเงินในตู้เซฟ")
PLACES = ("ที่ตลาดริมน้ำ", "ในโรงเรียนประจำอำเภอ", "ข้างวัดเก่า", "หน้าสถานีรถไฟ", "ใกล้บ้านผู้ใหญ่",
          "ในห้องประชุมใหญ่", "ที่ศาลากลางหมู่บ้าน", "บนเรือลำเล็ก")


def sentence_phrases(rng: random.Random) -> list[str]:
    """One sentence as 3-4 phrases: time, subject, verb phrase, optional place."""
    phrases = [rng.choice(TIMES), rng.choice(SUBJECTS), rng.choice(PREDICATES)]
    if rng.random() < 0.6:
        phrases.append(rng.choice(PLACES))
    return phrases


def compose_sentence_lines(seed: int, count: int, font_px: int, measure) -> list[str]:
    """`count` lines of phrases separated by spaces, filled until `measure` would pass the text width.

    A phrase that does not fit starts the next line; every line holds at least 4 marks.
    """
    rng = random.Random(seed)
    limit = PAGE[0] - 2 * MARGIN_X
    lines: list[str] = []
    pending: list[str] = []
    text = ""
    while len(lines) < count:
        if not pending:
            pending = sentence_phrases(rng)
        candidate = (text + " " + pending[0]).strip()
        if measure(candidate, font_px) > limit:
            if not text:
                raise ValueError(f"phrase {pending[0]!r} is wider than a line at {font_px}px")
            if n_marks(text) >= 4:
                lines.append(text)
            text = ""
            continue
        text = candidate
        pending.pop(0)
    return lines
