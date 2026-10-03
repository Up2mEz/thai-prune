# Status — PELY334

**Updated:** 2026-10-04

## Tracks I own

| track | package | state |
|---|---|---|
| Track A — speed without changing output (speculative decoding) | `src/labbs2026/spec_decode/` | **S1 done**: `docs/stage0/SPEC_DECODE_S1_RESULTS.md` — headline speedup 1.14–1.21×, identical except at fp16 near-ties; §6 cross-check with T1 pending T1 |
| Track B — existing training-free remedies | `src/labbs2026/remedies/` | **R1 pilot done**: `docs/stage0/REMEDIES_R1_RESULTS.md` — VCD/M3ID end loops but delete tone marks on readable pages; PAI at paper default breaks generation |
| shared tooling — output diagnostics | `src/labbs2026/output_diagnostics/` | structure-aware normalization, loop detection, per-item cause; exact bit-parallel distance (no full DP table) |

Track C: proposed in
`collab/messages/20260928T0546Z_PELY334_to_Up2mEz_propose-track-c-find-vs-read.md`,
no reply yet; nothing started. Track D: not started (waits on T2; overlaps
with Up2mEz's P-ZOOM on `feat/p-zoom`).

## Running now

- Nothing on Kaggle.

## Waiting on

- Up2mEz's reply on Track C.
- T1 posting, for S1 §6's cross-check.
- T2 posting, to read R1's tone-deletion finding against image gain.

## Do not touch without asking

- `src/labbs2026/spec_decode/`, `configs/spec_decode/`, `docs/stage0/SPEC_DECODE_*`
- `src/labbs2026/remedies/`, `configs/remedies/`, `docs/stage0/REMEDIES_*`
- `src/labbs2026/output_diagnostics/`, `docs/stage0/OUTPUT_DIAGNOSTICS_NOTES.md`
