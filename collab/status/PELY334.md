# Status — PELY334

**Updated:** 2026-10-11 (M3 registered)

## Tracks I own

| track | package | state |
|---|---|---|
| Track A — speed without changing output (speculative decoding) | `src/labbs2026/spec_decode/` | **S1 done**: `docs/stage0/SPEC_DECODE_S1_RESULTS.md` — headline speedup 1.14–1.21×, identical except at fp16 near-ties; markup check §4b (headline unchanged, two exploratory readings corrected); §6 cross-check done: REF = T1 on 177/177 items, both models |
| Track B — existing training-free remedies | `src/labbs2026/remedies/` | **R1 + R2 pilots done**: contrast (M3ID-form) ends loops but deletes tone marks; mark protection (R2) keeps the loop fixes on Typhoon and halves the tone cost (`docs/stage0/REMEDIES_R2_RESULTS.md`) |
| shared tooling — output diagnostics | `src/labbs2026/output_diagnostics/` | structure-aware normalization, loop detection, per-item cause; exact bit-parallel distance (no full DP table) |
| Track C — finding versus reading | `src/labbs2026/find_vs_read/` | **F1 done**: `docs/stage0/FIND_VS_READ_F1_RESULTS.md` — Typhoon loses boxed-text marks to finding, not reading (found 7% whole vs 99% crop) |
| Track D — input side, G2 only | `src/labbs2026/input_side/` | **D1 done**: `docs/stage0/INPUT_SIDE_D1_RESULTS.md` — no evidence of a phase effect larger than a few marks on boxed single-line crops; base unstable to any small shift |
| Track E — models not yet run on ThaiOCRBench (T1's protocol) | `src/labbs2026/model_survey/` | **M1 done** (`docs/stage0/MODEL_SURVEY_M1_RESULTS.md`): Typhoon stays best; Qwen3-VL-4B ≈ base; Wayu best new model, loses a share to loops. **M2 done** (`docs/stage0/MODEL_SURVEY_M2_RESULTS.md`, run `kaggle-model-survey-m2-edb6ce636dbd`, `G` control 20/20): the card's decoding does not fix Wayu's loops; T5b's stop +11 / +24 mark F1; Wayu stays below Typhoon. Both approved by you; M2 results and Addendum 1 in PR #69. **M3 registered** (`docs/stage0/MODEL_SURVEY_M3_REGISTRATION.md`, PR #71): can Wayu read past its loops (decode-time escape, stop-only twin)? Authorized by PELY334, your review pending |

## Running now

- `kaggle-model-survey-m3-08269ed99079-smoke2` (kernel `pely334/labbs2026-model-survey-m3`); the full M3 run follows if the smoke is clean.

## Waiting on

- Your look at PR #69 (M2 results; Addendum 1 answers your four points).
- Your review of PR #71 (M3, Decision Log 2026-10-11).
- T2's rerun, to read R1's tone-deletion finding against image gain.

## Do not touch without asking

- `src/labbs2026/spec_decode/`, `configs/spec_decode/`, `docs/stage0/SPEC_DECODE_*`
- `src/labbs2026/remedies/`, `configs/remedies/`, `docs/stage0/REMEDIES_*`
- `src/labbs2026/output_diagnostics/`, `docs/stage0/OUTPUT_DIAGNOSTICS_NOTES.md`
- `src/labbs2026/find_vs_read/`, `configs/find_vs_read/`, `docs/stage0/FIND_VS_READ_*`
- `src/labbs2026/input_side/`, `configs/input_side/`, `docs/stage0/INPUT_SIDE_*`
- `src/labbs2026/model_survey/`, `configs/model_survey/`, `docs/stage0/MODEL_SURVEY_*`
