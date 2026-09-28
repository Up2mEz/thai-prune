# Track B — existing training-free remedies on Thai marks

**Status: `R1_PILOT_REGISTERED`** (`docs/stage0/REMEDIES_R1_REGISTRATION.md`); evaluation authorized by `docs/DECISION_LOG.md` 2026-09-28b. Owner `PELY334`. Scope agreed in
`collab/messages/20260927T1633Z_Up2mEz_to_PELY334_approve-track-a-defer-bcd.md`:
implementation and unit tests may proceed; **no evaluation run until T2
results are posted**, and who runs the evaluation (PELY334 or Up2mEz) is not
decided yet. Nothing here authorizes inference with the pinned models.

| | |
|---|---|
| package | `src/labbs2026/remedies/` |
| configs | `configs/remedies/` (with the registration) |
| scripts / worker | `scripts/remedies_*.py`, `infra/kaggle/remedies_worker.py` (after registration) |
| registration | `docs/stage0/REMEDIES_R1_REGISTRATION.md` (pilot, 24 items) |
| branch | `PELY334/remedies` |

## 1. Question

RQ-B, accuracy half: do existing training-free remedies reduce mark-specific
error on ThaiOCRBench (Full-page OCR, Text recognition) for Qwen3-VL-2B and
Typhoon OCR 1.5 **without raising other errors**, and at what latency? Compared
against FULL greedy (T1) and against T2's oracle upper bound, which is why the
evaluation waits for T2 (`QWEN3VL_TYPHOON_EXPERIMENT_PLAN.md` §6).

## 2. Remedies, from the plan's §2 table

| family | method | what it needs | built |
|---|---|---|---|
| contrastive decoding | **VCD** (arXiv:2311.16922): contrast logits with a noised image, adaptive plausibility cut | a second forward stream per step (~2× decode) | step 1 — `remedies/contrastive.py` |
| contrastive decoding | **M3ID** form: contrast with **no image**, weight growing with step | a second, text-only stream | step 1 — `remedies/contrastive.py` |
| attention amplification | **PAI** (arXiv:2407.21771): scale attention to image tokens in chosen layers | attention hook; near-free | step 2 — `remedies/pai.py` |
| OCR-head intervention | **sink redistribution** (arXiv:2505.15865): move attention mass off sink tokens in OCR heads | head identification first; near-free | **deferred** by PELY334 (2026-09-28); not started |

Every method's formula is taken from its paper **and must be re-checked against
the paper text before the registration**; the implementation notes below say
where this project's reading could differ. The literature is search-level
(`docs/stage0/BEYOND_PRUNING_LITERATURE_SCAN.md`).

## 3. Engineering constraints (from what this project already paid for)

- **Qwen3-VL keeps `rope_deltas` as model state** (ONBOARDING §9). A second
  stream with a different image or no image would inherit the wrong M-RoPE
  offset through `generate`. The contrastive decoder therefore runs its own
  greedy loop with **explicit position ids per stream** (as T2 does) and never
  relies on the cached delta.
- The loop with `alpha = 0` must reproduce `model.generate` greedy exactly;
  this is the unit test that guards the position handling.
- Settings (α, β, noise step, layers, heads) are chosen on a calibration
  sub-split only, fixed in the registration before any evaluation output.

## 4. What is deliberately not done here

- No run with pinned weights, no Kaggle job, no registration — until T2.
- No claim that any remedy helps; the plan's gate logic stands.
- Tracks C and D.

## 5. Waiting on

1. T2 results (`result` message from Up2mEz).
2. Up2mEz's decision on who runs B's evaluation.
