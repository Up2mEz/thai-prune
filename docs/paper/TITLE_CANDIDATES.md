# Title candidates (2026-10-15)

Current title in the sources: **Absent, Not Misread: Where Thai OCR Vision-Language Models Lose Vowel and
Tone Marks**. Nothing was changed; pick one and the four `main_*.tex` files get the same edit.

Constraints from `docs/CLAIMS.md`: no "best" or "state-of-the-art"; nothing about Thai OCR VLMs beyond
the eight models and one benchmark; "not misread" needs care because Qwen3-VL-4B misreads about one tone
mark in eleven while generating (claim 15); the stop is 12 of 13 cells, so avoid "always" or "every".

## Diagnosis first (the main finding)

| # | English | ภาษาไทย | Note |
|---|---|---|---|
| 1 | **Absent, Not Misread: Where Open Thai OCR Models Lose Vowel and Tone Marks** | หายไปจาก output ไม่ใช่อ่านผิด: สระและวรรณยุกต์ใน OCR ภาษาไทยแบบเปิดหายที่ใด | The current title, with "Open" added so it does not read as all Thai OCR VLMs. Short, memorable. "Not Misread" is the strong part. |
| 2 | **Lost Before the Mark Is Reached: Locating Vowel and Tone Mark Errors in Open Thai OCR Models** | สระและวรรณยุกต์หายก่อนจะถึงตัว mark: การระบุตำแหน่งความผิดพลาดในโมเดล OCR ภาษาไทยแบบเปิด | Safer than 1: it says "before the mark", which also fits Qwen3-VL-4B. Longer. |
| 3 | **Mostly Absent, Rarely Misread: ...** (same subtitle as 1) | ส่วนใหญ่หายไป ไม่ค่อยอ่านผิด: ... | Hedged version of 1. "Rarely" is a stretch for Qwen3-VL-4B (about 9%), so use it only if the abstract keeps its caveat. |
| 4 | **Marks Missing from the Output, Not Misread: A Diagnosis of Eight Open Thai OCR Models** | mark ที่ไม่ปรากฏใน output ไม่ใช่ mark ที่อ่านผิด: การวินิจฉัยแปดโมเดล OCR ภาษาไทยแบบเปิด | Most literal about what was measured (absence from the output). States the number of models, so the scope is in the title. |

## Question form

| # | English | ภาษาไทย | Note |
|---|---|---|---|
| 5 | **Are Tone Marks the Weak Point of Open Thai OCR? A Locked-Split Study of Eight Models** | วรรณยุกต์เป็นจุดอ่อนของ OCR ภาษาไทยแบบเปิดจริงหรือ: การศึกษาแปดโมเดลบนชุดข้อมูลที่เปิดอ่านครั้งเดียว | Invites the answer "mostly no". Fits the project rule not to assume tone marks degrade faster. "Locked-Split" signals the confirmatory design to reviewers who know the term. |

## Method and result together

| # | English | ภาษาไทย | Note |
|---|---|---|---|
| 6 | **Why Open Thai OCR Models Lose Marks: Absent Text, Repetition Loops and a Training-Free Stop** | ทำไมโมเดล OCR ภาษาไทยแบบเปิดทำ mark หาย: ข้อความไม่ปรากฏ การวนซ้ำ และการหยุดโดยไม่ต้องฝึกเพิ่ม | Names the fix, so it sets the expectation of a method paper. Our stop is a measured effect of a known idea, so this slightly oversells. |
| 7 | **Order-Free Mark Scoring and Loop Stopping for Thai OCR: Where Vowels and Tone Marks Are Lost** | การให้คะแนน mark แบบไม่สนลำดับและการหยุดเมื่อวนซ้ำใน OCR ภาษาไทย: สระและวรรณยุกต์หายที่ใด | Puts the metric and the stop in front. Weaker hook; use if the venue cares about contributions more than the story. |

## Recommendation

**Candidate 4 or 1.** Candidate 4 is the most defensible against the claims file and gives scope
(eight models) up front. Candidate 1 is the best title if you accept that the abstract carries the
Qwen3-VL-4B caveat. Avoid 6 and 7 unless the paper is repositioned as a method paper, which the project
rules say it is not.
