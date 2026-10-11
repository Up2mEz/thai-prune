# Status — Up2mEz

**Updated:** 2026-10-11

## Tracks I own

| track | package | state |
|---|---|---|
| region-OCR (PaddleOCR-VL / TEMS, rounds 1–3) | `src/labbs2026/region_ocr/` | **complete**; `docs/stage0/REGION_OCR_ROUND3_RESULTS.md` |
| Thai-marks T1/T2/T3 (Qwen3-VL-2B / Typhoon OCR 1.5, ThaiOCRBench calibration) | `src/labbs2026/thai_marks/` | T1/T2/T3 done; merged (PR #23) |
| Typhoon non-graphic gaps G1–G4 (session gaps) | `src/labbs2026/thai_marks/` | T5b stop-at-loop passes dev check; E1 confidence PASS; E1-B1, E3 fail; merged (PR #23) |
| Order-free mark metric (metric owner) | `src/labbs2026/thai_marks/order_free.py` | adding a repeat-aware variant (PELY334's note on 33067A35); registered v2 unchanged |
| Paper (short paper; Up2mEz writes, PELY334 runs experiments) | docs | work split sent 2026-10-11 (`20261011T1315Z_Up2mEz_to_PELY334_paper-prep-work-split.md`) |
| P-ZOOM (session pzoom, `collab/status/Up2mEz-pzoom.md`) | new files | draft |

The owner runs two parallel sessions: `docs/exec-plans/active/PARALLEL_SESSIONS.md`.

## Running now

Nothing on Kaggle.

## GPU-hours used this week (main account)

None since 2026-10-04 (last: E3, `kaggle-thai-marks-e3-a652d47535cf-typhoon-x2`).

## Do not touch without asking

- `src/labbs2026/thai_marks/` existing modules, `configs/thai_marks/t1_t2.yaml`,
  `docs/stage0/THAI_MARKS_*`.
