# Qwen3.5-4B Measurement Diagnostic Report

**Evidence status:** `OPEN_CALIBRATION_MEASUREMENT_DIAGNOSTIC_ONLY`

**Root-cause classification:** `inconclusive`

**Required action:** `C. SCREEN_ARCHITECTURALLY_DISTINCT_BACKBONE`

**Gate 0:** `NOT_RUN`

**Next state:** `HUMAN_REVIEW_CHECKPOINT`

## คำถามที่ตรวจ

หลัง `Qwen/Qwen3.5-4B` calibration ภายใต้ exact A/B contract ให้ผลใกล้
chance งานนี้พยายามแยกว่า failure มาจาก answer-position interface หรือจาก
visual discrimination จริง โดยใช้เฉพาะ 100 `pair_id` ที่เปิดใน calibration
แล้ว และตรึง protocol, metrics, CI และ decision criteria ก่อนเปิดผลไว้ใน
`docs/stage0/QWEN35_MEASUREMENT_DIAGNOSTIC_PROTOCOL.md` กับ
`configs/stage0/qwen35_measurement_diagnostic.yaml`.

ไม่มี locked-validation pair ถูกเปิด ไม่มี split change, Resolution Reduction,
Token Pruning, Token Merging หรือ main experiment และทุก interval ใช้
pair-clustered bootstrap 2,000 replicates (`seed=20260908`) โดย `pair_id` เป็น
independent unit.

## ผล D1-D4

| Diagnostic | Metric | Estimate | Pair-clustered 95% CI | Frozen criterion | Result |
|---|---|---:|---:|---|---|
| D1 Position swap | content consistency | 10.75% | 6.63-15.38% | descriptive | ต่ำมาก |
| D1 Position swap | position following | 89.25% | 84.63-93.38% | CI low >= 90% | ไม่ผ่าน criterion |
| D1 Position swap | registered accuracy | 49.88% | 49.00-50.75% | descriptive | chance-level |
| D1 Position swap | swapped accuracy | 49.88% | 48.88-50.75% | descriptive | chance-level |
| D2 Candidate scoring | raw sequence accuracy | 51.13% | 50.13-52.25% | sensitivity | signal อ่อน |
| D2 Candidate scoring | blank-corrected sum-logP accuracy | 52.88% | 50.75-55.13% | estimate >= 60% and CI low > 50% | ไม่ผ่าน |
| D2 Candidate scoring | mean-token corrected accuracy | 52.13% | 50.38-54.00% | sensitivity | signal อ่อน |
| D3 Representation | leave-one-condition-out retrieval | 97.88% | 96.75-98.88% | estimate >= 60% and CI low > 50% | ผ่าน diagnostic criterion |
| D3 Representation | cosine similarity margin | 0.0311 | 0.0260-0.0367 | descriptive | positive |
| D4 Visual rescue | blank-corrected accuracy | 65.50% | 60.50-70.50% | signal criterion | ผ่าน |
| D4 Visual rescue | corrected gain vs source | +16.00 pp | +10.50 to +21.50 pp | gain >= 10 pp and CI low > 0 | ผ่าน |
| D4 Visual rescue | content consistency | 44.50% | 36.50-52.50% | descriptive | ดีขึ้นแต่ยังไม่สูง |
| D4 Visual rescue | position following | 55.50% | 47.50-63.50% | descriptive | bias ลดลง |

D4 ขยาย content bounding box ของ glyph ด้วย bicubic ให้ long side เป็น 320 px
ภายใน canvas 448 x 448 เดิม ใช้ processor เดิมและยังมี 196 native visual
positions จึงเป็น visual rescue diagnostic ไม่ใช่ Resolution Reduction หรือ
visual-token compression.

## การตีความตาม decision rule ที่ตรึงไว้

- D1 ให้ estimate ของ position following สูงมาก แต่ lower CI = 84.63% ต่ำกว่า
  threshold 90% จึงต้องตั้ง `interface_evidence=false` ตาม protocol แม้ pattern
  เชิงพรรณนาจะสอดคล้องกับ position bias อย่างแรง
- D2 ไม่พบ candidate-level signal ถึงเกณฑ์เมื่อหลีกเลี่ยง token A/B
- D3 พบว่า post-spatial-merger representation แยก minimal-pair member ได้สูง
  ภายใต้ probe ที่ลงทะเบียนไว้ แต่เป็น representation diagnostic ไม่ใช่
  primary accuracy และไม่พิสูจน์ว่าข้อมูลถูกใช้ได้ที่ final decision layer
- D4 พบ visual rescue ที่ชัดเจน แสดงว่าการทำ glyph ให้อ่านง่ายขึ้นสามารถฟื้น
  candidate score ได้ใน open subset นี้

หลักฐานจึงชี้ tension ระหว่าง representation ที่แยกได้, candidate decision ที่
อ่อน, answer-position sensitivity และ visual-scale sensitivity. Frozen
classifier ให้ `inconclusive` ไม่ใช่ `measurement/interface`,
`visual representation` หรือ `mixed`. ห้ามเปลี่ยน threshold หลังเห็นผลเพื่อให้
เข้าหมวดใดหมวดหนึ่ง.

## Component diagnostics

| Component | D1 position following | D2 corrected | D3 retrieval | D4 corrected | D4 gain |
|---|---:|---:|---:|---:|---:|
| `BASE_CHARACTER` | 98.13% | 56.88% | 98.75% | 92.50% | +40.00 pp |
| `LOWER_VOWEL_VARIANT` | 94.38% | 52.50% | 97.50% | 52.50% | +5.00 pp |
| `STACKED_TONE_MARK` | 86.88% | 51.25% | 98.75% | 55.00% | +5.00 pp |
| `TONE_MARK` | 77.50% | 51.88% | 98.75% | 77.50% | +30.00 pp |
| `UPPER_VOWEL_VARIANT` | 89.38% | 51.88% | 95.63% | 50.00% | 0.00 pp |

ตารางนี้เป็น exploratory component breakdown ที่มีเพียง 20 `pair_id` ต่อกลุ่ม;
CI เต็มอยู่ใน reproducibility summary และห้ามใช้เพื่อสรุปว่า tone marks หรือ
component ใด degrade เร็วกว่า.

## Qwen2.5 comparison boundary

Qwen2.5 ไม่มีผลภายใต้ D1-D4 contract เดียวกัน จึงไม่ทำ cross-backbone ranking
จาก D2, D3 หรือ D4. ผล A/B calibration เดิมใช้ measurement ใกล้เคียงกันได้เพียง
เป็น historical context แต่ไม่เพียงพอสำหรับตัดสินว่า Qwen2.5 เหนือกว่า
Qwen3.5 ภายใต้ contract ใหม่. ถ้าจะประเมิน Qwen2.5 ใหม่ต้องได้รับ human
authorization แยกต่างหาก.

## คำตัดสินหนึ่งอย่าง

**C. ต้อง screen backbone ใหม่** ตาม action map ที่ pre-register ไว้สำหรับ
`inconclusive`.

Candidate ที่เสนอสำหรับ human review คือ
[`google/gemma-3-4b-it`](https://huggingface.co/google/gemma-3-4b-it): multimodal
architecture คนละตระกูลกับ Qwen, 4B scale, รองรับ multilingual input และใช้
256 image tokens ต่อภาพตาม official model card. น้ำหนักระดับ 4B ทำให้การ fit
บน Kaggle T4 ด้วย FP16 มีความเป็นไปได้เชิงประมาณ แต่ยังไม่ใช่ compute proof;
model ยังมี gated Gemma license. ทางเลือก fallback ที่เปิดกว่าและเล็กกว่าคือ
[`HuggingFaceTB/SmolVLM2-2.2B-Instruct`](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct)
ซึ่งอิง Idefics3 และ model card รายงาน
memory footprint ระดับที่ควร fit T4 ได้ แต่ card ระบุ language focus เป็น
English จึงมีความเสี่ยงสูงกว่าสำหรับ Thai diagnostic.

ยังไม่เริ่ม run, download model, เปิด data เพิ่ม หรือเปลี่ยน backbone ใด ๆ.

## Reproducibility and verification

- successful run: `kaggle-qwen35-measurement-953dd5e386ea-79122b58`
- inference commit: `953dd5e386eaeee22b549995b9c80f2a3691ebbf`
- pre-registration commit: `4243b7f780c561e447d3efa5c624e8fe777559aa`
- model: `Qwen/Qwen3.5-4B`, revision
  `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`
- runtime: Kaggle `NvidiaTeslaT4`, FP16, `transformers==5.12.0`,
  `torch==2.14.0+cu130`, SDPA
- verified row counts: D1=800, D2=800, D3=800, D4=200
- verification: `VERIFIED`; locked pairs exposed=0; compression=`NOT_RUN`;
  visual positions={196}
- machine-readable summary:
  `docs/stage0/evidence/qwen35_measurement_diagnostic_analysis.json`
- local immutable raw/fetch/verification tree:
  `runs/kaggle/kaggle-qwen35-measurement-953dd5e386ea-79122b58/`

สอง run ก่อนหน้าล้มเหลวที่ D2 เพราะ Qwen3.5 multimodal RoPE ต้องขยาย
`mm_token_type_ids` ให้ตรงกับ candidate continuation. ไม่มี partial outcome จาก
run เหล่านั้นถูกใช้วิเคราะห์. การแก้เป็น engineering compatibility fix และไม่
เปลี่ยน scientific protocol, prompt, data, metric หรือ decision threshold.

## Stop boundary

Diagnostic เสร็จแล้วและหยุดที่ `HUMAN_REVIEW_CHECKPOINT`. Gate 0 ยังคง
`NOT_RUN`; locked validation, Stage 1A, Resolution Reduction, Token Pruning,
Token Merging, main experiment และ backbone screening run ยังไม่ได้รับอนุญาต.
