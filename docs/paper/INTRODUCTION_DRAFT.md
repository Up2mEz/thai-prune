# Introduction — draft v1 (EN + TH)

**Status:** first draft, following `THAI_MARKS_SHORT_PAPER_OUTLINE.md` §1.

**Rules for this draft:**
- Every result sentence stays inside `docs/CLAIMS.md` ("Thai-marks phase").
- `[CITE: …]` marks a citation still to be checked with `ref-verify`. No
  reference was added from memory.
- `[W1]`–`[W4]` mark numbers that wait for PELY334's runs.
- `[N]` is the final number of models.

---

## English

Thai is written with a consonant line and marks stacked above and below it:
upper and lower vowels, and four tone marks. A single mark can change a word's
meaning and its pronunciation, so a transcription that drops or swaps one is
wrong for a reader even when almost every character is right. Yet OCR
evaluation of Thai documents is usually summarized by character error rate
or benchmark-level scores [CITE: ThaiOCRBench, arXiv:2511.04479]. These
numbers do not say whether the marks are the problem. Character error rate
also charges a model for reading a page's columns in a different order than
the reference.

Open vision-language models (VLMs) trained for Thai OCR are now available
[CITE: Typhoon OCR 1.5; Pathumma-llm-vision 3.0; wayu-paxa-ocr-zero]. They
raise a practical question: when such a model gets a Thai mark wrong, what
went wrong? One possibility is that the visual evidence for a small mark is
lost or too weak. Another is that the model's language prior overrides that
evidence. A third is that the mark is never read at all, because the model
skipped the line, failed to find the text, or fell into a repetition loop.
These causes call for different remedies. If the image is the problem, one
re-reads or zooms. If the prior is the problem, one subtracts the prior, as
contrastive decoding methods do [CITE: VCD; M3ID]. If the text is never
read, it needs a decoding or localization fix.

We study this question on ThaiOCRBench [CITE: ThaiOCRBench] with [N] open
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
   - [W1/W3: the same diagnosis across the other models.]
3. **What training-free decoding does to marks.**
   - Stopping generation at a detected loop leaves every non-looping output
     unchanged and raises mark F1. [W4: confirmatory numbers.]
   - The repetition penalty shipped with an OCR package lowers mark F1 on
     non-looping pages and raises tone errors.
   - Decoding that subtracts the language prior removes correct tone marks.

Taken together, the remaining mark errors of a strong Thai OCR model sit
upstream of the mark itself. The useful levers are in decoding and in
finding text, not in seeing a tone mark more sharply.

---

## ภาษาไทย

อักษรไทยเขียนพยัญชนะเป็นแนวหลัก แล้วมีเครื่องหมายซ้อนอยู่ด้านบนและด้านล่าง ได้แก่ สระบน สระล่าง และวรรณยุกต์สี่รูป mark เพียงตัวเดียวเปลี่ยนความหมายและเสียงของคำได้ การถอดข้อความที่ทำ mark หายหรือสลับผิดตัวจึงถือว่าผิดสำหรับผู้อ่าน แม้ตัวอักษรเกือบทั้งหมดจะถูก แต่การประเมิน OCR เอกสารไทยมักสรุปด้วย character error rate หรือคะแนนรวมของ benchmark [CITE: ThaiOCRBench, arXiv:2511.04479] ตัวเลขเหล่านี้ไม่ได้บอกว่าปัญหาอยู่ที่ mark หรือไม่ และ character error rate ยังลงโทษโมเดลที่อ่านคอลัมน์ของหน้าในลำดับที่ต่างจากเฉลยด้วย

ปัจจุบันมี vision-language model (VLM) แบบเปิดที่ train มาเพื่อ OCR ภาษาไทยแล้ว [CITE: Typhoon OCR 1.5; Pathumma-llm-vision 3.0; wayu-paxa-ocr-zero] จึงเกิดคำถามเชิงปฏิบัติว่า เมื่อโมเดลแบบนี้ทำ mark ภาษาไทยผิด ผิดเพราะอะไร มีความเป็นไปได้สามทาง

1. หลักฐานในภาพของ mark ที่เล็กมากหายไปหรืออ่อนเกินไป
2. ความรู้ภาษาของโมเดลทับหลักฐานในภาพ
3. โมเดลไม่ได้อ่าน mark นั้นเลย เพราะข้ามบรรทัด หาข้อความไม่เจอ หรือติดการวนซ้ำ

สาเหตุแต่ละทางต้องแก้ต่างกัน ถ้าปัญหาอยู่ที่ภาพ ต้องอ่านซ้ำหรือขยายภาพ ถ้าปัญหาอยู่ที่ความรู้ภาษา ต้องหักความรู้ภาษาออกแบบที่ contrastive decoding ทำ [CITE: VCD; M3ID] ถ้าข้อความไม่ถูกอ่านเลย ต้องแก้ที่วิธี decode หรือการหาตำแหน่งข้อความ

เราศึกษาคำถามนี้บน ThaiOCRBench [CITE: ThaiOCRBench] กับโมเดลแบบเปิด [N] ตัว ในงานอ่านทั้งหน้าและงานอ่านข้อความสั้น โดยมีส่วนร่วม (contributions) สามข้อ

1. **ตัวชี้วัด mark ที่ไม่ลงโทษลำดับการอ่าน**
   - ให้คะแนนสระบน สระล่าง และวรรณยุกต์ทีละบรรทัดของเฉลย ไม่ว่าบรรทัดนั้นจะไปอยู่ตรงไหนของ output
   - ยังหักคะแนนข้อความที่เขียนเกิน และไม่ให้คะแนนกับข้อความที่ซ้ำจากการวนซ้ำ
   - บนโมเดลที่ได้คะแนนสูงสุดคือ Typhoon OCR 1.5 2B การลงโทษลำดับการอ่านอย่างเดียวทำให้คะแนน mark F1 ของงานอ่านทั้งหน้าลดจาก 94.9 เหลือ 93.1
2. **การวินิจฉัยว่า mark หายไปตรงไหน**
   - บน Typhoon ในตำแหน่งที่อ่านพยัญชนะถูก วรรณยุกต์ผิดเพียง 0.65%
   - เมื่อให้คำก่อนหน้าที่ถูก โมเดลเลือกวรรณยุกต์ถูก 98.8% แม้ไม่เห็นภาพ
   - mark ที่หายส่วนใหญ่ไม่ได้ถูกอ่านเลย ได้แก่ หายทั้งบรรทัด หาข้อความไม่เจอ หรือ output ถูกการวนซ้ำกินไป ส่วนการอ่าน mark ผิดในข้อความที่อ่านแล้วเป็นส่วนที่น้อยกว่า
   - [W1/W3: ผลวินิจฉัยเดียวกันกับโมเดลอื่น]
3. **ผลของ training-free decoding ต่อ mark**
   - การหยุด generate เมื่อเจอการวนซ้ำไม่เปลี่ยน output ที่ไม่วนซ้ำเลย และเพิ่มคะแนน mark [W4: ตัวเลขจากการทดลองยืนยัน]
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
