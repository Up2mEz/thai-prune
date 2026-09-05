# VLM Architecture Assumptions and Measurement Points

> Purpose: define exactly what this project means by image resolution, visual patches, visual representations, visual tokens, and compression points. This file prevents experiments from mixing different mechanisms under one label.

## 1. Scope

This document describes the architecture concepts needed for the research project on orthographic micro-feature robustness under visual-token compression in Vision-Language Models (VLMs).

This is **not** a claim that every VLM uses the same architecture. Model-specific details must be verified from the exact model revision and implementation used in each experiment.

The current first target is expected to be a Qwen-family VLM, but the codebase must not assume that all models behave identically.

---

## 2. Conceptual pipeline

The project uses the following conceptual pipeline:

```text
Input image
   ↓
Image preprocessing / resizing
   ↓
Patchification or equivalent visual input construction
   ↓
Vision encoder
   ↓
Optional spatial merge / projector / connector
   ↓
Visual representations supplied to the language model
   ↓
Language model
   ↓
Generated answer
```

The exact placement of the projector, merger, resampler, token selector, or pruning module depends on the model.

---

## 3. Definitions used in this project

### 3.1 Input resolution
The spatial resolution of the image after the preprocessing step that actually determines what the vision encoder receives.

Do not confuse:
- file size in MB,
- original image dimensions,
- preprocessed image dimensions,
- number of visual representations passed to the language model.

These are different quantities.

### 3.2 Patch
A local image region created by the model's patchification or equivalent input process.

A patch is not automatically equivalent to one final visual token supplied to the language model.

### 3.3 Visual representation
A hidden representation produced by the visual branch of the model.

This term is intentionally broad because different model families expose different intermediate representations.

### 3.4 Visual-token budget
Unless an experiment explicitly states otherwise:

> **Visual-token budget means the number of visual representations supplied to the language-model side after the model's vision-side encoding / merging / connector stage and before language generation.**

If a method removes patches or tokens **before** the vision encoder, the experiment must describe it explicitly as a pre-encoder or pre-ViT reduction method rather than silently treating it as the same intervention.

### 3.5 Compression ratio
A derived quantity only.

Every experiment must also record the **actual visual-token count**. Ratios such as 50% are not sufficient by themselves.

---

## 4. Compression families must be separated

### A. Resolution reduction

```text
Image
 ↓
Reduce image resolution
 ↓
Vision encoder
 ↓
Visual representations
 ↓
LLM
```

Interpretation:
- fine visual evidence may disappear before visual encoding;
- this tests sensitivity to loss of input detail;
- this is not equivalent to post-encoder token pruning.

### B. Pre-encoder patch/token reduction

```text
Image / patches
 ↓
Select or remove visual inputs
 ↓
Vision encoder
 ↓
LLM
```

Interpretation:
- the vision encoder never processes the removed content;
- report this intervention separately from post-encoder pruning.

### C. Post-encoder visual-token pruning

```text
Image
 ↓
Vision encoder receives full selected image resolution
 ↓
Visual representations
 ↓
Select / remove representations
 ↓
LLM
```

Interpretation:
- visual encoding happened before pruning;
- useful for asking whether important encoded evidence is discarded downstream.

### D. Token merging / pooling

```text
Visual representations
 ↓
Combine multiple representations
 ↓
Fewer representations
 ↓
LLM
```

Interpretation:
- information is combined rather than simply deleted;
- do not report merging and pruning as the same mechanism.

---

## 5. Critical-region mapping

Controlled minimal pairs may provide a pixel-level difference mask describing which rendered pixels differ between two stimuli.

Example:

```text
กี  ↔  กี่
```

The difference mask can be used to identify image regions spatially associated with the distinguishing feature.

### Important limitation

Do **not** interpret a post-encoder token as containing information only from the patch where it originated.

After attention and other mixing operations inside a vision transformer, a representation can contain information from multiple spatial locations.

Therefore the project may claim:

> "This token/representation is spatially associated with or originates from a critical region."

It must not claim without additional evidence:

> "The critical feature exists only inside this token."

---

## 6. Model-adapter requirements

Every supported VLM adapter should expose, where technically possible:

```text
predict(...)
get_preprocessed_image_shape(...)
get_visual_token_count(...)
get_visual_stage_metadata(...)
```

Optional research interfaces:

```text
extract_visual_representations(...)
apply_compression(...)
map_image_region_to_visual_grid(...)
```

Do not make research code depend directly on one Hugging Face class throughout the repository.

---

## 7. Model-specific architecture record

For each evaluated model, record:

- model name;
- exact revision / commit if available;
- library version;
- image processor revision;
- input resizing behavior;
- patch size or equivalent;
- spatial merge / resampling behavior;
- location at which the project measures visual-token count;
- location at which each compression method intervenes;
- whether the intervention requires modification of model internals.

These facts must be verified from code or official model documentation for the exact revision used.

### 7.1 Current sequential candidate strategy

The first candidate is `Qwen/Qwen2.5-VL-3B-Instruct`, selected for an initial
feasibility audit based on architecture observability, existing compression
implementation coverage, model maturity, and plausible local resource use.
This is not evidence that the model will pass Stage 0.

`Qwen/Qwen3-VL-2B-Instruct` is a secondary candidate only. It may be opened if
the primary candidate fails local execution, leaves token accounting
ambiguous, fails full-information measurement after engineering defects are
excluded, or a documented methodological requirement needs Qwen3-VL.

Backbone selection must not use the magnitude or direction of a degradation
effect. Opening the secondary candidate requires a Decision Log entry.

For Qwen3-VL, the architecture record must distinguish primary LLM visual
positions from additional multi-level visual features such as `DeepStack`.
Do not collapse these into a single count without an explicit definition and
compute interpretation.

The current primary-backbone audit is recorded in
`docs/architecture/QWEN2_5_VL_3B.md`. That record is architecture feasibility
evidence only and must not be cited as Stage 0 measurement validity.

Step 3 is `COMPLETE` after the human smoke-image approval recorded on
2026-09-06 in `docs/DECISION_LOG.md`. This completion establishes only primary
backbone engineering feasibility; it does not establish Stage 0 validity.

### 7.2 Kaggle execution backend

The minimal Kaggle Tesla T4 backend is integrated into `main`. Its exact proof
run and provenance boundaries are recorded in
`docs/architecture/KAGGLE_BACKEND.md` with status
`KAGGLE_BACKEND_FEASIBLE_PROPOSED`. The proposal is engineering-only and does
not authorize an experiment or transfer smoke-control evidence to any
scientific hypothesis.

The operational runtime profile targets `refs/heads/main`. Every future Kaggle
run must pin the exact remote commit and preserve config, environment, model
revision, seed where applicable, and actual token counts in immutable
artifacts.

### 7.3 Stage 1A measurement boundary

Stage 1A changes processor-controlled input resolution. It must record:

- requested resolution/pixel budget;
- actual preprocessed dimensions;
- patch/grid metadata;
- actual visual representations passed to the language-model side; and
- model-specific rounding or minimum/maximum constraints.

The resulting actual token count is an outcome of Resolution Reduction. It
does not make Stage 1A a post-encoder pruning experiment.

---

## 8. Architectural claims that are currently forbidden

Until directly supported by experimental evidence, do not claim that:

- Thai tone marks are stored in specific individual tokens;
- pruning is the cause of Thai OCR failure;
- a failure observed in one Qwen model generalizes to all VLMs;
- reducing image resolution and pruning post-encoder tokens are interchangeable;
- equal token counts always imply equal compute cost across different compression locations.

---

## 9. Fair-comparison principle

When comparing compression approaches, match the resource constraint appropriate to the question.

At minimum record:
- actual visual-token count;
- latency;
- peak memory when feasible;
- FLOPs or an explicit compute proxy when feasible.

If methods intervene at different layers, final token count alone may not provide a fair compute comparison.

---

## 10. Change control

Any discovery that changes the architecture interpretation used by an existing experiment must be recorded in `docs/DECISION_LOG.md`.

Do not silently reinterpret old runs under a new token definition.
