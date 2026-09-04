# Research Specification

> Status: pre-registration draft. Scientific gates and the direction of H1
> remain human-owned decisions.

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

## 4. H1 directionality — human decision required

The current Claims Registry permits the non-directional hypothesis:

> Distinctions involving Thai orthographic components may degrade differently
> as visual-token budget changes.

An earlier draft proposed the directional form:

> Micro-features may exhibit greater degradation than base-character
> distinctions.

The directional form is `PENDING_HUMAN_DECISION`. Until it is justified from
literature and frozen by the human researcher, it must not be used as a
confirmatory directional hypothesis. The non-directional interaction remains
the safe primary question.

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
