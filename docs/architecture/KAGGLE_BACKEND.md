# Kaggle T4 Backend Feasibility Record

**Audit date:** 2026-09-06
**Status:** `KAGGLE_BACKEND_FEASIBLE_PROPOSED`
**Scientific evidence status:** `Not Tested`
**Integration branch:** `main`

## Scope

This record covers only the engineering feasibility of running the frozen
Step 3 Latin A/B smoke controls on a Kaggle Tesla T4 backend. It does not test
Thai rendering, Stage 0 measurement validity, H1, Resolution Reduction, or
post-encoder Token Pruning.

## Immutable proof run

| Item | Observed value |
|---|---|
| Run ID | `kaggle-step3-6c17245ae8a6` |
| Source commit | `6c17245ae8a6f25b1f428bcba9a12336674ade3f` |
| Source ref at submission | `refs/heads/infra/kaggle-phase1` |
| Kaggle kernel | `thanakritsamoena/labbs2026-step-3-kaggle-proof`, version 1 |
| Kaggle status | `COMPLETE` |
| Local artifact verification | `VERIFIED` |
| Observed accelerator | `Tesla T4`, compute capability 7.5 |
| Model | `Qwen/Qwen2.5-VL-3B-Instruct` |
| Model/processor revision | `66285546d2b821cf421d4f5eb2576359d3770cd3` |
| Runtime | Python 3.12.13, `torch==2.14.0+cu130`, `transformers==4.57.6` |

The verifier accepted all hard checks, including repository SHA, frozen
config and fixture hashes, package versions, accelerator identity, CUDA tensor
execution, artifact checksums, A/B parsing, and three-way token accounting.
Both controls recorded `image_grid_thw=[1,32,32]`, 1,024 pre-merge patches,
256 processor image-token positions, and 256 runtime Vision Encoder output
positions. Raw and parsed outputs were A→A and B→B and matched the local
reference outputs.

Resource observations from this single smoke run were 39.07 seconds for model
load, 59.81 seconds total, 7,572,831,744 bytes peak CUDA allocation during
inference, and 7,610,564,608 bytes peak CUDA reservation. These are feasibility
observations, not benchmark or throughput claims.

## Review and provenance boundaries

The immutable Kaggle manifest says `VALID_WITH_WARNINGS` and
`PENDING_HUMAN_REVIEW` because it was produced before the researcher approved
the two smoke images. The later human approval is recorded in
`docs/DECISION_LOG.md`; the raw artifact is intentionally not rewritten.

The proof run used `refs/heads/infra/kaggle-phase1`. After merge, the operational
profile in `configs/runtime/kaggle_t4.yaml` targets `refs/heads/main` so future
authorized work uses the research continuation branch. A future run on `main`
must still pin and verify its own exact commit, config, environment, and actual
token counts.

## Interpretation

The observed evidence supports proposing the Kaggle T4 path as an available
execution backend. Final backend adoption remains a human decision, so the
status is `KAGGLE_BACKEND_FEASIBLE_PROPOSED`, not an approved scientific gate.
This status does not authorize Stage 0 or any later experiment.
