# Qwen3.5-4B Stage 0 Backbone Calibration

**Run:** `kaggle-qwen35-stage0-4fef178183d7-b31935da`

**Inference commit:** `4fef178183d77c533fcc854a37748ce308688e38`

**Evidence scope:** open calibration only; `FULL_INFORMATION`; no locked
validation and no compression intervention

**Decision recommendation:** `MEASUREMENT_REDESIGN_REQUIRED`

## Executive conclusion

`Qwen/Qwen3.5-4B` รันบน Kaggle Tesla T4 ด้วย FP16 ได้โดยไม่ quantize และ
engineering smoke ผ่านทุก contract รวมทั้ง exact A/B token, direct-forward
logit equality, runtime visual accounting และ exact rerun อย่างไรก็ตาม
full-information accuracy เท่ากับ 49.875% (pair-clustered 95% CI
49.00–50.75%) และทั้งห้า component เป็น `INADEQUATE` ตามเกณฑ์ planning ที่
ตรึงก่อนเปิดผล จึงไม่เหมาะเป็น primary experimental backbone ภายใต้
measurement contract ปัจจุบัน

ผลนี้ไม่ใช่เพียง accuracy ต่ำ: blank control เลือกตำแหน่ง A 100%,
full-information เลือก A 93.375%, expected-A accuracy 93.25% แต่ expected-B
accuracy 6.50% และ mean image gain เท่ากับ 0.0106 (95% CI −0.0173 ถึง
0.0399) จึงไม่มีหลักฐานว่า aggregate decision ใช้ภาพได้เพียงพอสำหรับวัด
degradation ภายหลัง

## สถานะก่อนเปิดผล Qwen3.5

- primary backbone เดิม: `Qwen/Qwen2.5-VL-3B-Instruct` revision
  `66285546d2b821cf421d4f5eb2576359d3770cd3`;
- Stage 0: repaired open calibration และ Checkpoint E diagnostic เสร็จแล้ว;
- Gate 0: `NOT_RUN`;
- allocation: 100 open calibration + 100 locked validation `pair_id`,
  20/component/split;
- frozen conditions: Noto Sans Thai และ Noto Serif Thai ที่ 72/96 px,
  ตำแหน่ง center;
- parser: `^[AB]$`; generation contract: one canonical A/B token;
- Qwen2.5 LLM-boundary positions: 256 จาก grid `[1,32,32]`, pre-merge 1,024;
- provisional SESOI: 10 percentage points เหนือ chance 50%;
- Qwen2.5 ไม่เหมาะเป็น all-component instrument เพราะ
  `LOWER_VOWEL_VARIANT` และ `STACKED_TONE_MARK` มี point estimate ไม่เกิน
  60%, `UPPER_VOWEL_VARIANT` เป็น borderline, blank A bias 85% และ image
  gain/member asymmetry อ่อนใน component สำคัญ

## Pinned model and architecture

| Field | Observed / pinned value |
|---|---|
| Model | `Qwen/Qwen3.5-4B` |
| Model/processor/tokenizer revision | `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` |
| Model class | `Qwen3_5ForConditionalGeneration` |
| Processor wrapper | `Qwen3VLProcessor` |
| Image processor | `Qwen2VLImageProcessor` |
| Tokenizer | `Qwen2Tokenizer`; A=`32`, B=`33` verified at assistant boundary |
| Transformers / Torch | `5.12.0` / `2.14.0+cu130` |
| Device / dtype / attention | Tesla T4 / FP16 / SDPA |
| Parameters / checkpoint bytes | 4,659,865,088 / 9,319,828,096 bytes |
| License | Apache-2.0 |

Official metadata and implementation used for pre-registration are the pinned
[model page](https://huggingface.co/Qwen/Qwen3.5-4B),
[config](https://huggingface.co/Qwen/Qwen3.5-4B/blob/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a/config.json),
[preprocessor config](https://huggingface.co/Qwen/Qwen3.5-4B/blob/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a/preprocessor_config.json),
[Transformers 5.12 documentation](https://huggingface.co/docs/transformers/v5.12.0/en/model_doc/qwen3_5),
and [model source](https://github.com/huggingface/transformers/blob/v5.12.0/src/transformers/models/qwen3_5/modeling_qwen3_5.py).

## Visual-token measurement boundary

Runtime hooks ยืนยันเส้นทางต่อ observation ดังนี้:

```text
448 × 448 RGB image
  -> patch size 16, image_grid_thw = [1, 28, 28]
  -> patch_embed output = 784 pre-merge representations
  -> spatial_merge_size = 2
  -> merger pooler_output = 196 representations
  -> 196 image placeholders / positions entering the language model
```

คำว่า visual token ในรายงานนี้หมายถึง **Qwen3.5 Vision Encoder spatial-merger
`pooler_output` ที่แทน image placeholder positions ใน LLM input** ไม่ใช่
pre-merge patch count และไม่ใช่ budget ที่ถูกบีบอัด ค่าทั้ง formula,
placeholder count, patch hook และ merger hook ตรงกันทุก 2,040 calls

## Engineering smoke

Smoke ใช้ห้า pair ที่เลือกก่อน inference หนึ่ง pair/component, condition
`noto_sans_thai_regular__72__center`, full/blank รวม 20 calls ต่อ exact run
และทำสองรอบ รวม 40 calls สถานะ `PASS` ทุกข้อ:

- pinned model/processor/tokenizer/Transformers identity;
- one exact canonical token, parser และ argmax ตรงกัน;
- `do_sample=false`, `min_new_tokens=max_new_tokens=1`;
- generation pre-processor A/B logits เท่ากับ direct-forward logits;
- runtime visual accounting 784 → 196 ตรงทุก boundary;
- raw output, token, logits และ metadata ตรงกัน exact rerun;
- smoke ไม่ถูกนำไปคำนวณ accuracy evidence

## Full calibration design

ใช้เฉพาะ 100 open calibration `pair_id`: 100 × 4 frozen conditions × 2
displayed members = 800 full-information calls และ blank control 100 × 2
candidate orientations = 200 calls รวม 1,000 ต่อรอบ ทำ exact rerun เป็น
2,000 calls ไม่ pool สองรอบ และใช้ `pair_id` เป็น independent unit

## Primary results

| Component | Accuracy | Pair-clustered 95% CI | Status |
|---|---:|---:|---|
| `BASE_CHARACTER` | 50.625% | 50.00–51.875% | `INADEQUATE` |
| `TONE_MARK` | 50.000% | 48.125–51.875% | `INADEQUATE` |
| `UPPER_VOWEL_VARIANT` | 47.500% | 45.00–49.375% | `INADEQUATE` |
| `LOWER_VOWEL_VARIANT` | 50.000% | 48.125–51.875% | `INADEQUATE` |
| `STACKED_TONE_MARK` | 51.250% | 48.75–53.75% | `INADEQUATE` |
| **Overall** | **49.875%** | **49.00–50.75%** | **`INADEQUATE`** |

Parser failures = 0, execution failures = 0 และ exact-rerun mismatch = 0/1,000.
ช่วงความเชื่อมั่นคำนวณด้วย cluster bootstrap ที่ `pair_id`; ไม่ได้ถือว่า 800
images เป็น independent samples

## Qwen2.5 versus Qwen3.5

| Component | Qwen2.5 | Qwen3.5 | Qwen3.5 − Qwen2.5 | Qwen2.5 status | Qwen3.5 status |
|---|---:|---:|---:|---|---|
| `BASE_CHARACTER` | 96.25% | 50.625% | −45.625 pp | `ADEQUATE` | `INADEQUATE` |
| `TONE_MARK` | 81.875% | 50.000% | −31.875 pp | `ADEQUATE` | `INADEQUATE` |
| `UPPER_VOWEL_VARIANT` | 63.750% | 47.500% | −16.250 pp | `BORDERLINE` | `INADEQUATE` |
| `LOWER_VOWEL_VARIANT` | 58.125% | 50.000% | −8.125 pp | `INADEQUATE` | `INADEQUATE` |
| `STACKED_TONE_MARK` | 56.250% | 51.250% | −5.000 pp | `INADEQUATE` | `INADEQUATE` |

Paired pair-clustered overall difference = −21.375 pp (95% CI −25.50 ถึง
−17.50). Component difference CI ไม่คร่อมศูนย์ ยกเว้น
`STACKED_TONE_MARK` (−11.25 ถึง +0.625 pp) นี่เป็น frozen-condition
association ไม่ใช่ claim ว่า architecture หนึ่งเหนือกว่าโดยทั่วไป

| Diagnostic | Qwen2.5 | Qwen3.5 |
|---|---:|---:|
| Overall accuracy | 71.25% | 49.875% |
| Blank A choice rate | 85.0% | 100.0% |
| Blank `z_A-z_B` | 0.3580 | 2.5230 |
| Mean image gain | 0.6269 | 0.0106 |
| Exact rerun | exact | exact |
| Parser failure | 0% | 0% |
| Native LLM visual positions | 256 | 196 |
| Peak allocated VRAM | 7.053 GiB | 8.559 GiB |
| Mean generation latency | 0.2629 s | 0.3029 s |

จำนวน native visual positions ต่างกันตาม architecture และไม่ใช่ compression
treatment จึงห้ามอธิบายความต่างของ accuracy ว่าเกิดจาก token count เพียงอย่างเดียว

## Bias, image gain, and member asymmetry

Blank images ไม่มี visual ground truth จึงไม่มี blank accuracy. Qwen3.5 เลือก
A 100% ในทุก orientation, lexical-status subset และ component; mean blank
`z_A-z_B=2.5230` (95% CI 2.3956–2.6475). Canonical-member-a choice rateยัง
สมดุล 50% เพราะ orientation กลับตำแหน่ง candidate ตาม design—จึงชี้ว่า bias
อยู่ที่ตำแหน่ง A มากกว่าชื่อ canonical member

Overall image gain = 0.0106 (95% CI −0.0173 ถึง 0.0399), median 0.0078 และ
proportion `image_gain>0` = 50.125% (95% CI 48.375–52.00). ทุก component
มี image-gain CI คร่อมศูนย์:

| Component | Mean image gain | 95% CI |
|---|---:|---:|
| `BASE_CHARACTER` | 0.0505 | −0.0433–0.1434 |
| `TONE_MARK` | 0.0392 | −0.0088–0.0869 |
| `UPPER_VOWEL_VARIANT` | −0.0136 | −0.0628–0.0391 |
| `LOWER_VOWEL_VARIANT` | −0.0171 | −0.0630–0.0309 |
| `STACKED_TONE_MARK` | −0.0058 | −0.0667–0.0553 |

Flag `MEMBER_ASYMMETRY` สำหรับ `LOWER_VOWEL_VARIANT`, `STACKED_TONE_MARK`,
`TONE_MARK` และ `UPPER_VOWEL_VARIANT`: member-a/member-b accuracies เท่ากับ
53.75/46.25%, 57.50/45.00%, 56.25/43.75% และ 56.25/38.75% ตามลำดับ
พร้อม image-gain เปลี่ยนเครื่องหมายระหว่าง members หลาย component. Pattern นี้
สอดคล้องกับ position prior ที่แรง; ยังพิสูจน์ไม่ได้ว่าเป็น glyph-specific
recognition asymmetry

## Rendering diagnostics

Overall condition accuracy อยู่เพียง 49.0–52.0%. Paired 96-minus-72 accuracy
เท่ากับ −1.25 pp (`BASE`), 0 (`LOWER`), 0 (`STACKED`), −2.50 pp (`TONE`)
และ −5.00 pp (`UPPER`; CI −10.0 ถึง −1.25 pp). Font และ size image-gain
associations ส่วนใหญ่เล็กและคร่อมศูนย์ การที่ไม่มี rendering condition ใด
ช่วยให้พ้น chance สนับสนุนข้อสรุปเรื่อง instrument inadequacy แต่ association
เหล่านี้ไม่ใช่ causal mechanism

## Compute and provenance

- first model load 54.79 s (รวม cold download/cache path); subsequent full-run
  loads 5.86–6.10 s;
- after-load allocated/reserved VRAM = 8.463/8.473 GiB;
- first-call peak allocated/reserved = 8.558/8.574 GiB;
- full-run peak allocated/reserved = 8.559/8.584 GiB;
- warm first smoke inference = 6.619 s; full-run mean = 0.3029 s/call;
- total submission = 759.15 s;
- Python 3.12.13, Torch 2.14.0+cu130, CUDA 13.0, Transformers 5.12.0;
- artifact verification `VERIFIED`; SHA/checksum, config, bundle, allocation,
  rendering, prompt, raw output, parsed output, logits, runtime และ failures
  ถูกเก็บครบ

## Evidence interpretation

### Observed

Qwen3.5-4B มี compute feasibility และ engineering observability ดี แต่
forced-choice outcome ภายใต้ frozen prompt contract ถูกครอบด้วย A-position
prior และ aggregate image gain ไม่แยกจากศูนย์ ทุก component ขาด 10-pp
downward headroom เหนือ chance

### Inference

ภายใต้ contract นี้ Qwen3.5-4B ไม่สามารถทำหน้าที่เป็น baseline measurement
instrument สำหรับการวัด degradation ได้ การเพิ่ม model generation quality
หรือความใหม่ของ backbone ไม่รับประกัน construct-valid forced-choice behavior

### Unknown

ยังไม่ทราบว่า collapse เกิดจาก Qwen3.5 instruction/chat calibration,
label-position semantics, synthetic glyph distribution หรือ interaction ระหว่างสิ่งเหล่านี้
และยังไม่ทราบว่า cross-architecture backbone หรือ pre-registered measurement
redesign ใดจะแก้ได้

### Prohibited claims

ผลนี้ไม่สนับสนุน claim ว่า Qwen3.5 อ่านภาษาไทยทั่วไปไม่ได้, Qwen3.5 ด้อยกว่า
Qwen2.5 โดยทั่วไป, Thai tone marks เปราะกว่า, visual-token count 196 เป็นสาเหตุ,
Token Pruning ทำลายรายละเอียด, หรือ compression ใดมีผล เพราะไม่มี compression
intervention และไม่มี real-world sample

## Decision and stop

เลือก `MEASUREMENT_REDESIGN_REQUIRED` ไม่ switch ไป Qwen3.5-4B และไม่ทดสอบ
Qwen3.5-2B เพราะ 4B fit บน T4 แล้ว ปัญหาที่ตรวจพบคือ measurement behavior
ไม่ใช่ compute infeasibility. Gate 0 ยัง `NOT_RUN`; locked validation,
Stage 1A, Resolution Reduction, Token Pruning และ Token Merging ยัง blocked

งานหยุดที่ human review checkpoint ตาม authorization เดิม
