# Status — Up2mEz

**Updated:** 2026-10-03

## Tracks I own

| track | package | state |
|---|---|---|
| region-OCR (PaddleOCR-VL / TEMS, rounds 1–3) | `src/labbs2026/region_ocr/` | **complete**; `docs/stage0/REGION_OCR_ROUND3_RESULTS.md` |
| Thai-marks T1/T2/T3 (Qwen3-VL-2B / Typhoon OCR 1.5, ThaiOCRBench calibration) | `src/labbs2026/thai_marks/` | T1/T2/T3 done; branch `fix/t1-scoring-v2` (PR #23) |
| Typhoon non-graphic gaps G1–G4 (session gaps) | `src/labbs2026/thai_marks/` | offline diagnosis |
| P-ZOOM (session pzoom, `collab/status/Up2mEz-pzoom.md`) | new files | draft |

The owner runs two parallel sessions: `docs/exec-plans/active/PARALLEL_SESSIONS.md`.

## Running now

Nothing on Kaggle.

## GPU-hours used this week (main account)

0 since 2026-10-03.

## Do not touch without asking

- `src/labbs2026/thai_marks/` existing modules, `configs/thai_marks/t1_t2.yaml`,
  `docs/stage0/THAI_MARKS_*`.
