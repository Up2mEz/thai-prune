# Qwen3.5-4B Measurement Diagnostic Protocol — Pre-registered

**Frozen before diagnostic outcome:** 2026-09-08

**Status:** `FROZEN_BEFORE_DIAGNOSTIC_OUTCOME`

**Scope:** 100 already exposed calibration `pair_id` values only

**Gate 0:** `NOT_RUN`; locked validation remains sealed

## Question

หลัง Qwen3.5-4B calibration ภายใต้ exact A/B contract ให้ผลใกล้ chance และ
เลือกตำแหน่ง A อย่างรุนแรง diagnostic นี้ถามว่า failure สัมพันธ์กับ
`measurement/interface`, การแยก visual representation, ทั้งสองส่วนร่วมกัน
(`mixed`) หรือหลักฐานยังไม่พอ (`inconclusive`) โดยไม่เปลี่ยน primary metric
ย้อนหลังและไม่ทดสอบ compression

## Frozen scientific boundary

- ใช้เฉพาะ 100 open calibration pairs และสี่ rendering conditions เดิม
- `pair_id` เป็น independent statistical unit; font, size, member และ order
  เป็น repeated observations
- ไม่อ่าน ไม่ package และไม่ infer locked-validation pairs
- ไม่เปลี่ยน pair inventory, allocation, Unicode strings หรือ frozen split
- ไม่ใช้ Token Pruning, Resolution Reduction, Token Merging หรือ main experiment
- D1–D4 เป็น secondary measurement diagnostics ไม่ใช่ Gate 0 metric

## D1 — Position swap

สำหรับ full-information image เดิมทุกภาพ รัน candidate order ทั้ง registered
และ swapped แล้ว map output กลับเป็น canonical member `a/b`

- `content_consistency`: เลือก canonical member เดิมเมื่อสลับตำแหน่ง
- `position_following`: เลือก label position เดิม (`A` หรือ `B`) ทั้งสอง order
- `order-averaged accuracy`: accuracy เมื่อถือสอง order เป็น repeated measures

Interface evidence ถูกกำหนดล่วงหน้าว่า pair-clustered 95% CI lower bound ของ
`position_following` ต้องอย่างน้อย 0.90 เกณฑ์นี้ชี้ measurement/interface
association เท่านั้น ไม่ระบุ causal mechanism ภายใน chat model

## D2 — Candidate scoring without A/B tokens

ใช้ prompt คงที่ `อ่านข้อความในภาพและตอบเฉพาะข้อความที่เห็น` และ teacher-force
candidate text ทั้งสอง member ที่ assistant boundary โดยไม่ใส่ candidate list
หรือ token A/B คำนวณผลรวม token log-probability ของ candidate sequence

Primary diagnostic score คือ

```text
S(c, image) = log P(c | image, prompt) - log P(c | blank, prompt)
```

เลือก candidate ที่ `S` สูงกว่า อีกทั้งรายงาน raw sequence score และ
mean-token blank-corrected sensitivity analysis แต่ห้ามเลือก scoring variant
จากผล ตัว primary diagnostic ใช้ sum log-probability ตามที่ freeze ไว้

Visual signal ถือว่า present ใน diagnostic เมื่อ accuracy point estimate
อย่างน้อย 0.60 และ pair-clustered CI lower bound มากกว่า chance 0.50

## D3 — Representation diagnostic

เก็บ uncompressed Qwen3.5 Vision Encoder output หลัง spatial merger ก่อนเข้า
final A/B decision รูปร่างคาดหมาย 196 positions × hidden dimension สำหรับแต่ละ
ภาพ ภายในแต่ละ `pair_id` ทำ leave-one-render-condition-out nearest-member
centroid retrieval ด้วย cosine similarity จาก flattened post-merger tensor

- primary: retrieval accuracy
- secondary: cosine similarity ของ correct-member centroid ลบ other-member
  centroid

ใช้ signal-present rule เดียวกับ D2 ผลนี้บอกเพียงว่าระยะ representation มี
ข้อมูลแยก member ข้าม render หรือไม่ ไม่ใช่ primary task accuracy และไม่พิสูจน์
ว่า downstream language model ใช้ข้อมูลนั้น

## D4 — Visual rescue

ใช้ source condition `noto_sans_thai_regular__72__center` ของ open pairs ทั้ง
100 คู่ ตรวจ foreground bounding box จากภาพเดิม เพิ่ม padding 8 px แล้ว resize
ด้วย bicubic ให้ด้านยาว 320 px ก่อนวางกึ่งกลาง canvas 448×448 พื้นขาว

Canvas, processor, prompt และจำนวน native visual positions ต้องคงเดิม นี่คือ
glyph-scale rescue diagnostic ไม่ใช่ Resolution Reduction และไม่ลด visual
tokens รัน D1 และ D2 บน rescue image แล้วเปรียบเทียบ D2 blank-corrected
accuracy กับ source condition เดิมแบบ paired by `pair_id`

Rescue gain ต้องมี point estimate อย่างน้อย +0.10 และ pair-clustered 95% CI
lower bound มากกว่า 0 จึงถือว่า evidence present

## Root-cause classification frozen before results

ใช้ลำดับต่อไปนี้โดยไม่ retune:

1. `mixed`: มี interface evidence, original D2 ยังไม่ผ่าน signal-present และ
   D4 มี rescue gain
2. `measurement/interface`: มี interface evidence และ D2 หรือ D3 มี visual
   signal present
3. `visual representation`: ไม่มี interface evidence, ทั้ง D2 และ D3 ไม่ผ่าน
   signal-present และ D4 มี rescue gain
4. `inconclusive`: กรณีอื่นทั้งหมด

Action map ที่ freeze ไว้:

- `measurement/interface` → A. retain Qwen3.5 + redesign measurement
- `visual representation` หรือ `mixed` → B. reject Qwen3.5 และประเมิน
  Qwen2.5 ภายใต้ contract ใหม่
- `inconclusive` → C. screen backbone ที่ architecture ต่างจริง โดยเสนอได้แต่
  ห้ามเริ่ม inference ใน diagnostic นี้

Qwen2.5 เปรียบเทียบได้เฉพาะ metric ที่ใช้ contract เดียวกันเท่านั้น ผล A/B
เดิมอาจรายงานเป็น historical context แต่ห้ามใช้แทน D2/D3 ที่ยังไม่ได้รันด้วย
contract เดียวกัน

## Reproducibility and stop

ทุก artifact ต้องบันทึก config hash, seed, model/processor/tokenizer revision,
Git commit, environment, runtime visual counts, failures และ checksums ผลต้อง
วิเคราะห์ด้วย pair-clustered bootstrap และหยุดที่ human-review checkpoint
หลัง D1–D4 โดยไม่เปลี่ยน Gate 0 หรือเปิดขั้นถัดไป

