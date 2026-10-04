# Track D — input-side probes on Thai marks

**Status: `D1_DONE`** — results `docs/stage0/INPUT_SIDE_D1_RESULTS.md` (Decision Log 2026-10-04b). Owner `PELY334`. Scope agreed by Up2mEz as **G2
(patch phase) only**, with three edits built in
(`collab/messages/20261004T0605Z_Up2mEz_to_PELY334_f1-addendum1-ok-pr38-track-d-review-s1-results.md`);
G3 (scale) stays with P-ZOOM on Up2mEz's side. Nothing runs before the D1
Decision Log entry is approved by both researchers;
`configs/input_side/d1.yaml` stays `DRAFT_FOR_REVIEW` until then.

| | |
|---|---|
| package | `src/labbs2026/input_side/` |
| configs | `configs/input_side/` |
| scripts / worker | `scripts/input_side_kaggle.py`, `scripts/input_side_analyze.py`, `infra/kaggle/input_side_worker.py` |
| registration | `docs/stage0/INPUT_SIDE_D1_REGISTRATION.md` (`DRAFT_FOR_REVIEW`) |
| branch | `PELY334/input-side-d1` |

## Question (gap G2)

Does the 16-px patch grid decide whether a Thai mark survives? A tone mark is
a few pixels inside a patch dominated by its base consonant
(`QWEN3VL_TYPHOON_ARCHITECTURE_GAPS.md` §2); where the grid falls on a glyph is
an accident of page position. If marks flip with sub-patch shifts while a
phase-neutral shift leaves them alone, alignment — not resolution — governs
mark survival, and phase-aware input handling (e.g. reading at two phases) is
a training-free remedy worth registering.

## Design

FIND_VS_READ_F1's grid-aligned crop (same pixels and scale as the page) is
moved by `d` px before it reaches the model — no resampling, white outside the
page. `d ∈ {0, 4, 8, 12}` varies patch phase; `d = 16` keeps patch phase and
changes the 2×2 merge pairing; `d = 32` keeps both and moves one token row
and `d = 64` keep both and move one / two token rows (controls for position and edge context). Same 69 Fine-grained calibration
items as F1; both models, Typhoon primary.

## Waiting on

1. Up2mEz's review of the D1 registration and approval of its Decision Log
   entry.
2. Then smoke, full run, analysis, results.
