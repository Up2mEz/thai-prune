# Introduction — draft v1 (EN + TH)

**Status:** first draft, following `THAI_MARKS_SHORT_PAPER_OUTLINE.md` §1.

**Rules for this draft:**
- Every result sentence stays inside `docs/CLAIMS.md` ("Thai-marks phase").
- Citation keys point to `references.bib`, verified 2026-10-11 (see
  `RELATED_WORK_DRAFT.md`).
- `[W1]`–`[W4]` marked numbers that waited for PELY334's runs; all four are now in (2026-10-15).
- `[N]` is the final number of models.

---

## English

Thai is written with a consonant line and marks stacked above and below it:
upper and lower vowels, and four tone marks. A single mark can change a word's
meaning and its pronunciation, so a transcription that drops or swaps one is
wrong for a reader even when almost every character is right. Yet Thai OCR
is scored with whole-text measures: n-gram overlap and normalized edit
distance in ThaiOCRBench [nonesung2025thaiocrbench], and character error
rate elsewhere. These numbers do not say whether the marks are the problem,
and sequence-level scores also charge a model for reading a page's columns
in a different order than the reference.

Open vision-language models (VLMs) trained for Thai OCR are now available
[nonesung2026typhoonocr; nectec2026pathumma; pipatanakul2026synthetic]. They
raise a practical question: when such a model gets a Thai mark wrong, what
went wrong? One possibility is that the visual evidence for a small mark is
lost or too weak. Another is that the model's language prior overrides that
evidence. A third is that the mark is never read at all, because the model
skipped the line, failed to find the text, or fell into a repetition loop.
These causes call for different remedies. If the image is the problem, one
re-reads or zooms. If the prior is the problem, one subtracts the prior, as
contrastive decoding methods do [leng2024vcd; favero2024m3id]. If the text is never
read, it needs a decoding or localization fix.

We study this question on ThaiOCRBench [nonesung2025thaiocrbench] with [N] open
models, using full-page OCR and text recognition. We make three
contributions.

1. **A mark metric that does not charge reading order.** It scores upper
   vowels, lower vowels and tone marks per reference line, wherever the line
   appears in the output. It charges surplus text, and it gives no credit to
   the copies of a repetition loop. On the best-scoring model, Typhoon OCR
   1.5 2B, charging reading order alone lowers full-page mark F1 from 94.9
   to 93.1.
2. **A diagnosis of where marks are lost.**
   - On Typhoon, when the base consonant is read correctly, the tone mark is
     wrong only 0.65% of the time.
   - Given the correct preceding text, the tone mark is chosen correctly
     98.8% of the time even without the image.
   - The marks that are lost are mostly never read: whole lines absent, text
     not found, or output consumed by loops. Wrong marks inside read text are
     a smaller share.
   - On the locked split, absent text costs 4.7 to 15.8 times more marks than a misread mark after a correct consonant, in all eight models. One exception to the wording: Qwen3-VL-4B also misreads about one tone mark in eleven while it writes the page (W3), so "mostly absent" is right and "almost never misread" is not.
3. **What training-free decoding does to marks.**
   - Stopping generation at a detected loop raised mark F1 in 12 of the 13 registered cells on the locked split, and changed 1 of 2,400 outputs that had ended on their own. The cell that did not pass (Pathumma, full pages) rarely loops.
   - The repetition penalty shipped with an OCR package lowers mark F1 on
     non-looping pages and raises tone errors.
   - Decoding that subtracts the language prior removes correct tone marks.

Taken together, the remaining mark errors of a strong Thai OCR model sit
upstream of the mark itself. The useful levers are in decoding and in
finding text, not in seeing a tone mark more sharply.

---

## ภาษาไทย

อักษรไทยเขียนพยัญชนะเป็นแนวหลัก แล้วมีเครื่องหมายซ้อนอยู่ด้านบนและด้านล่าง ได้แก่ สระบน สระล่าง และวรรณยุกต์สี่รูป mark เพียงตัวเดียวเปลี่ยนความหมายและเสียงของคำได้ การถอดข้อความที่ทำ mark หายหรือสลับผิดตัวจึงถือว่าผิดสำหรับผู้อ่าน แม้ตัวอักษรเกือบทั้งหมดจะถูก แต่ OCR ภาษาไทยถูกให้คะแนนด้วยตัวชี้วัดระดับข้อความทั้งก้อน ได้แก่ ความทับซ้อนของ n-gram และ normalized edit distance ใน ThaiOCRBench [nonesung2025thaiocrbench] และ character error rate ในงานอื่น ตัวเลขเหล่านี้ไม่ได้บอกว่าปัญหาอยู่ที่ mark หรือไม่ และคะแนนแบบเทียบทั้งลำดับยังลงโทษโมเดลที่อ่านคอลัมน์ของหน้าในลำดับที่ต่างจากเฉลยด้วย

ปัจจุบันมี vision-language model (VLM) แบบเปิดที่ train มาเพื่อ OCR ภาษาไทยแล้ว [nonesung2026typhoonocr; nectec2026pathumma; pipatanakul2026synthetic] จึงเกิดคำถามเชิงปฏิบัติว่า เมื่อโมเดลแบบนี้ทำ mark ภาษาไทยผิด ผิดเพราะอะไร มีความเป็นไปได้สามทาง

1. หลักฐานในภาพของ mark ที่เล็กมากหายไปหรืออ่อนเกินไป
2. ความรู้ภาษาของโมเดลทับหลักฐานในภาพ
3. โมเดลไม่ได้อ่าน mark นั้นเลย เพราะข้ามบรรทัด หาข้อความไม่เจอ หรือติดการวนซ้ำ

สาเหตุแต่ละทางต้องแก้ต่างกัน ถ้าปัญหาอยู่ที่ภาพ ต้องอ่านซ้ำหรือขยายภาพ ถ้าปัญหาอยู่ที่ความรู้ภาษา ต้องหักความรู้ภาษาออกแบบที่ contrastive decoding ทำ [leng2024vcd; favero2024m3id] ถ้าข้อความไม่ถูกอ่านเลย ต้องแก้ที่วิธี decode หรือการหาตำแหน่งข้อความ

เราศึกษาคำถามนี้บน ThaiOCRBench [nonesung2025thaiocrbench] กับโมเดลแบบเปิด [N] ตัว ในงานอ่านทั้งหน้าและงานอ่านข้อความสั้น โดยมีส่วนร่วม (contributions) สามข้อ

1. **ตัวชี้วัด mark ที่ไม่ลงโทษลำดับการอ่าน**
   - ให้คะแนนสระบน สระล่าง และวรรณยุกต์ทีละบรรทัดของเฉลย ไม่ว่าบรรทัดนั้นจะไปอยู่ตรงไหนของ output
   - ยังหักคะแนนข้อความที่เขียนเกิน และไม่ให้คะแนนกับข้อความที่ซ้ำจากการวนซ้ำ
   - บนโมเดลที่ได้คะแนนสูงสุดคือ Typhoon OCR 1.5 2B การลงโทษลำดับการอ่านอย่างเดียวทำให้คะแนน mark F1 ของงานอ่านทั้งหน้าลดจาก 94.9 เหลือ 93.1
2. **การวินิจฉัยว่า mark หายไปตรงไหน**
   - บน Typhoon ในตำแหน่งที่อ่านพยัญชนะถูก วรรณยุกต์ผิดเพียง 0.65%
   - เมื่อให้คำก่อนหน้าที่ถูก โมเดลเลือกวรรณยุกต์ถูก 98.8% แม้ไม่เห็นภาพ
   - mark ที่หายส่วนใหญ่ไม่ได้ถูกอ่านเลย ได้แก่ หายทั้งบรรทัด หาข้อความไม่เจอ หรือ output ถูกการวนซ้ำกินไป ส่วนการอ่าน mark ผิดในข้อความที่อ่านแล้วเป็นส่วนที่น้อยกว่า
   - บนชุด locked ข้อความที่หายทำให้เสีย mark มากกว่าการอ่าน mark ผิดหลังอ่านพยัญชนะถูก 4.7 ถึง 15.8 เท่า ในทั้งแปดโมเดล ข้อยกเว้นของถ้อยคำคือ Qwen3-VL-4B ซึ่งอ่านวรรณยุกต์ผิดราว 1 ใน 11 ตอนเขียนหน้าเองด้วย (W3) จึงใช้คำว่า "ส่วนใหญ่หายไปจาก output" ได้ แต่ใช้ "แทบไม่เคยอ่านผิด" ไม่ได้
3. **ผลของ training-free decoding ต่อ mark**
   - การหยุด generate เมื่อเจอการวนซ้ำเพิ่ม mark F1 ใน 12 จาก 13 เซลล์ที่ลงทะเบียนไว้บนชุด locked และเปลี่ยน output ที่จบเองเพียง 1 จาก 2,400 รายการ เซลล์ที่ไม่ผ่าน (Pathumma หน้าเต็ม) วนซ้ำน้อย
   - repetition penalty ที่ติดมากับ package ของ OCR ทำให้คะแนน mark ของหน้าที่ไม่วนซ้ำลดลง และวรรณยุกต์ผิดมากขึ้น
   - decoding ที่หักความรู้ภาษาออกทำให้วรรณยุกต์ที่ถูกอยู่แล้วหายไป

เมื่อรวมกัน ความผิดของ mark ที่ยังเหลือในโมเดล Thai OCR ที่เก่งอยู่แล้ว เกิดขึ้นก่อนถึงตัว mark จุดที่แก้ได้จริงจึงอยู่ที่วิธี decode และการหาข้อความให้เจอ ไม่ใช่การทำให้มองวรรณยุกต์ชัดขึ้น

---

## Notes for the author (ไม่ใส่ในเปเปอร์)

- **"best-scoring model".** This is only true among the models we measure.
  If W2 finds Pathumma 3.0 above Typhoon, change contribution 1's example
  model or say "a strong model". Do not write "state of the art".
- **98.8% without the image.** It comes from an in-context forced choice, not
  free generation. Say this in §4.2.
- **"mostly never read".** On Typhoon, Full-page BQ, about 3.0% of marks are
  absent and 1.5% misread. Keep "mostly" until W1 shows the same pattern on
  the other models; otherwise narrow it to Typhoon.
- **Repetition penalty and prior removal.** Both rest on Typhoon (T5) plus
  R1/R2's 24 items. In the paper, call R1/R2 "M3ID-form".
- **Last paragraph.** It is a conclusion-style sentence. Soften it to "for
  the models studied" if W1–W3 come back mixed.
