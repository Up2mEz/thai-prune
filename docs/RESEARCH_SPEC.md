# Research Specification

> Status: pre-registration draft. Scientific gates remain human-owned
> decisions; H1 directionality was frozen on 2026-09-04.

## 2026-09-12 Thai-specific OCR adaptation study — S0 authorized

Status: `APPROVED_FOR_S0_OPEN_CALIBRATION_BASELINE_ONLY`.

The revised research question is:

> Does Thai-specific OCR adaptation change robustness to controlled
> visual-information reduction?

The current comparison is **base OCR VLM versus Thai-specialized OCR
descendant**, not general VLM versus OCR-specialized VLM. `MODEL` represents
`PaddlePaddle/PaddleOCR-VL-1.6` as the base OCR model and
`wayu-ai/wayu-paxa-ocr-zero` as its declared Thai-specific OCR adaptation.
PaddleOCR-VL-1.6 is already an OCR/document-recognition model.

The proposed primary hypothesis is a non-directional `MODEL x BUDGET`
interaction. `MODEL x BUDGET x COMPONENT` is conditional secondary/descriptive
work until baseline measurement capacity is adequate. The 45,723-page
synthetic training set must not be described as the only difference between
the checkpoints. The fallback terms gate,
provenance limits, compression boundaries, and exact proposed non-scientific
workload are in `FALLBACK_PAIR_CLEARANCE.md`. The historical Typhoon proposal
remains in `SPECIALIZATION_PIVOT_REVIEW.md`.

The human-approved S0 is open-calibration full-information baseline measurement
only. It does not test `MODEL x BUDGET`, compression robustness, or authorize
locked validation. `Gate 0` remains `NOT_RUN`; prior Qwen2.5 and Qwen3.5
evidence retains only its original diagnostic scope.

## 1. Research objective

Evaluate whether controlled Thai orthographic distinctions show different
robustness as the amount of visual information supplied to a Vision-Language
Model changes, while separating measurement artifacts, generic visual-detail
effects, and distinct compression intervention families.

This project does not assume that the effect exists, that Token Pruning causes
it, or that a new method is required.

## 2. Current contribution framing

The current candidate contribution is an evaluation/diagnostic study. It may
advance only if the literature evidence in `LITERATURE.md` remains compatible
with a defendable gap and Stage 0 establishes valid measurement.

Possible outcomes are:

- continue a Thai orthographic diagnostic;
- pivot to generic micro-detail robustness;
- report an inconclusive feasibility result; or
- stop because novelty, measurement, or resources are insufficient.

## 3. RQ1 — Differential degradation

When actual visual-token budget decreases within a clearly named intervention
family, do orthographic component categories have different degradation
curves?

The primary RQ is non-directional. It asks about a `component_type × budget`
interaction, not whether Thai tone marks necessarily degrade faster.

## 4. H1 directionality — frozen non-directional

The current Claims Registry permits the non-directional hypothesis:

> Distinctions involving Thai orthographic components may degrade differently
> as visual-token budget changes.

The human researcher approved the non-directional `component_type × budget`
interaction as H1 on 2026-09-04. An earlier draft proposed the directional
form:

> Micro-features may exhibit greater degradation than base-character
> distinctions.

The directional form is not registered and must not be used as a confirmatory
hypothesis. It would require separate literature justification and explicit
change control before any locked experiment.

## 5. Related hypotheses

- **H2:** Any apparent component effect may be explained by properties of the
  distinction-critical visual evidence. Status: `UNTESTED`.
- **H3:** Resolution Reduction and post-encoder token reduction may produce
  different degradation patterns. Status: `UNTESTED`.
- **H4:** Existing OCR/text-aware compression methods may not fully preserve
  distinction-critical evidence. Status: `UNTESTED`; literature-sensitive.

These are hypotheses from `CLAIMS.md`, not established facts.

## 6. Estimand and unit of analysis

For a registered intervention family, the central estimand is the change in
forced-choice correctness across actual visual-token budgets and whether that
change differs by `component_type`.

- An **observation** is one model response for one rendered stimulus under one
  model, budget, prompt, and candidate order.
- The primary independent sampling/analysis unit is the linguistic minimal
  pair identified by `pair_id`.
- Font, size, position, rendering seed, candidate order, and budget create
  repeated observations of a pair; they do not create new independent pairs.
- Uncertainty must preserve pair clustering through within-pair contrasts,
  cluster bootstrap by `pair_id`, or an appropriate hierarchical model.

The registered component labels are `BASE_CHARACTER`, `TONE_MARK`,
`UPPER_VOWEL_VARIANT`, `LOWER_VOWEL_VARIANT`, and `STACKED_TONE_MARK`.
`STACKED_TONE_MARK` changes only the tone mark while an upper vowel is present
in both pair members. The current `BASE_CHARACTER` candidates are Stage 0
measurement stimuli and are not presumed size-matched for Stage 2.

## 7. Stage and gate map

### Stage 0 — Measurement validity

Stage 0 asks whether the selected model, controlled dataset, forced-choice
task, parser, and metrics can measure the intended distinctions at
full-information settings.

1. `Stage 0 calibration` estimates measurement quality.
2. The human researcher freezes justified Gate 0 criteria.
3. `Stage 0 locked validation` evaluates those criteria on locked data.
4. The human researcher records `PASS`, `FAIL`, or `INCONCLUSIVE`.

No compression outcome may be used to select Gate 0 thresholds.

### Stage 1A — Resolution Sensitivity Pilot

Stage 1A is a conditional, non-gate pilot allowed only after Gate 0 is
human-approved `PASS`. It changes input resolution through the official image
processor and records the resulting actual visual-token counts.

Stage 1A evidence is `Preliminary/Pilot`. It cannot approve Gate 1, reject a
post-encoder Token Pruning hypothesis, or test H3. Post-encoder compression
remains `Not Tested` until directly manipulated.

### Gate 1 — Differential degradation

Gate 1 requires a registered main experiment with an explicitly named
intervention family, predefined uncertainty/effect criteria, per-component
curves, and a `component_type × budget` analysis.

- `PASS`: evidence supports a meaningful interaction within the registered
  intervention scope.
- `FAIL`: no meaningful interaction is supported within that scope.
- `INCONCLUSIVE`: measurement precision or evidence is insufficient.

A Gate 1 result for one intervention family must not be generalized to another.

### Gates 2–6

- Gate 2: evaluate visual-size and other major confounds.
- Gate 3: directly compare intervention families for failure localization.
- Gate 4: determine whether a meaningful unresolved failure remains after fair
  evaluation of strong compatible existing methods.
- Gate 5: consider a new method only after human-approved Gate 4 `PASS` in the
  sense defined above.
- Gate 6: evaluate real-world and cross-architecture external validity.

Exact evidence requirements remain in `EXPERIMENT_PROTOCOL.md` and
`DECISION_LOG.md`.

## 8. Claim boundary

- Synthetic Qwen evidence is scoped to the exact model, revision, stimuli, and
  intervention tested.
- Resolution Reduction is not post-encoder Token Pruning.
- Statistical evidence of an interaction is not automatically evidence of an
  orthographic mechanism or practical importance.
- Codex may recommend gate outcomes; only the human researcher approves them.
