# Active tracks

One row per experiment track. Each owner updates their own rows when a track
starts, changes state, or finishes. Superseded plans live in `docs/archive/`.

| track | owner (GitHub) | package | plan | branch | state |
|---|---|---|---|---|---|
| Thai-marks T1/T2 — FULL baseline and oracle mark-variant scoring, Qwen3-VL-2B vs Typhoon OCR 1.5 on ThaiOCRBench | `Up2mEz` | `src/labbs2026/thai_marks/` | `QWEN3VL_TYPHOON_EXPERIMENT_PLAN.md` | `main` | T1/T2 calibration run in flight on Kaggle (`kaggle-thai-marks-t1-t2-a44199c29759`) |
| region-OCR — PaddleOCR-VL / TEMS, rounds 1–3 | `Up2mEz` | `src/labbs2026/region_ocr/` | (archived) | `main` | complete; `docs/stage0/REGION_OCR_ROUND3_RESULTS.md` |
| Track A — speed without changing output: exact-verification speculative decoding, Qwen3-VL-2B and Typhoon OCR 1.5 on T4 | `PELY334` | `src/labbs2026/spec_decode/` | `SPEC_DECODE_PLAN.md` | `PELY334/spec-decode` | plan approved; `SPEC_DECODE_S1` registration reviewed by Up2mEz (`TYPHOON_CARD` fixed); authorized (Decision Log 2026-09-28); code merged, smoke `kaggle-spec-decode-s1-be7333b19b85-smoke2` passed; full run waits on T1 timings |
| Track B — existing training-free remedies (VCD, M3ID, PAI, OCR-head sink redistribution) | `PELY334` (evaluation owner not decided) | `src/labbs2026/remedies/` | `REMEDIES_PLAN.md` | `PELY334/remedies` | implementation and unit tests done (PR #14, #15); full evaluation no longer waits on T2 (Decision Log 2026-09-28b) — registration still required before any run |
