# Research Decision Log

> Human-owned scientific decision record. Codex may propose decisions and summarize evidence, but final gate approval belongs to the researcher.

## Status vocabulary

- `BLOCKED` — prerequisite gate not passed
- `NOT_RUN` — eligible but not evaluated
- `PILOTING` — exploratory work in progress; not final evidence
- `PASS_PROPOSED` — evidence suggests pass; awaiting human approval
- `FAIL_PROPOSED` — evidence suggests fail; awaiting human approval
- `INCONCLUSIVE_PROPOSED` — evidence insufficient; awaiting human decision
- `PASS` — human-approved gate pass
- `FAIL` — human-approved gate fail
- `INCONCLUSIVE` — human-approved decision that more evidence is required

---

# Gate 0 — Measurement validity

**Status:** NOT_RUN

## Question
Can the selected model + controlled dataset + forced-choice task reliably measure the intended distinctions without compression?

## Evidence required
- full-information baseline results;
- per-component accuracy;
- rendering spot-check;
- parser validation;
- Unicode validation;
- token-count validation;
- reproducibility check.

## Predefined decision criteria
To be proposed from Stage 0 calibration estimates of measurement precision,
ceiling/headroom, negative-control separation, and the intended Stage 1 effect.
The human researcher must freeze the criteria before locked Stage 0 validation.

Do not set or revise the threshold using Stage 1A or later compression results.

## Evidence
None yet.

## Decision
None yet.

## Consequence
- PASS → Stage 1A becomes eligible; a main Stage 1 experiment still needs
  its own registered intervention and analysis plan.
- FAIL → repair measurement setup; Stage 1A and main Stage 1 remain blocked.
- INCONCLUSIVE → improve Stage 0 precision or controls without weakening
  the frozen criteria; Stage 1A and main Stage 1 remain blocked.

---

# Stage 1A — Resolution Sensitivity Pilot

**Status:** BLOCKED

**Requires:** Gate 0 = human-approved PASS

## Question

Under processor-controlled Resolution Reduction, is there a preliminary
degradation signal worth studying in a later registered experiment?

## Evidence required

- grid frozen from processor/token mapping before predictions are opened;
- requested and actual visual-token budgets;
- per-component descriptive degradation curves;
- pair-clustered uncertainty estimates;
- raw-run audit and resource measurements.

## Decision authority

Stage 1A does not approve Gate 1. Its evidence status is `Preliminary/Pilot`.

## Consequence

- component-varying signal → consider a powered resolution experiment and a
  separately designed direct post-encoder study;
- generic signal → consider a generic micro-detail framing;
- no signal with wide uncertainty → resolution branch remains inconclusive;
- no signal with adequate precision → reduce or stop the resolution branch
  within the tested scope.

Post-encoder Token Pruning and H3 remain `NOT TESTED` in every Stage 1A outcome.

---

# Gate 1 — Differential degradation

**Status:** BLOCKED

**Requires:** Gate 0 = PASS

## Question
Does degradation across compression budgets meaningfully differ by orthographic component category?

## Evidence required
- registered budget grid;
- per-component degradation curves;
- uncertainty estimates;
- component × budget analysis;
- raw-run audit.

## Evidence
None yet.

## Decision
None yet.

## Consequence
- evidence of differential degradation → proceed to Stage 2;
- no meaningful differential degradation → stop Thai-component-specific interpretation and evaluate a generic compression/micro-detail framing;
- inconclusive → improve power or measurement before proceeding.

---

# Gate 2 — Visual-size/confound explanation

**Status:** BLOCKED

**Requires:** Gate 1 = PASS

## Question
Does the component-specific effect remain after accounting for critical visual evidence size and other major visual confounds?

## Evidence required
At minimum analysis of:
- critical pixel area;
- critical-region dimensions;
- contrast;
- font/font size;
- position / patch alignment when possible;
- stroke thickness when reliably measurable.

## Evidence
None yet.

## Decision
None yet.

## Consequence
- effect largely explained by generic visual properties → reframe as generic micro-detail robustness;
- residual component effect remains → orthographic structure becomes a plausible contributor, not yet a proven mechanism;
- inconclusive → do not advance a Thai-specific claim.

---

# Gate 3 — Failure localization

**Status:** BLOCKED

**Requires:** Gate 2 decision sufficient to justify localization work

## Question
Where does degradation primarily emerge under controlled interventions?

Compare clearly separated families such as:
- input-resolution reduction;
- pre-encoder reduction when included;
- post-encoder pruning;
- merging/pooling when included.

## Evidence
None yet.

## Decision
None yet.

## Consequence
Use wording such as `failure localization` unless stronger mechanistic evidence is collected.

---

# Gate 4 — Unresolved gap after existing methods

**Status:** BLOCKED

**Requires:** prior stages establish a meaningful failure worth testing

## Question
After fair evaluation of strong compatible existing methods, does a meaningful
unresolved failure remain?

## Evidence required
- strongest compatible baselines identified from current literature;
- fair matched-budget comparison;
- compatibility limitations documented;
- accuracy–resource trade-off reported.

## Evidence
None yet.

## Decision
None yet.

## Consequence
- PASS → a meaningful unresolved failure remains; Stage 5 may be considered
  only after human approval;
- FAIL → existing methods address the failure sufficiently; do not force a new
  method and retain an evaluation/analysis contribution;
- INCONCLUSIVE → Stage 5 remains blocked.

---

# Gate 5 — New-method value

**Status:** BLOCKED

**Requires:** Gate 4 = human-approved PASS, meaning that a meaningful unresolved
failure remains after fair evaluation of strong compatible existing methods.

## Question
Does the proposed distinction-preserving method improve the accuracy–resource trade-off compared with strong baselines?

## Evidence required
- matched budgets;
- multiple budgets, not one cherry-picked operating point;
- ablations;
- raw predictions;
- compute/resource measures where feasible.

## Evidence
None yet.

## Decision
None yet.

---

# Gate 6 — External validity

**Status:** BLOCKED

## Question
Do key findings extend beyond controlled synthetic data and beyond a single architecture?

## Evidence required
- real-world Thai text/OCR evaluation where appropriate;
- at least one additional architecture if feasible;
- claim boundaries explicitly updated.

## Evidence
None yet.

## Decision
None yet.

---

# Decision entry template

## 2026-09-04 — Provisional novelty framing and H1 direction

**Stage/Gate:** Pre-Stage 3 research governance

**Decision owner:** Human researcher

**Decision:** Proceed provisionally under an evaluation/diagnostic framing.
Freeze H1 as a non-directional `component_type × budget` interaction.
Authorize Step 3 only.

### Evidence

- analysis artifact: `docs/NOVELTY_TRIAGE.md`
- relevant literature: `docs/LITERATURE.md`

### Reasoning

The bounded review leaves a candidate controlled Thai orthographic diagnostic
gap but does not justify a new-method claim. A non-directional interaction does
not assume that any component degrades faster.

### Alternatives considered

- directional H1 without additional rationale;
- generic micro-detail pivot before measurement feasibility;
- new-method development.

### Known limitations

The novelty decision is provisional and must be revisited if new comparable
work is found. Step 3 does not test H1 and cannot support a degradation claim.

### Consequence for next stage

Step 3 primary-backbone feasibility is eligible. Steps 4 and later remain
blocked pending Step 3 evidence and their own required decisions.

### Files/configs affected

- `docs/NOVELTY_TRIAGE.md`
- `docs/RESEARCH_SPEC.md`
- `docs/CLAIMS.md`
- `docs/DECISION_LOG.md`
- `docs/exec-plans/active/ADVISOR_READINESS.md`

---

## 2026-09-04 — Advisor Readiness implementation contract

**Stage/Gate:** Evidence foundation through Advisor Readiness

**Decision owner:** Human researcher

**Decision:** Implement the approved staged plan with Stage 1A as a conditional
Resolution Sensitivity Pilot, calibration-derived Gate 0 criteria, `pair_id` as
the independent analysis unit, sequential backbone feasibility, and explicit
advisor evidence-status labels.

### Evidence

- analysis artifact: `docs/CONSISTENCY_REVIEW.md`
- relevant literature: `docs/LITERATURE.md`

### Reasoning

The contract front-loads novelty and measurement kill-tests and prevents
Resolution Reduction evidence from being treated as direct evidence about
post-encoder Token Pruning.

### Alternatives considered

- fixed universal Gate 0 thresholds;
- fixed canonical pair counts before validity review;
- simultaneous backbone comparison;
- treating Resolution Reduction as a proxy test of post-encoder pruning.

These alternatives were rejected in the approved plan.

### Known limitations

This entry approves the process constraints only. It does not approve the
provisional novelty framing, H1 directionality, any dataset item, any gate
outcome, secondary-backbone use, Stage 1A execution, or A100 use.

### Consequence for next stage

Complete literature triage and Source-of-Truth reconciliation, then pause for
the remaining human decisions before model or dataset implementation.

### Files/configs affected

- `docs/RESEARCH_SPEC.md`
- `docs/EXPERIMENT_PROTOCOL.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISION_LOG.md`
- `docs/CLAIMS.md`

---

## Entry template

Copy this block whenever a substantive scientific decision is made.

```md
## YYYY-MM-DD — <decision title>

**Stage/Gate:**
**Decision owner:** Human researcher
**Decision:**

### Evidence
- run IDs:
- analysis artifact:
- relevant literature:

### Reasoning

### Alternatives considered

### Known limitations

### Consequence for next stage

### Files/configs affected
```
