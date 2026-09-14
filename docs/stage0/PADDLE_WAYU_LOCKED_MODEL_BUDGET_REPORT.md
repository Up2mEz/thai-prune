# Paddle/Wayu Locked MODEL x BUDGET Report

> Status: `LOCKED_MODEL_BUDGET_EXPERIMENT_COMPLETE_PENDING_HUMAN_REVIEW`
>
> Terminal state: `HUMAN_REVIEW_AFTER_LOCKED_MODEL_BUDGET_PANEL`

## ขอบเขตและ provenance

การทดลองนี้ใช้ controlled synthetic Thai minimal-pair testbed เพื่อทดสอบว่า
เส้นการเปลี่ยนแปลงของ exact transcription ต่างกันตาม `MODEL x BUDGET`
หรือไม่ ภายใต้ **CONTROLLED BICUBIC INPUT RESOLUTION REDUCTION** เท่านั้น
ไม่ใช่การทดลอง post-encoder `Token Pruning`, `Token Merging` หรือ compression
โดยทั่วไป

- run: `kaggle-paddle-wayu-locked-panel-attempt5`
- workload: `100 pair_id x 2 members x 2 fonts x 2 sizes x 2 models x 4 budgets = 6,400 calls`
- original scientific design: `871996221a36a56a401fa040c239f55768561210`
- U+FFFD protocol amendment: `ee9f8c4f85feea935f8c99d05005deea16c30442`
- Attempt-5 execution: `1fa4cdda6ebe37faf215e574a6a5db467beda1cb`
- numerical-fit-exception eligibility amendment:
  `1145dcea76d19d7fb4492b460f2eee3667439232`
- BASE: `PaddlePaddle/PaddleOCR-VL-1.6@c5630abae1d940eafe0697512a0325494b02ab42`
- SPECIALIZED: `wayu-ai/wayu-paxa-ocr-zero@af0204b4f334a6d5068b6bac2b3738932d6e289b`
- local artifact verification: `VERIFIED`
- registered locked pairs: 100; unauthorized/out-of-workload locked pairs: 0

Attempt 4 remains an excluded immutable partial run and contributes zero rows.
Attempt 5 is the only completed scientific panel used here.

## FULL measurement validity

`FULL validity = PASS` ภายใต้เกณฑ์วางแผนที่ freeze ไว้ จึงอนุญาตให้ตีความ
overall primary `MODEL x BUDGET` analysis ได้ เกณฑ์นี้ไม่ยืนยัน measurement
capacity ของทุก component

| Model | FULL exact accuracy | pair-clustered 95% CI | Output-contract failure |
|---|---:|---:|---:|
| BASE | 31.750% | 24.750%–38.875% | 0.000% |
| SPECIALIZED | 45.625% | 38.875%–52.500% | 0.125% |

ค่าความต่างที่ FULL เป็น descriptive baseline association ไม่ใช่ causal effect
ของ Wayu training data และไม่ใช่หลักฐานของ robustness interaction

## Primary model และ fallback

`PRIMARY_GLMM_UNAVAILABLE`

registered `lme4::glmer` full model ถูกเรียกตามสเปกเดิม แต่เกิด numerical
fit exception ก่อนมี fitted object และก่อนสร้าง convergence diagnostics:

- `fit_status = FIT_EXCEPTION_NUMERICAL_FALLBACK_ELIGIBLE`
- `fit_stage = FULL_MODEL_FIT`
- condition classes: `simpleError`, `error`, `condition`
- call location: `pwrssUpdate`
- message: `Downdated VtV is not positive definite`
- `diagnostics_available = false`

`REGISTERED_NONPARAMETRIC_FALLBACK_USED`

fallback ใช้ `pair_id` เป็น cluster/resampling unit และคง estimator, bootstrap
10,000 replicates, seed `20260913`, covariance, 3-df DID-vector Wald test,
three DIDs, raw p-values, Holm correction และ SESOI 10 percentage points
ตามที่กำหนดไว้เดิมทั้งหมด

## Primary global result

registered fallback global test ให้ Wald statistic `5.011636`, df `3`,
`p = 0.170947` ดังนั้น global interaction ไม่ significant ที่ two-sided
alpha 0.05

Frozen classifier:

`NO_CONFIRMATORY_MODEL_BUDGET_INTERACTION_EVIDENCE`

ผลนี้หมายถึงไม่มี confirmatory evidence ของ `MODEL x BUDGET` interaction
ภายใต้ design นี้ ไม่ใช่ equivalence และไม่พิสูจน์ว่า robustness เท่ากัน

## Registered exact-transcription DIDs

Positive DID หมายถึง SPECIALIZED มีการเปลี่ยนจาก FULL ที่สูงกว่า BASE
บน probability scale

| Contrast | DID | separate pair-clustered bootstrap 95% CI | Raw p | Holm p |
|---|---:|---:|---:|---:|
| `DID_196` | +0.250 pp | −2.375 ถึง +2.875 pp | 0.887411 | 1.000000 |
| `DID_121` | +1.625 pp | −1.500 ถึง +4.875 pp | 0.339966 | 1.000000 |
| `DID_64` | −1.750 pp | −5.250 ถึง +1.875 pp | 0.357464 | 1.000000 |

CI ทั้งสามเป็น separate percentile bootstrap CIs ไม่ใช่ Holm-adjusted หรือ
simultaneous CIs ทุก observed `|DID|` ต่ำกว่า SESOI 10 pp แต่ classifier เป็น
Case 4 เพราะ omnibus ไม่ significant; ไม่ใช่ Case 2

## Registered CER sensitivity

CER ต่ำกว่าดีกว่า จึงต้องกลับทิศเมื่อตรวจ qualitative agreement กับ exact
accuracy ผล sensitivity เป็น `PARTIALLY CONSISTENT`: ทิศทางสอดคล้อง 2 จาก 3
budgets แต่ไม่มีผลใด significant และช่วงความไม่แน่นอนกว้าง

| Contrast | CER DID | separate 95% CI | Raw p | Holm p |
|---|---:|---:|---:|---:|
| `DID_196` | −1.625 pp | −5.250 ถึง +1.625 pp | 0.361564 | 0.361564 |
| `DID_121` | +8.833 pp | −0.376 ถึง +22.125 pp | 0.112989 | 0.338966 |
| `DID_64` | +14.896 pp | −3.813 ถึง +35.355 pp | 0.130087 | 0.338966 |

CER fallback global test: Wald `3.779708`, df `3`, `p = 0.286255`.
CER เป็น sensitivity analysis และไม่ใช้ rescue primary result

## Component descriptives

ค่าต่อไปนี้เป็น exact accuracy และมีสถานะ
`DESCRIPTIVE_DIAGNOSTIC_ONLY`; แต่ละ component มี 20 `pair_id` และไม่ได้ผ่าน
confirmatory three-way analysis

| Component | Model | FULL | 196 | 121 | 64 |
|---|---|---:|---:|---:|---:|
| BASE_CHARACTER | BASE | 58.750% | 63.125% | 66.875% | 65.625% |
| BASE_CHARACTER | SPECIALIZED | 61.875% | 63.125% | 65.000% | 60.625% |
| LOWER_VOWEL_VARIANT | BASE | 11.875% | 13.125% | 9.375% | 14.375% |
| LOWER_VOWEL_VARIANT | SPECIALIZED | 37.500% | 38.125% | 38.125% | 37.500% |
| STACKED_TONE_MARK | BASE | 6.250% | 6.875% | 5.625% | 6.250% |
| STACKED_TONE_MARK | SPECIALIZED | 35.625% | 37.500% | 33.125% | 30.625% |
| TONE_MARK | BASE | 64.375% | 65.000% | 58.125% | 64.375% |
| TONE_MARK | SPECIALIZED | 61.250% | 64.375% | 68.750% | 66.250% |
| UPPER_VOWEL_VARIANT | BASE | 17.500% | 18.125% | 20.000% | 18.125% |
| UPPER_VOWEL_VARIANT | SPECIALIZED | 31.875% | 33.750% | 32.500% | 34.375% |

ตารางนี้ใช้เพื่อวินิจฉัย measurement heterogeneity เท่านั้น ห้ามเลือก component
ภายหลังเพื่อแทน primary outcome และห้ามสรุปว่า Thai orthographic component
ชนิดใดเสื่อมเร็วกว่า

## FACT / INFERENCE / UNKNOWN

### FACT

- Attempt 5 ทำครบและผ่าน local verification ที่ 6,400/6,400 calls
- FULL validity ผ่านเกณฑ์ที่ freeze ไว้
- registered full GLMM เกิด eligible numerical exception ที่ `pwrssUpdate`
  และไม่มี diagnostics ที่จะรายงาน
- registered pair-clustered fallback ให้ global `p = 0.170947`
- DIDs ทั้งสามไม่ผ่าน Holm และ observed magnitude ต่ำกว่า 10 pp
- frozen decision label คือ
  `NO_CONFIRMATORY_MODEL_BUDGET_INTERACTION_EVIDENCE`

### INFERENCE ที่อนุญาต

ภายใต้ model pair, revisions, controlled synthetic dataset, OCR prompt/parser,
budget grid และ BICUBIC Input Resolution Reduction นี้ โครงการไม่พบ
confirmatory evidence ว่า Thai-specific OCR adaptation มี degradation curve
ต่างจาก BASE ตามเกณฑ์ที่ลงทะเบียนไว้

### UNKNOWN / ยังพิสูจน์ไม่ได้

- models มี equivalent robustness หรือไม่
- true interaction มีขนาดเล็กกว่า SESOI จริงหรือไม่
- ผลจะ generalize ไปยัง real-world Thai OCR, model family อื่น หรือ dataset อื่นหรือไม่
- ผลของ post-encoder Token Pruning, Token Merging หรือ compression family อื่น
- causal effect ของ Wayu training data
- attention, representation หรือ component-specific mechanism

## Transparency disclosure

The preregistered primary GLMM encountered a numerical fitting exception before
convergence diagnostics could be produced. The preregistered protocol already
contained a pair-clustered nonparametric fallback with a global interaction
test, DID contrasts, multiplicity correction, and the same SESOI decision
framework, but it was ambiguous whether a pre-diagnostic numerical fit
exception triggered that fallback. After the FULL validity gate had been
observed, but before any reduced-budget interaction or contrast result was
computed, the protocol was amended to classify numerical exceptions arising
inside the registered GLMM fitting path as fallback-eligible. No GLMM formula,
fallback estimator, test, threshold, or decision rule was changed.

Amendment นี้ไม่ใช่ preregistered eligibility และไม่ขจัดความเสี่ยงจาก
post-data-access bias ทั้งหมด

## Artifact preservation

Canonical analysis files อยู่ที่
`runs/kaggle/kaggle-paddle-wayu-locked-panel-attempt5/analysis/` พร้อม hashes ใน
`ANALYSIS_COMPLETION_MANIFEST.json` ส่วน partial analysis ก่อน amendment ถูกเก็บ
แยกไว้ที่ `analysis_pre_exception_eligibility_amendment/` และไม่ได้ overwrite

ระหว่าง parent-process capture บน Windows มี background reader thread รายงาน
`cp874 UnicodeDecodeError` หลัง structured outputs ถูกสร้างครบแล้ว คำสั่งหลัก
exit 0 และไม่มีการ rerun ประเด็นนี้ถูกบันทึกเป็น engineering observation ไม่ใช่
scientific exclusion หรือ result change

## ข้อเสนอแนะถัดไป

เสนอเพียงอย่างเดียว: ให้ human reviewer ตรวจและตัดสินรับผล registered panel
พร้อม disclosure นี้ก่อนพิจารณางานใดต่อไป; ยังไม่อนุญาต experiment, post-hoc
analysis, threshold change, prompt tuning, pruning/merging หรือ fine-tuning ใหม่

`HUMAN_REVIEW_AFTER_LOCKED_MODEL_BUDGET_PANEL`
