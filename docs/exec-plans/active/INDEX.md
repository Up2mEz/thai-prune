# Active tracks

One row per experiment track. Each owner updates their own rows when a track
starts, changes state, or finishes. Superseded plans live in `docs/archive/`.

| track | owner (GitHub) | package | plan | branch | state |
|---|---|---|---|---|---|
| Thai-marks T1/T2/T3 — baseline, oracle mark scoring, line-skip diagnostic; Typhoon non-graphic gaps G1–G4 | `Up2mEz` (session gaps) | `src/labbs2026/thai_marks/` | `QWEN3VL_TYPHOON_EXPERIMENT_PLAN.md`, `PARALLEL_SESSIONS.md` | `fix/t1-scoring-v2` (PR #23) | T1/T2/T3 done on calibration; gaps G1–G4 in diagnosis |
| P-ZOOM — can Typhoon read the graphic text it leaves out, if enlarged | `Up2mEz` (session pzoom) | `src/labbs2026/thai_marks/` (new files) | `PARALLEL_SESSIONS.md` §5, `docs/stage0/P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md` | `feat/p-zoom` | P-ZOOM and P-ZOOM-2 run; P-ZOOM-3 controls (repeat, bands100) next; see `collab/status/Up2mEz-pzoom.md` |
| region-OCR — PaddleOCR-VL / TEMS, rounds 1–3 | `Up2mEz` | `src/labbs2026/region_ocr/` | (archived) | `main` | complete; `docs/stage0/REGION_OCR_ROUND3_RESULTS.md` |
| Track A — speed without changing output: exact-verification speculative decoding, Qwen3-VL-2B and Typhoon OCR 1.5 on T4 | `PELY334` | `src/labbs2026/spec_decode/` | `SPEC_DECODE_PLAN.md` | `PELY334/spec-decode` | plan approved; `SPEC_DECODE_S1` registration reviewed by Up2mEz (`TYPHOON_CARD` fixed); authorized (Decision Log 2026-09-28); code merged, smoke `kaggle-spec-decode-s1-be7333b19b85-smoke2` passed; full run waits on T1 timings |
| Track B — existing training-free remedies (VCD, M3ID, PAI, OCR-head sink redistribution) | `PELY334` (evaluation owner not decided) | `src/labbs2026/remedies/` | `REMEDIES_PLAN.md` | `PELY334/remedies` | implementation and unit tests only; no evaluation until T2 posts |
