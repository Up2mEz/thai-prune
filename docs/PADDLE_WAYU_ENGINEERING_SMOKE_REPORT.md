# PaddleOCR-VL / Wayu-Paxa Engineering Smoke Report

> **NON-SCIENTIFIC ENGINEERING OBSERVATIONS ONLY**
>
> Run completed: 2026-09-12  
> Status: `ENGINEERING_SMOKE_PASS`  
> Terminal state: `HUMAN_REVIEW_AFTER_ENGINEERING_SMOKE`  
> Stage S0 authorization: **No**

## 1. Decision

Exactly one recommendation:

```text
ENGINEERING_SMOKE_PASS_S0_READY_PROPOSED
```

This is a proposal for human review. It does not automatically authorize
Stage S0, locked validation, compression, representation comparison as
scientific evidence, fine-tuning, or new-method work.

No accuracy, component accuracy, model ranking, specialization benefit,
measurement capacity, `MODEL` effect, or compression robustness was calculated
or interpreted.

## 2. Immutable run identity

- Run ID: `kaggle-paddle-wayu-smoke-dcd835673e1c-28c1cecd`
- Git commit: `dcd835673e1c0c1d3d199144cd68c5039978eb85`
- Remote ref: `refs/heads/codex/paddle-wayu-smoke`
- Config SHA-256:
  `28c1cecdb9418f5328ecb8f8d574e96f652bf87b11bc98e2e8be04bdbf1b8a81`
- Runtime SHA-256:
  `626484d85f252852f2b97e2ab18f529c55c56a5e62a06955ca90858adc829e5a`
- Source bundle SHA-256:
  `d865d689f296f4e929c3adce4b2aa75dab56958d9e203ef940a9edbcf54f1992`
- Kaggle reported two Tesla T4 devices; the run selected a T4 with compute
  capability 7.5 and 15,636,037,632 bytes total VRAM.

Kaggle normalized the configured kernel slug
`labbs2026-paddle-wayu-smoke` to the observed slug
`labbs2026-paddle-wayu-engineering-smoke` from the title. There was one
submission and no retry or resubmission. Fetch and status used the observed
slug; the immutable run/config/source identities above remained unchanged.

## 3. Exact model and environment manifest

| Role | Exact checkpoint | Runtime class | Processor | Weight SHA-256 | Weight bytes |
|---|---|---|---|---|---:|
| BASE | `PaddlePaddle/PaddleOCR-VL-1.6@c5630abae1d940eafe0697512a0325494b02ab42` | `PaddleOCRVLForConditionalGeneration` | `PaddleOCRVLProcessor` | `85a479d506a11e724e7285d395c551be69f41dbc16b6342d3cacfb189aed71db` | 1,917,255,968 |
| SPECIALIZED | `wayu-ai/wayu-paxa-ocr-zero@af0204b4f334a6d5068b6bac2b3738932d6e289b` | `PaddleOCRVLForConditionalGeneration` | `PaddleOCRVLProcessor` | `6129b78107aeecdc3a72582a12236cbb05767a6cc00e98bff81e0f3ca5758235` | 1,811,280,336 |

Both requested revisions resolved exactly. Both loading records contained no
missing, unexpected, mismatched, or error keys after the native loader's
declared legacy-key handling.

Environment:

- Python `3.12.13`
- PyTorch `2.14.0+cu130`
- Transformers `5.12.0`
- CUDA runtime `13.0`
- cuDNN `92400`
- `float16`, SDPA, greedy deterministic decoding, `max_new_tokens=32`

## 4. Exact workload and locked-set audit

The executed workload was exactly:

```text
5 pair_id x 2 members x 2 models x 2 exact repeats = 40 calls
```

Selected already-exposed open-calibration IDs:

- `base_m1_ue07_ue1c`
- `lower_variant_ue2b`
- `stacked_tone_ue13`
- `tone_ue13`
- `upper_variant_ue0b`

The same ten PNG hashes were used for both models. Prompt text was exactly
`OCR:`. Cross-model prompt, image hash, and input-token-ID consistency passed
for all 20 matched model-call groups.

```text
locked_pair_count = 0
```

## 5. Processor, token boundary, and tensor shapes

All 40 calls produced the same engineering shape/accounting contract:

| Boundary | Observed |
|---|---|
| Input PNG | 448 x 448 RGB |
| `pixel_values` | `[1024, 3, 14, 14]` |
| `image_grid_thw` | `[1, 32, 32]` |
| Input token count | 269 |
| Pre-merge visual positions | 1,024 |
| Projector output positions | 256 |
| LLM image placeholders | 256 |
| Patch embeddings | `[1024, 1152]` |
| Vision Encoder output | `[1024, 1152]` |
| Post-encoder norm | `[1024, 1152]` |
| Projector output | `[256, 1024]` |

Generated output prefixes matched the input token sequence, so output slicing
at input length 269 was verified. Raw generated token IDs were preserved.
UTF-8 round-trip decoding passed without replacement characters. All captured
patch, encoder, projector, and generation-logit tensors were finite.

These shapes are engineering observations only, not representation evidence
and not compression evidence.

## 6. Repeat consistency

All 20 `(model, pair_id, member)` groups had two exact repeats. Generated token
IDs, decoded output, input IDs, grid/count metadata, and intermediate shapes
were identical within every group.

The raw decoded strings remain in the immutable artifact, labeled
`FORBIDDEN_ENGINEERING_OBSERVATION_ONLY`. They were not scored against targets
and were not compared across models.

## 7. Kaggle T4 runtime and peak VRAM

| Role | Load time | 20-call inference time | Peak allocated | Peak reserved |
|---|---:|---:|---:|---:|
| BASE | 8.977 s | 7.615 s | 1,880,104,960 bytes (1.751 GiB) | 1,944,059,904 bytes (1.810 GiB) |
| SPECIALIZED | 9.115 s | 2.764 s | 1,880,105,472 bytes (1.751 GiB) | 1,944,059,904 bytes (1.810 GiB) |

Total measured smoke execution time was 69.841 seconds, including artifact
hashing/download preparation and sequential model work inside the smoke
process. The first BASE call included CUDA warm-up and took 4.932 seconds; it
must not be interpreted as a model-speed comparison.

The intended workload is therefore engineering-feasible on the observed
Kaggle T4 environment. This is not a scientific capability claim.

## 8. Failure and artifact audit

- Failure log: empty.
- `SUCCESS.json`: present.
- `FAILURE.json`: absent.
- Artifact checksum verification: passed.
- Local verification: `VERIFIED`.
- Exact 40-call count: passed.
- No automatic retry or scientific follow-on: passed.

Raw and derived artifacts are preserved under:

`runs/kaggle/kaggle-paddle-wayu-smoke-dcd835673e1c-28c1cecd/`

Required evidence includes `model_revision_manifest.json`,
`environment_manifest.json`, `workload_manifest.json`, `raw_outputs.jsonl`,
`repeat_consistency_report.json`, `prompt_consistency_report.json`,
`processor_grid_token_report.json`, `intermediate_tensor_shapes.json`,
`runtime_vram_report.json`, `failure_log.json`, `locked_set_audit.json`,
`recommendation.json`, checksums, and local verification.

## 9. Stop

```text
HUMAN_REVIEW_AFTER_ENGINEERING_SMOKE
```

Do not proceed to Stage S0 without a new explicit human decision.

