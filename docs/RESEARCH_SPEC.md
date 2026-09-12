# Research Specification

> Status: pre-registration draft. Scientific gates remain human-owned
> decisions; H1 directionality was frozen on 2026-09-04.

## 2026-09-12 Thai-specific OCR adaptation study — S0 authorized

Status: `REVISED_OVERALL_MODEL_BUDGET_DESIGN_PENDING_FINAL_AUTHORIZATION`.
The non-directional overall `MODEL x BUDGET` design, FULL-validity criteria,
one-shot 6,400-call panel, target-aware random effects, primary/fallback
analysis, and Input Resolution Reduction pipeline are frozen. No locked image
generation, locked inference, or reduced-resolution inference is authorized.

The revised research question is:

> Does Thai-specific OCR adaptation change the degradation curve under
> controlled visual-information reduction?

The current comparison is **base OCR VLM versus Thai-specialized OCR
descendant**, not general VLM versus OCR-specialized VLM. `MODEL` represents
`PaddlePaddle/PaddleOCR-VL-1.6` as the base OCR model and
`wayu-ai/wayu-paxa-ocr-zero` as its declared Thai-specific OCR adaptation.
PaddleOCR-VL-1.6 is already an OCR/document-recognition model.

The frozen primary hypothesis is a non-directional `MODEL x BUDGET`
interaction. `MODEL x BUDGET x COMPONENT` is descriptive/diagnostic under the
current 19-cluster-per-component design. The 45,723-page
synthetic training set must not be described as the only difference between
the checkpoints. The fallback terms gate,
provenance limits, compression boundaries, and exact proposed non-scientific
workload are in `FALLBACK_PAIR_CLEARANCE.md`. The historical Typhoon proposal
remains in `SPECIALIZATION_PIVOT_REVIEW.md`.

S0 remains open-calibration full-information baseline measurement only. It did
not test `MODEL x BUDGET` or compression robustness. The historical staged
`Gate 0` execution remains `NOT_RUN` and has been replaced prospectively by a
FULL-validity condition evaluated only after the whole locked panel is
immutable. Prior Qwen2.5 and Qwen3.5 evidence retains only its original
diagnostic scope.

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

## 3. Active RQ1 — Differential degradation by model

Does the change in exact transcription across actual visual-token budgets
differ between the BASE OCR VLM and its Thai-specialized OCR descendant?

The primary RQ is non-directional; the active primary is frozen non-directional
and asks about `MODEL x BUDGET`. Component
curves remain descriptive/diagnostic. The earlier `component_type x budget`
question below is preserved as research history but is not the active
confirmatory primary hypothesis under the current dataset.

## 4. Historical component H1 — non-directional, now descriptive

The current Claims Registry permits the non-directional hypothesis:

> Distinctions involving Thai orthographic components may degrade differently
> as visual-token budget changes.

The human researcher approved the non-directional `component_type x budget`
interaction as H1 on 2026-09-04. On 2026-09-13, the human reviewer froze
`MODEL x BUDGET` as the active primary and retained component results as
descriptive/diagnostic. An earlier draft proposed the directional form:

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

For the active registered Input Resolution Reduction design, the central
estimand is whether change in exact transcription correctness across actual
LLM image-position budgets differs by `MODEL`.

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

1. `Stage 0 calibration` estimates measurement quality on open data.
2. The human researcher freezes justified FULL-validity criteria and the whole
   confirmatory panel before any locked outcome.
3. One authorized one-shot locked panel executes all four budgets without
   intermediate scientific outcome access.
4. After the panel is immutable, the FULL condition is evaluated. Failure
   makes the overall `MODEL x BUDGET` analysis `NOT_INTERPRETABLE`; PASS permits
   the already-frozen primary analysis.

No compression outcome may be used to select Gate 0 thresholds.

### Historical Stage 1A Resolution Sensitivity Pilot — superseded for the frozen first experiment

The earlier Stage 1A concept was a conditional non-gate pilot. The amended
2026-09-13 freeze supersedes it with one registered Paddle/Wayu
`MODEL x BUDGET` Input Resolution Reduction panel. It remains blocked until
final human authorization; there is no conditional continuation after a
FULL-only run.

Stage 1A evidence is `Preliminary/Pilot`. It cannot approve Gate 1, reject a
post-encoder Token Pruning hypothesis, or test H3. Post-encoder compression
remains `Not Tested` until directly manipulated.

### Gate 1 — Overall differential degradation

Gate 1 requires the frozen Input Resolution Reduction experiment, predefined
uncertainty/effect criteria, and confirmatory `MODEL x BUDGET` analysis.
Per-component curves are descriptive/diagnostic under the current dataset.

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
