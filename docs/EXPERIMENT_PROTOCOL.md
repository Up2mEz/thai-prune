# Experiment Protocol

> Status: living protocol before the main experiment. Changes that affect scientific interpretation must be logged in `docs/DECISION_LOG.md`.

## 2026-09-12 Thai-specific OCR adaptation amendment — S0 only

Status: `FINAL_LOCKED_PANEL_AUTHORIZATION_READY`.
The overall interaction design, FULL-validity criteria, one-shot 6,400-call
Input Resolution Reduction panel, target-aware random effects, estimator
diagnostics/fallback, metrics, and exclusions are frozen. No locked image
generation, locked inference, or reduced-resolution inference occurred in this
amendment. Execution still requires an explicit human run order.

The primary comparison is **base OCR VLM versus Thai-specialized OCR
descendant**. Do not describe it as general VLM versus OCR-specialized VLM.
The research question is: “Does Thai-specific OCR adaptation change the
degradation curve under controlled visual-information reduction?” The frozen
primary interaction is non-directional `MODEL x BUDGET`; S0 measured only
full-information baseline capacity and did not test that interaction.

The complete frozen design is in `OVERALL_MODEL_BUDGET_FREEZE.md`. The future
budget variable is categorical actual LLM image-placeholder count at
`256/196/121/64`, realized by processor targets `448/392/308/224` using Input
Resolution Reduction only. `MODEL x BUDGET x COMPONENT` is
descriptive/diagnostic. The prepared one-shot locked-panel protocol remains
unauthorized. It forbids a FULL-only run, conditional continuation, and access
to intermediate scientific outcomes.

The Typhoon branch is `NOT_PURSUED_DUE_TO_USAGE_TERMS`; no Typhoon inference,
smoke, compression, or benchmarking is authorized. The broader historical
model-agnostic question remains in the record, while the active confirmatory
question is now frozen for PaddleOCR-VL-1.6 and Wayu-Paxa. This pair passed the
engineering smoke and completed the authorized S0 open-calibration baseline.
The 45,723-page synthetic training set is not assumed to be the only checkpoint
difference.

The earlier 25-`pair_id`, 400-call Typhoon proposal below is historical and is
not transferred to Paddle/Wayu. The current S0 contract excludes the five
engineering-smoke pairs and uses the remaining 95 open-calibration pairs only.

For provenance, the historical non-executable proposal required prompt
selection from a separate non-scientific smoke before S0 outcomes. Its
preferred contract applied the exact pinned official Typhoon
OCR prompt to both models with identical deterministic decoding and one
parser. If the base cannot execute that interface in the smoke, a predeclared
two-contract sensitivity design may compare a shared semantic OCR contract
with each model's frozen interface; prompt/interface effects must then be
reported separately from checkpoint capability.

Before any authorized fallback run, the current terms/model cards must be
snapshotted because the terms may change. `TERMS_CLEAR` in the source-only
audit is not permanent legal advice.
Before S1, processor-only and runtime evidence must map requested resolution to
actual grid, pre-merge patches, post-merge primary visual positions, DeepStack
accounting, and LLM image-placeholder positions. Resolution Reduction,
pre-encoder reduction, post-encoder Token Pruning, Token Merging/Pooling, and
dynamic decoding-time access remain distinct interventions.

The historical Typhoon contract is `SPECIALIZATION_PIVOT_REVIEW.md`; the
fallback source-only audit is `FALLBACK_PAIR_CLEARANCE.md`. This section does
not authorize execution or alter the active stages below.

## 1. Purpose

This protocol defines how experiments are conducted so that observed effects can be attributed as cleanly as possible to the intended manipulation rather than to prompt variation, rendering artifacts, language priors, uncontrolled model changes, or selective analysis.

The project follows the research stages and hypotheses defined in `docs/RESEARCH_SPEC.md`.

---

## 2. Core rule

**Do not optimize the experiment to make the hypothesis succeed.**

A failed hypothesis is a valid research outcome.

No later research stage may be treated as scientifically justified until the prerequisite gate is approved in `docs/DECISION_LOG.md`.

---

## 3. Experimental stages

### Stage 0 — Measurement validity
Goal: verify that the dataset, task, prompt, parser, model adapter, and metrics work before compression is studied.

Primary question:
> Can the uncompressed/full-information model reliably discriminate the controlled stimuli?

### Stage 1 — Overall differential degradation
Goal: determine whether the BASE and SPECIALIZED checkpoints have different
exact-transcription degradation curves as actual visual-information budget
decreases under Input Resolution Reduction. Component curves are
descriptive/diagnostic.

### Historical Stage 1A Resolution Sensitivity Pilot — superseded for the frozen Paddle/Wayu design
The earlier pilot concept is preserved as history. The frozen first
Paddle/Wayu budget experiment is the overall `MODEL x BUDGET` design in
`OVERALL_MODEL_BUDGET_FREEZE.md`, pending final one-shot panel authorization.
FULL validity is evaluated only after the complete panel is immutable.

Stage 1A is not the main Stage 1 experiment and cannot approve Gate 1. It does
not test post-encoder Token Pruning and cannot reject H3 because only one
intervention family is manipulated.

### Stage 2 — Confound control
Goal: determine whether apparent component differences can be explained by visual properties such as critical-region size, stroke thickness, contrast, or patch alignment.

### Stage 3 — Failure localization
Goal: compare input-resolution reduction with post-encoder visual-token reduction and other clearly separated intervention families.

### Stage 4 — Existing-method evaluation
Goal: determine whether strong compatible existing compression methods already solve the observed failure.

### Stage 5 — New method
Allowed only if Stage 4 supports a meaningful unresolved gap.

### Stage 6 — External validity
Goal: test whether findings extend beyond synthetic controlled data and beyond a single model architecture.

---

## 4. Controlled stimulus design

### 4.1 Minimal-pair principle
Within a pair, change only the target distinction whenever technically possible.

Registered Stage 0 component labels are:

- `BASE_CHARACTER`: the base character changes;
- `TONE_MARK`: a tone mark changes without an upper vowel in the registered
  pair context;
- `UPPER_VOWEL_VARIANT`: the upper-vowel variant changes;
- `LOWER_VOWEL_VARIANT`: the lower-vowel variant changes;
- `STACKED_TONE_MARK`: an upper vowel is present in both members and only the
  tone mark changes, for example `กี` versus `กี่`.

The current `BASE_CHARACTER` candidates are admissible for Stage 0
measurement-validity testing. They are not assumed to be size-matched visual
controls for Stage 2; critical-region size and related confounds require a
separate Stage 2 assessment.

Specific pair inventories must be versioned and reviewed before the main run.

### 4.2 Required metadata per sample
At minimum:

```text
sample_id
pair_id
target_text
distractor_text
component_type
font_id
font_size
canvas_size
text_position
foreground/background specification
contrast measure
rendering engine/version
seed
difference_mask_path
critical_pixel_area
critical_bbox_width
critical_bbox_height
```

When feasible also record:

```text
stroke_thickness_estimate
critical-region centroid
patch/grid alignment metadata
Unicode code points
normalization form
lexical_status for each pair member: REAL, CONSTRUCTED, or UNCERTAIN
```

### 4.3 Dataset diversity
The full dataset must vary rendering conditions rather than using only one font/background/size.

Variation should be controlled and reproducible, including appropriate combinations of:
- font;
- font size;
- text position jitter;
- foreground/background contrast;
- rendering/anti-aliasing conditions if relevant.

### 4.4 Unit of analysis and repeated rendering

The primary independent sampling/analysis unit is `pair_id`, representing a
linguistic minimal pair. A model response to a rendered stimulus is an
observation, not an independent linguistic unit.

Multiple fonts, sizes, positions, rendering seeds, candidate orders, and
budgets for the same `pair_id` are repeated observations. Analyses and
uncertainty estimates must preserve this dependence through within-pair
contrasts, cluster bootstrap by `pair_id`, or an appropriate hierarchical
model. Do not report the number of rendered images as the independent sample
size.

### 4.5 Exclusion policy
Do not remove samples because they weaken the expected result.

Permitted exclusions must be defined before the main analysis, e.g.:
- rendering failure;
- invalid Unicode sequence generated by a bug;
- corrupted file;
- model execution failure unrelated to the sample content.

Every exclusion must remain visible in raw logs with a reason code.

---

## 5. Unicode and Thai-text integrity

Before inference:
- record Unicode code points;
- record normalization form;
- verify that rendered target and distractor correspond to intended strings;
- ensure the evaluation parser does not accidentally normalize away the tested distinction.

Unit tests are required for representative combining-mark cases.

---

## 6. Primary task: forced-choice discrimination

The primary controlled task is a forced-choice visual discrimination task unless `RESEARCH_SPEC.md` is explicitly revised.

Example:

```text
Which text appears in the image?
A. กี
B. กี่
```

Requirements:
- randomize candidate order deterministically from the run seed;
- keep prompt wording fixed within a registered experiment;
- use deterministic or maximally reproducible decoding where supported;
- save raw model output before parsing;
- parser failures must be recorded separately from incorrect visual decisions.

Rationale:
The task reduces, but does not eliminate, contamination from unrestricted text generation and language priors.

---

## 7. Secondary tasks

Secondary analyses may include:
- exact OCR accuracy;
- character error rate (CER);
- component deletion rate;
- component substitution rate;
- critical-region token/representation retention when measurable.

Secondary outcomes must not silently replace the registered primary outcome after results are observed.

---

## 8. Language-prior controls

Because an LLM may infer text from linguistic plausibility rather than visual evidence alone:
- include stimuli with reduced semantic predictability when linguistically valid;
- balance target/distractor frequencies;
- randomize A/B ordering;
- avoid prompts that reveal the expected distinction;
- analyze real-word and low-semantic-predictability subsets separately when available.

Do not claim that forced-choice accuracy is a pure measurement of visual perception; it is only a more controlled proxy.

Blank-image controls are `LANGUAGE_CANDIDATE_BIAS_BLANK` controls. Because a
blank image has no naturally correct visual answer, these controls report
candidate/order/lexical-status preference and parser behavior, not OCR or
visual accuracy. They must never enter the visual-accuracy denominator.

Constructed strings are permitted and must not be excluded merely because
they are nonwords. Preserve `lexical_status` so `REAL`, `CONSTRUCTED`, and
`UNCERTAIN` subsets can be analyzed separately without outcome-driven
redefinition of the primary analysis.

---

## 9. Compression intervention protocol

Every compression configuration must record:
- compression family;
- location in the architecture;
- requested budget;
- actual visual-token count;
- preprocessed image dimensions;
- method-specific parameters.

### 9.1 Budget grid
The historical pilot proposal used a coarse nominal grid such as:

```text
100%, 75%, 50%, 25%
```

The active Paddle/Wayu grid is now frozen at actual LLM image-position counts
`256/196/121/64` before locked output. Do not replace these with nominal
percentages.

For Stage 1A, the grid is selected using processor/token mapping only, before
opening predictions. If processor rounding maps requested budgets to duplicate
actual token counts, revise and freeze the grid before inference. Do not revise
the grid because of observed task outcomes.

### 9.2 Never equate percentage with mechanism
A 50% input-resolution intervention and a 50% post-encoder token-retention intervention are different experimental conditions even if they yield similar final visual-token counts.

---

## 10. Stage 0 calibration and validity checks

Before running Stage 1A or any main Stage 1 experiment:
- verify dataset rendering visually on a sampled subset;
- verify candidate randomization;
- verify parser accuracy on known outputs;
- verify raw prediction storage;
- verify actual token counting;
- verify reproducibility from a fixed seed;
- measure full-information baseline by component type and rendering condition.

Stage 0 calibration estimates baseline and per-component precision, parser
behavior, candidate-order sensitivity, negative-control separation, and
reproducibility. It must also assess whether the full-information ceiling and
headroom are adequate for the smallest later-stage effect the study intends to
detect.

Gate 0 criteria must be derived from these calibration estimates and the
intended Stage 1 estimand, documented with rationale, and frozen by the human
researcher before locked Stage 0 validation. Do not invent universal numeric
requirements, and never choose or relax a threshold using Stage 1A or later
compression results.

For the current Advisor Readiness measurement plan, the human-selected
provisional smallest effect of interest is a 10 percentage-point absolute
differential degradation. It is not a publication threshold, evidence that
the effect exists, or permission to classify smaller effects as absent. Any
change that affects measurement adequacy must be logged and re-evaluated
before later-stage evidence is collected.

---

## 11. Active main statistical question

The active question is not simply whether accuracy decreases. It is whether
degradation differs by MODEL as budget changes after accounting for different
FULL baselines.

Conceptually:

```text
exact_correct
~ MODEL * BUDGET
+ FONT + FONT_SIZE + MEMBER + COMPONENT
+ (1 | pair_id) + (1 | pair_id:member)
```

The confirmatory interaction is `MODEL x BUDGET`; `BUDGET` is a categorical
four-level factor. The global omnibus is the registered 3-df likelihood-ratio
test against the model without the interaction. Report all three frozen
`DID_196`, `DID_121`, and `DID_64` marginal probability-scale contrasts with
pair-clustered uncertainty and Holm multiplicity control. The exact GLMM
diagnostics and direction-independent fallback are in
`stage0/PADDLE_WAYU_PRIMARY_ANALYSIS_SPEC.md`. Component interactions are
descriptive/diagnostic.

Do not treat a visually different graph as statistically established evidence by itself.

---

## 12. Stage 2 confound controls

At minimum investigate:
- critical-region pixel area;
- bounding-box dimensions;
- stroke thickness if reliable;
- contrast;
- font;
- font size;
- position;
- alignment relative to visual patch/grid boundaries when recoverable.

Important distinction:

> Compare the size of the **critical visual evidence used to distinguish a pair**, not naively the total size of a consonant versus the total size of a tone mark.

---

## 13. Fair comparison for existing methods

When comparing methods:
- use the same dataset split;
- use the same model revision where compatible;
- use the same prompt and decoding;
- compare at matched or clearly reported actual token budgets;
- additionally report compute/memory/latency when layer placement makes token count alone misleading;
- document compatibility limitations rather than omitting strong baselines without explanation.

---

## 14. Run immutability

Every experiment run must create a new output directory.

Never overwrite an existing run.

Each run must retain:

```text
resolved_config
raw_predictions
parsed_predictions
metrics
logs
environment metadata
git commit
model revision
seed
actual visual-token counts
```

The metrics must be recomputable from stored predictions.

---

## 15. Required run status

Every run ends with one of:

```text
VALID
VALID_WITH_WARNINGS
INVALID
```

An invalid run must not be used as evidence for a gate decision.

## 15.1 Evidence status in reports

Run validity and evidence status are separate. Advisor-facing reports must use:

- `Tested` — direct valid locked evidence exists for the stated question and
  intervention;
- `Preliminary/Pilot` — valid exploratory evidence exists but is not final or
  gate evidence;
- `Not Tested` — no direct valid experiment exists;
- `Blocked` — prerequisites, compatibility, compute, or data prevent testing.

Evidence from one compression family cannot change another family from
`Not Tested` to `Tested`.

---

## 16. Human decision rule

Codex may:
- calculate metrics;
- summarize evidence;
- identify protocol violations;
- recommend PASS / FAIL / INCONCLUSIVE.

Codex must **not** autonomously approve a scientific gate that changes the research direction.

The human researcher records the final decision in `docs/DECISION_LOG.md`.

---

## 17. Reproducibility checklist

Before calling a stage complete, verify:

- [ ] exact model revision recorded
- [ ] exact code commit recorded
- [ ] dependency/environment metadata recorded
- [ ] dataset manifest/version recorded
- [ ] seed recorded
- [ ] raw predictions preserved
- [ ] actual token counts preserved
- [ ] exclusions preserved with reasons
- [ ] metrics reproducible from raw outputs
- [ ] protocol deviations documented
- [ ] claims checked against `docs/CLAIMS.md`
