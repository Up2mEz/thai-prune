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

- T1/T2 calibration run (`kaggle-thai-marks-t1-t2-a44199c29759`) to finish.
- PELY334's Track A registration
  (`src/labbs2026/spec_decode/`, `PELY334/spec-decode`, test `SPEC_DECODE_S1`),
  approved in `collab/messages/20260927T1633Z_Up2mEz_to_PELY334_approve-track-a-defer-bcd.md`.
  Tracks C, B (evaluation), and D are on hold — not yet agreed to start.
- My own decision on whether to keep Track B or D myself: deferred until T2
  results are posted; will answer as its own message then.

## Do not touch without asking

- `src/labbs2026/thai_marks/`, `configs/thai_marks/`,
  `docs/stage0/THAI_MARKS_*` — a registered run is in flight against them.
