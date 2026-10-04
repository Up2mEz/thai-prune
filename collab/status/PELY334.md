# Status — PELY334

**Updated:** 2026-10-04 (after F1)

## Tracks I own

| track | package | state |
|---|---|---|
| Track A — speed without changing output (speculative decoding) | `src/labbs2026/spec_decode/` | **S1 done**: `docs/stage0/SPEC_DECODE_S1_RESULTS.md` — headline speedup 1.14–1.21×, identical except at fp16 near-ties; §6 cross-check with T1 pending T1 |
| Track B — existing training-free remedies | `src/labbs2026/remedies/` | **R1 pilot done**: `docs/stage0/REMEDIES_R1_RESULTS.md` — VCD/M3ID end loops but delete tone marks on readable pages; PAI at paper default breaks generation |
| shared tooling — output diagnostics | `src/labbs2026/output_diagnostics/` | structure-aware normalization, loop detection, per-item cause; exact bit-parallel distance (no full DP table) |
| Track C — finding versus reading | `src/labbs2026/find_vs_read/` | **F1 done**: `docs/stage0/FIND_VS_READ_F1_RESULTS.md` — Typhoon loses boxed-text marks to finding, not reading (found 7% whole vs 99% crop) |
| Track D — input side, G2 only | `src/labbs2026/input_side/` | D1 registration + Decision Log entry in review (PR #46); nothing run |

## Running now

- Nothing on Kaggle.

## Waiting on

- Up2mEz's review of D1 (PR #46).
- T1 posting, for S1 §6's cross-check; T2's rerun, to read R1's tone-deletion
  finding against image gain.

## Do not touch without asking

- `src/labbs2026/spec_decode/`, `configs/spec_decode/`, `docs/stage0/SPEC_DECODE_*`
- `src/labbs2026/remedies/`, `configs/remedies/`, `docs/stage0/REMEDIES_*`
- `src/labbs2026/output_diagnostics/`, `docs/stage0/OUTPUT_DIAGNOSTICS_NOTES.md`
- `src/labbs2026/find_vs_read/`, `configs/find_vs_read/`, `docs/stage0/FIND_VS_READ_*`
- `src/labbs2026/input_side/`, `configs/input_side/`, `docs/stage0/INPUT_SIDE_*`
