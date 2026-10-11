# Related work — draft v1 (EN + TH)

**Status:** first draft, following `THAI_MARKS_SHORT_PAPER_OUTLINE.md` §2.

**Verification:** every citation was checked on 2026-10-11 against the page
listed in `references.bib`. Most supporting quotes came through a fetch
summarizer, so check the wording against the PDF before submission. Two
items were read from raw source: the DeepSeek-OCR and PaddleX code, and CTRL.

---

## English

**Thai OCR with vision-language models.**
- ThaiOCRBench [nonesung2025thaiocrbench] evaluates proprietary and open VLMs
  on Thai document tasks, including full-page OCR and text recognition.
  - It scores them with n-gram overlap and edit-distance measures (BLEU,
    METEOR, F1, normalized Levenshtein; ANLS for text recognition).
  - Its introduction names stacked diacritics as a Thai difficulty, but no
    score isolates the marks.
- Open Thai OCR models have since appeared:
  - Typhoon OCR [nonesung2026typhoonocr], a full fine-tune of Qwen3-VL-2B
    [bai2025qwen3vl] in version 1.5, whose authors list infographics as an
    area for improvement;
  - Pathumma-llm-vision 3.0 [nectec2026pathumma], another Qwen3-VL-2B
    fine-tune;
  - wayu-paxa-ocr-zero [pipatanakul2026synthetic], a fine-tune of
    PaddleOCR-VL [cui2025paddleocrvl] on synthetic Thai pages.
- Each reports aggregate accuracy. **We instead ask where vowel and tone
  marks are lost.**

**Diacritics in OCR.** Diacritic-heavy scripts are known to be hard for OCR.
- Post-OCR correction has been proposed specifically for Vietnamese
  diacritics [do2025reference].
- Arabic OCR evaluations treat diacritized text as a separate condition
  [elsafty2025arabic].
- We know of no work that scores Thai marks separately from reading order
  and surplus text. That is the purpose of our metric.

**Repetition and omission in OCR VLMs.**
- Likelihood-maximizing decoding produces repetitive text [holtzman2020curious],
  and document OCR models degenerate the same way:
  - Nougat reports pages where the model repeats the same sentence and stops
    generation when a logit-variance signal falls [blecher2024nougat];
  - olmOCR retries at a higher temperature [poznanski2025olmocr];
  - the PaddleOCR-VL pipeline truncates repetitive output after decoding
    [paddlex2025truncate];
  - DeepSeek-OCR's released code bans repeated n-grams within a window
    [deepseekocr2025code, wei2025deepseekocr].
- CC-OCR measures repetition as a form of OCR hallucination [yang2025ccocr].
- These works treat repetition as a failure to detect or avoid. **We measure
  what each remedy costs the marks on pages that do not loop.** The
  repetition penalty of CTRL [keskar2019ctrl], shipped as a default in some
  OCR packages, is among them.

**Language priors and training-free decoding.**
- Contrastive decoding methods reduce hallucination in VLMs by
  down-weighting what the model would predict without, or with degraded,
  visual input: VCD [leng2024vcd], M3ID [favero2024m3id], PAI [liu2024pai].
- They assume the language prior is the problem. For Thai tone marks we find
  the prior is usually right, so subtracting it removes correct marks.
- **Naming:** our variants are reimplementations, called "M3ID-form" and
  "PAI-style" (`docs/CLAIMS.md`).
- Speculative decoding [leviathan2023speculative], here with prompt lookup
  drafts [saxena2023pld], speeds up greedy decoding without changing its
  output in exact arithmetic. We use it for the speed side of our
  training-free setting.

---

## ภาษาไทย

**OCR ภาษาไทยด้วย vision-language model**
- ThaiOCRBench [nonesung2025thaiocrbench] ประเมิน VLM ทั้งแบบปิดและแบบเปิดบนงานเอกสารภาษาไทย รวมถึงงานอ่านทั้งหน้าและงานอ่านข้อความสั้น
  - ใช้ตัวชี้วัดแบบความทับซ้อนของ n-gram และ edit distance (BLEU, METEOR, F1, normalized Levenshtein และ ANLS สำหรับงานอ่านข้อความสั้น)
  - บทนำระบุว่า diacritic ที่ซ้อนกันเป็นความยากของภาษาไทย แต่ไม่มีคะแนนที่แยก mark ออกมาให้เห็น
- หลังจากนั้นมี OCR ภาษาไทยแบบเปิดออกมาหลายตัว
  - Typhoon OCR [nonesung2026typhoonocr] เวอร์ชัน 1.5 เป็น full fine-tune ของ Qwen3-VL-2B [bai2025qwen3vl] และผู้เขียนระบุว่า infographic เป็นจุดที่ยังต้องปรับปรุง
  - Pathumma-llm-vision 3.0 [nectec2026pathumma] เป็น fine-tune ของ Qwen3-VL-2B อีกตัว
  - wayu-paxa-ocr-zero [pipatanakul2026synthetic] เป็น fine-tune ของ PaddleOCR-VL [cui2025paddleocrvl] ด้วยหน้าเอกสารไทยสังเคราะห์
- ทุกงานรายงานความแม่นยำรวม **งานของเราถามแทนว่า สระและวรรณยุกต์หายไปตรงไหน**

**Diacritic ใน OCR** อักษรที่มี diacritic มากเป็นที่รู้กันว่ายากสำหรับ OCR
- มีงานเสนอการแก้ข้อความหลัง OCR สำหรับ diacritic ภาษาเวียดนามโดยเฉพาะ [do2025reference]
- งานประเมิน OCR ภาษาอาหรับแยกข้อความที่มี diacritic เป็นเงื่อนไขต่างหาก [elsafty2025arabic]
- เราไม่พบงานที่ให้คะแนน mark ภาษาไทยแยกจากลำดับการอ่านและข้อความที่เขียนเกิน ซึ่งเป็นสิ่งที่ตัวชี้วัดของเราทำ

**การวนซ้ำและการตกหล่นใน OCR VLM**
- decoding ที่เลือกคำตามความน่าจะเป็นสูงสุดทำให้ข้อความวนซ้ำ [holtzman2020curious] และโมเดล OCR เอกสารก็เสื่อมแบบเดียวกัน
  - Nougat รายงานหน้าที่โมเดลพิมพ์ประโยคเดิมซ้ำ และหยุด generate เมื่อสัญญาณความแปรปรวนของ logit ต่ำลง [blecher2024nougat]
  - olmOCR สุ่มใหม่ด้วย temperature ที่สูงขึ้น [poznanski2025olmocr]
  - pipeline ของ PaddleOCR-VL ตัดข้อความที่ซ้ำหลัง decode เสร็จ [paddlex2025truncate]
  - โค้ดที่ DeepSeek-OCR เผยแพร่ห้าม n-gram ซ้ำภายในหน้าต่างหนึ่ง [deepseekocr2025code, wei2025deepseekocr]
- CC-OCR วัดการวนซ้ำในฐานะ hallucination แบบหนึ่งของ OCR [yang2025ccocr]
- งานเหล่านี้มองการวนซ้ำเป็นความล้มเหลวที่ต้องตรวจจับหรือหลีกเลี่ยง **เราวัดว่าวิธีแก้แต่ละแบบทำให้ mark ในหน้าที่ไม่วนซ้ำเสียไปเท่าไร** รวมถึง repetition penalty ของ CTRL [keskar2019ctrl] ที่บาง package ของ OCR ตั้งเป็นค่าเริ่มต้น

**ความรู้ภาษาและ training-free decoding**
- contrastive decoding ลด hallucination ของ VLM โดยลดน้ำหนักสิ่งที่โมเดลจะทำนายเมื่อไม่มีภาพหรือภาพถูกทำให้เสีย ได้แก่ VCD [leng2024vcd], M3ID [favero2024m3id] และ PAI [liu2024pai]
- วิธีเหล่านี้ตั้งสมมติฐานว่าความรู้ภาษาเป็นต้นเหตุ แต่สำหรับวรรณยุกต์ไทย เราพบว่าความรู้ภาษามักถูกอยู่แล้ว การหักมันออกจึงลบวรรณยุกต์ที่ถูกไปด้วย
- **การเรียกชื่อ:** วิธีที่เราใช้เป็นการเขียนใหม่ จึงเรียกว่า "M3ID-form" และ "PAI-style" (`docs/CLAIMS.md`)
- speculative decoding [leviathan2023speculative] ซึ่งในงานนี้ใช้ prompt lookup เป็นตัวร่าง [saxena2023pld] ทำให้ greedy decoding เร็วขึ้นโดย output ไม่เปลี่ยนเมื่อคำนวณแบบแม่นยำ เราใช้ในด้านความเร็วของเงื่อนไข training-free

---

## Notes for the author (ไม่ใส่ในเปเปอร์)

**Corrections this check forced** (already applied in this PR):
- **ThaiOCRBench does not use CER.** It does not evaluate Typhoon OCR, and
  it does not call infographics hard. The infographic weakness comes from
  the Typhoon OCR paper. The introduction draft's first paragraph is fixed.
- **PaddleOCR-VL.** Its *paper* says nothing about repetition. The
  truncation is in the PaddleX pipeline code
  (`truncate_repetitive_content`), so cite the code. The slide line is
  adjusted.
- **DeepSeek-OCR.** The n-gram ban is in its released code; we did not check
  the paper for it. Cite the code.

**Thin spots:**
- **Diacritics.** Only two peer-reviewed works were verified, Vietnamese
  (AAAI 2025) and Arabic (IEEE BigData 2025). For the Arabic one only the
  abstract was seen.
- **Preprints.** Typhoon OCR, olmOCR, Qwen3-VL, PaddleOCR-VL, DeepSeek-OCR
  and the Wayu paper are arXiv-only. Pathumma has only a model card.
- **PAI's title** differs: the ECCV version says "Images", arXiv says
  "Image". `references.bib` uses ECCV.
