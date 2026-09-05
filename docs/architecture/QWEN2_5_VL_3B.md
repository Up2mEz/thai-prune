# Qwen2.5-VL-3B Primary-Backbone Architecture Record

**Audit date:** 2026-09-04  
**Status:** `COMPLETE`
**Scientific evidence status:** `Not Tested`  
**Backbone decision:** `PRIMARY_FEASIBLE`
**Human checkpoint:** smoke-image visual review approved on 2026-09-06

## Selection basis

`Qwen/Qwen2.5-VL-3B-Instruct` was selected before any degradation experiment
because it has an inspectable Hugging Face implementation, relevant literature
compatibility, a smaller primary checkpoint than the secondary candidate, and
plausible local CPU feasibility. No compression outcome was used.

## Immutable model and software record

| Item | Pinned value |
|---|---|
| Model | `Qwen/Qwen2.5-VL-3B-Instruct` |
| Model revision | `66285546d2b821cf421d4f5eb2576359d3770cd3` |
| Processor revision | `66285546d2b821cf421d4f5eb2576359d3770cd3` |
| Processor | `Qwen2VLImageProcessor`, `use_fast=False` |
| `transformers` | `4.57.6` |
| `torch` | `2.14.0+cpu` |
| `qwen-vl-utils` | `0.0.14` |
| Config | `configs/step3/qwen25_vl_3b.yaml` |
| Implementation commit | `3280bbdf9822eaf61553bd0afa990c98eeb00e82` |

Official sources inspected:

- [pinned Qwen model repository](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/tree/66285546d2b821cf421d4f5eb2576359d3770cd3)
- [Transformers Qwen2.5-VL model documentation](https://huggingface.co/docs/transformers/v4.57.6/model_doc/qwen2_5_vl)
- `transformers.models.qwen2_5_vl.processing_qwen2_5_vl`
- `transformers.models.qwen2_5_vl.modeling_qwen2_5_vl`
- `transformers.models.qwen2_vl.image_processing_qwen2_vl`

The local Python sources are supplied by the locked package, not copied into
this repository.

## Verified processing and measurement boundary

Pinned configuration and runtime inspection agree on:

| Property | Verified value |
|---|---:|
| Spatial patch size | 14 |
| Temporal patch size | 2 |
| Spatial merge size | 2 |
| Processor minimum pixels | 3,136 |
| Processor maximum pixels | 12,845,056 |

For each image, the processor exposes `image_grid_thw = (t, h, w)`. The
pre-merge patch count is `t × h × w`. The number of representations supplied
to the language-model side is:

```text
llm_visual_token_count = product(image_grid_thw) / spatial_merge_size²
```

This definition is cross-checked at three points:

1. the formula from `image_grid_thw`;
2. the number of `<|image_pad|>` positions created by the processor; and
3. the first dimension of the runtime Vision Encoder output after its spatial
   merger.

The measured boundary is the Vision Encoder output after spatial merging,
matched to image-token positions in the language-model input. It is not the
raw patch count and is not a post-encoder pruning intervention.

## Local feasibility environment

| Item | Observed value |
|---|---|
| OS | Windows 11 |
| Logical CPU count | 8 |
| Physical RAM | 33,916,248,064 bytes (31.59 GiB) |
| CUDA | unavailable |
| PyTorch XPU | unavailable in installed build |
| Execution path | CPU, `bfloat16`, SDPA |

Windows reports an Intel Arc 140V device, but the locked PyTorch build is
CPU-only. This audit therefore does not claim working GPU acceleration.

## Smoke design

Two 448 × 448 white images contain one centered black Latin letter, A or B,
rendered with local `arial.ttf`. They are deliberately simple pipeline controls
and are marked `FORBIDDEN_STEP3_SMOKE_ONLY`; they are not Thai candidate pairs,
Stage 0 samples, or scientific accuracy evidence.

The font and rendered image hashes are stored in each run manifest. The human
researcher approved the two smoke images on 2026-09-06; the approval is
recorded in `docs/DECISION_LOG.md` and does not convert these controls into
Thai or scientific evidence.

## Run evidence

| Run ID | Purpose | Result |
|---|---|---|
| `20260904T064824Z_3280bbdf` | Processor-only audit | Grid, prompt count, and preprocessing metadata valid |
| `20260904T064919Z_3280bbdf` | Initial deterministic inference | A→A and B→B; includes weights download |
| `20260904T065945Z_3280bbdf` | Cached deterministic rerun | A→A and B→B; raw/parsed outputs reproduced |

All three runs use:

- `image_grid_thw = [1, 32, 32]`;
- pre-merge patch count = 1,024;
- formula-derived LLM visual positions = 256;
- processor image-token positions = 256; and
- runtime Vision Encoder output count = 256 for inference runs.

Cached-run resource observations:

| Measurement | Observed value |
|---|---:|
| Model load | 0.68 s |
| Preprocess per image | 0.029–0.037 s |
| Generation per image | 25.2–28.2 s |
| Peak process RSS | 8,036,507,648 bytes (7.48 GiB) |
| Total two-image run | 72.4 s |

The initial run's 531.8-second model-load measurement includes the network
download and must not be interpreted as warm model-load latency. These timings
are feasibility observations from two trivial samples, not throughput claims.

Raw artifacts are immutable local directories under `runs/step3/<run_id>/`.
Each contains `manifest.json`, `predictions.json`, and the hashed smoke images.

## Feasibility interpretation

The primary backbone is locally runnable and its LLM-boundary token accounting
is observable without modifying model internals. No current secondary-backbone
trigger is present:

- local execution succeeded;
- token accounting is not ambiguous for this image-only smoke path;
- the full-information smoke task produced parseable outputs; and
- no methodology/literature requirement currently mandates Qwen3-VL.

Therefore the proposed action is to keep Qwen2.5-VL-3B as primary and not open
the secondary candidate.

The human approval completed Step 3. No secondary-backbone trigger was opened,
and Stage 0 remains separately gated.

## Explicit non-claims

This audit does not establish:

- Stage 0 measurement validity;
- Thai rendering or linguistic validity;
- any `component_type × budget` effect;
- Resolution Reduction sensitivity;
- post-encoder Token Pruning behavior;
- real-world OCR performance; or
- cross-architecture validity.
