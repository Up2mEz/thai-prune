# Status — Up2mEz

**Updated:** 2026-09-27

## Tracks I own

| track | package | state |
|---|---|---|
| region-OCR (PaddleOCR-VL / TEMS, rounds 1–3) | `src/labbs2026/region_ocr/` | **complete**; results in `docs/stage0/REGION_OCR_ROUND3_RESULTS.md` |
| Thai-marks T1/T2 (Qwen3-VL-2B / Typhoon OCR 1.5 on ThaiOCRBench) | `src/labbs2026/thai_marks/` | **running** on Kaggle |

## Running now

- Kaggle kernel `thanakritsamoena/labbs2026-thai-marks-t1-t2`, run id
  `kaggle-thai-marks-t1-t2-a44199c29759`, commit `a44199c`. T1 (FULL baseline,
  2 models × 2 prompts) and T2 (oracle mark-variant scoring) on the 178-item
  calibration split. Registration:
  `docs/stage0/THAI_MARKS_T1_T2_REGISTRATION.md`. Results will be posted as a
  `result` message.

## Waiting on

- Nothing from the collaborator yet. First thing I need: a `proposal` message
  saying which track you want to take (see `ONBOARDING.md` §7).

## Do not touch without asking

- `src/labbs2026/thai_marks/`, `configs/thai_marks/`,
  `docs/stage0/THAI_MARKS_*` — a registered run is in flight against them.
