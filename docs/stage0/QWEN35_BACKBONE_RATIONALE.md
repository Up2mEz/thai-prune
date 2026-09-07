# Qwen3.5-4B Stage 0 Backbone Rationale — Pre-registered

**Pre-registration date:** 2026-09-07

**Outcome state at registration:** `NO_QWEN35_MODEL_OUTPUT_OBSERVED`

**Authorized scope:** already exposed Stage 0 calibration pairs only

**Gate 0:** `NOT_RUN`

## Scientific question

This run asks whether `Qwen/Qwen3.5-4B` has enough full-information baseline
capacity, visual evidence, headroom, reproducibility, and architectural
observability to serve as a measurement instrument for a later controlled
visual-token-compression study. It does not ask whether the model is generally
good at Thai OCR, and it does not test compression robustness.

## Outcome-independent selection rationale

`Qwen/Qwen3.5-4B` is opened as a measurement-capacity candidate before any of
its synthetic Thai calibration outputs are observed because:

1. it is a current-generation open-weight native multimodal checkpoint;
2. its approximately 4.66-billion-parameter checkpoint is compact enough to
   justify a direct Tesla T4 feasibility test at batch size 1;
3. the official model card reports strong visual-language and OCR benchmark
   capability, which is a screening rationale rather than evidence for the
   present Thai construct;
4. the official Hugging Face implementation exposes a distinct Vision
   Encoder, patch embedding, spatial merger, and LLM input positions;
5. model, processor, tokenizer, software, and decoding revisions can be pinned
   for reproducible local/Kaggle inference;
6. the post-merger representation is inspectable and therefore compatible in
   principle with a future, separately authorized post-encoder Token Pruning
   intervention;
7. the checkpoint is Apache-2.0 licensed; and
8. Stage 0 will use FP16 without quantization if the T4 runtime proves feasible.

None of these reasons depends on the magnitude, direction, or component pattern
of a Qwen3.5 calibration result. A negative Stage 0 result remains valid.

## Pinned identity before inference

| Item | Pre-registered value |
|---|---|
| Model ID | `Qwen/Qwen3.5-4B` |
| Model revision | `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` |
| Processor revision | `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` |
| Tokenizer revision | `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` |
| Model class | `Qwen3_5ForConditionalGeneration` |
| Processor class | `Qwen3VLProcessor` |
| Tokenizer class | `Qwen2Tokenizer` |
| Tested Transformers target | `5.12.0` |
| Lowest release with the model source verified in this audit | `5.2.0` |
| Runtime dtype target | `float16` |
| Runtime attention target | `sdpa` |
| Runtime device target | Kaggle `NVIDIA Tesla T4 16 GB` |
| Quantization | forbidden for the primary Stage 0 attempt |
| License | Apache-2.0 |

The official model card asks users to use the latest Transformers rather than
declaring an exact minimum release. Therefore `5.2.0` is recorded only as the
lowest tagged source release located in this audit; `5.12.0` is the exact
version selected for runtime validation. Runtime compatibility, not version
number alone, remains a mandatory smoke condition.

## Architecture hypothesis to verify at runtime

Official config and processor inspection predict the following for the frozen
448 x 448 input:

```text
448 x 448 image
  -> 16 x 16 spatial patchification
  -> image_grid_thw = [1, 28, 28]
  -> 784 pre-merge representations
  -> 2 x 2 spatial merge
  -> 196 post-merge representations / LLM image positions
```

This calculation is not accepted as the observed visual-token count. The
engineering smoke must reconcile the grid formula, processor placeholder
count, runtime merger output, and actual LLM input positions. The measurement
boundary is provisionally the Vision Encoder merger output consumed at the
language-model image positions.

## Frozen scientific inputs

The comparison preserves the existing Stage 0 calibration allocation,
candidate strings, component labels, provisional lexical metadata, four
centered font-size conditions, both displayed members, blank controls, prompt
semantics, exact A/B parser, deterministic order, and seed. The Qwen3.5
assistant-boundary token mapping must be inspected independently; Qwen2.5 token
IDs are not assumed.

## Fail-closed sequence

1. Run repository tests and preflight from the exact clean inference commit.
2. Load the pinned model on T4 in FP16 and record load/one-call memory and
   latency.
3. Run the preselected 40-call engineering smoke and exact rerun.
4. Continue only if model identity, one-token A/B output, logits, visual-token
   accounting, and reproducibility all pass.
5. Run two exact 1,000-observation calibration passes; use the second pass only
   as a reproducibility audit.
6. Stop for human review without opening locked validation or running any
   compression intervention.

## Prohibited retrospective rationale

Qwen3.5 accuracy, image gain, bias, or a convenient component pattern may not
be used after the fact to rewrite why this backbone was selected. A later
backbone decision must weigh measurement adequacy, architectural inspectability,
reproducibility, and compute feasibility together.
