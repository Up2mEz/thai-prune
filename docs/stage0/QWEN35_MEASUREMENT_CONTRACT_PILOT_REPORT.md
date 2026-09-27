# Qwen3.5 Measurement-Contract Pilot Report

**Evidence status:** `OPEN_CALIBRATION_ONLY_MEASUREMENT_DIAGNOSTIC`

**Frozen decision:** `MIXED_TARGETED_INSTRUMENT_REVIEW`

**Gate 0:** `NOT_RUN`

**Next state:** `HUMAN_REVIEW_CHECKPOINT — STOP`

## ขอบเขตและการตรวจความถูกต้อง

รัน `kaggle-qwen35-contract-39dd41767265-c32968de` ใช้เฉพาะ 25
`pair_id` ที่เปิดใน calibration แล้ว โดยมี 5 pairs ต่อ component, ทั้งสอง
members, Noto Sans/Serif Thai และ 72/96 px. Condition A reuse แถว D1 เดิม
โดยรวม registered/swapped order เป็นหนึ่ง target score; Conditions B/C ทำ
deterministic transcription อย่างละ 200 observations.

Hard verification ผ่านทั้งหมด: B=200, C=200, target-pixel identity=200/200,
artifact checksums ถูกต้อง, source Git SHA ตรงกับ remote, และ
`locked_pair_count=0`. ไม่มี backbone screening, compression หรือ Gate 0 run.
ทุก CI ใช้ paired percentile bootstrap 2,000 resamples (`seed=20260912`)
โดย cluster ที่ `pair_id`.

## Registered primary results

| Metric | Estimate | Pair-clustered 95% CI |
|---|---:|---:|
| A forced-choice target accuracy | 49.50% | 47.50–51.00% |
| B isolated-transcription target accuracy | 0.00% | 0.00–0.00% |
| C surrounding-layout target accuracy | 0.00% | 0.00–0.00% |
| `delta_interface = B - A` | -49.50 pp | -51.00 to -47.50 pp |
| `delta_surrounding = C - B` | 0.00 pp | 0.00 to 0.00 pp |

Neither registered contrast meets the positive 10 pp SESOI rule. Direct
transcription therefore did not rescue target accuracy; it was substantially
worse than A. Adding the frozen artificial surrounding layout did not change
exact target accuracy relative to B.

## Output/error taxonomy

| Condition | Correct | Opposite | Other substitution | Deletion | Output-contract failure |
|---|---:|---:|---:|---:|---:|
| B | 0 | 0 | 186 (93.0%; CI 88.0–97.0%) | 0 | 14 (7.0%; CI 3.0–12.0%) |
| C | 0 | 0 | 155 (77.5%; CI 71.0–83.0%) | 0 | 45 (22.5%; CI 17.0–29.0%) |

`other_substitution` follows the frozen taxonomy and includes any non-empty
single-line output with extra or different code points. Raw outputs were often
Latin strings, numbers, or partial labels rather than either Thai pair member.
Condition C crosses the preregistered 20% output-contract-failure flag; its
multi-line/explanatory outputs prevent a clean interpretation of the B-to-C
input contrast.

Secondary target-component accuracy was 10.0% (CI 4.0–18.0%) for B and 11.5%
(5.0–18.5%) for C. Raw and NFC-normalized CER were identical: 2.011
(1.377–2.783) for B and 7.095 (5.890–8.353) for C. These secondary metrics do
not replace exact target accuracy.

## Descriptive component results

| Component | A | B | C | B-A | C-B |
|---|---:|---:|---:|---:|---:|
| `BASE_CHARACTER` | 50.00% | 0.00% | 0.00% | -50.00 pp | 0.00 pp |
| `LOWER_VOWEL_VARIANT` | 48.75% | 0.00% | 0.00% | -48.75 pp | 0.00 pp |
| `STACKED_TONE_MARK` | 47.50% | 0.00% | 0.00% | -47.50 pp | 0.00 pp |
| `TONE_MARK` | 51.25% | 0.00% | 0.00% | -51.25 pp | 0.00 pp |
| `UPPER_VOWEL_VARIANT` | 50.00% | 0.00% | 0.00% | -50.00 pp | 0.00 pp |

แต่ละ component มีเพียง 5 independent pairs จึงเป็น descriptive เท่านั้น
และไม่รองรับข้อสรุปว่า component ใด degrade มากกว่าอีก component.

## การตีความและ frozen decision

ผลนี้แย้งสมมติฐานว่า A/B forced-choice interface เป็นสาเหตุหลักเพียงอย่าง
เดียว: เมื่อเปลี่ยนเป็น direct transcription ภายใต้ภาพเดิม B ไม่ได้ดีขึ้น แต่
ลดลงเป็นศูนย์. อย่างไรก็ตาม ผลนี้ยังไม่พิสูจน์ว่า Vision Encoder แยก glyph
ไม่ได้ เพราะ D3 เดิมแยก representation ได้สูง และ B/C มี readout/output
contract failure ชัดเจน โดยเฉพาะ C.

ตาม decision rule ที่ตรึงก่อน inference, C มี output-contract-failure rate
22.5% ซึ่งเกิน threshold 20%. จึงต้องตัดสินเป็น
`MIXED_TARGETED_INSTRUMENT_REVIEW` ก่อนพิจารณา secondary-backbone screening.
ห้ามตีความ C เป็น natural-language context, positional robustness หรือ
realistic document layout.

Pilot นี้ไม่อนุมัติ measurement pivot, Gate 0, compression, backbone
screening หรือ main experiment. ขั้นนี้หยุดที่ human-review checkpoint.

## Reproducibility artifacts

Raw outputs, stimulus hashes, paired rows, analysis, runtime, submission spec,
verification และ checksums อยู่ใน
`docs/stage0/evidence/qwen35_measurement_contract_pilot/ARTIFACTS.md`.
