# Research Decision Log

> Human-owned scientific decision record. Codex may propose decisions and summarize evidence, but final gate approval belongs to the researcher.

## 2026-09-06 — Checkpoint A final freeze for Stage 0 calibration

**Stage/Gate:** Stage 0 calibration only; Gate 0 remains `NOT_RUN`.

**Human decision:** `APPROVED FOR STAGE 0 CALIBRATION ONLY`. The calibration
design status is `FROZEN_CALIBRATION`. This authorizes the exact two-run,
2,000-call Kaggle T4 workload and does not authorize locked validation, Gate 0
approval, Stage 1A, Resolution Reduction, Token Pruning, Token Merging, or any
other compression intervention.

**Frozen evidence identity:**

- candidate inventory SHA-256:
  `cf69f0d23bec61fbeaca7fd5ed34d48219aaad9624e509cc2208a0c98a8021b2`;
- source review packet SHA-256:
  `e340a2b8386751352beb36732d21a6c613fd3bbdd1822262880e4a0a4b671df3`;
- pair allocation version: `stage0_pair_allocation_v1`;
- pair allocation SHA-256:
  `385c283091852820016bd6b1247a01af90ee04e966d298761f14cd392b8f47e8`;
- 100 calibration and 100 disjoint locked-validation `pair_id`s, balanced at
  20 per component category in each split;
- four centered 448 x 448 black-on-white rendering conditions listed in
  `configs/stage0/calibration_design.yaml`;
- all 100 calibration pairs receive both orientations of
  `LANGUAGE_CANDIDATE_BIAS_BLANK`; these controls have no visual ground truth
  and never enter visual accuracy.

**Frozen numerical/runtime contract:** Kaggle `NvidiaTeslaT4`, `float16`,
`sdpa`, Python 3.12, `torch==2.14.0+cu130`, `transformers==4.57.6`, pinned
model and processor revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`, `use_fast=False`, the pinned
processor parameters in `configs/stage0/qwen25_vl_3b_calibration.yaml`,
deterministic decoding (`do_sample=false`, `max_new_tokens=4`), and seed
`20260906`. The exact rerun measures realized reproducibility; deterministic
PyTorch algorithms were not newly enabled because the approved configuration
follows the verified backend proof run.

**Interpretive boundaries:** Current lexical status remains provisional;
`UNCERTAIN` is neither recoded as `CONSTRUCTED` nor excluded automatically.
Current `BASE_CHARACTER` pairs remain
`size_matched_stage2_status = NOT_ASSESSED_NOT_ASSUMED`. The 10 percentage
point SESOI remains measurement-planning guidance only.

**Required next checkpoint:** stop after calibration and report observed
evidence, interpretation, proposed numeric Gate 0 criteria, and unresolved
uncertainty separately. Human review is required before locked validation.

## 2026-09-06 — Stage 0 Checkpoint A conditional approval

**Stage/Gate:** Steps 4–6 / Stage 0 pre-calibration review

**Human decision:** `CONDITIONAL APPROVAL`. The five initial contact sheets
were accepted for Thai shaping, mark placement, clipping, and visible A/B
distinction. Calibration remains unauthorized until the revised inventory and
allocation receive a final human freeze.

**Frozen interpretation changes:**

- component labels are `BASE_CHARACTER`, `TONE_MARK`,
  `UPPER_VOWEL_VARIANT`, `LOWER_VOWEL_VARIANT`, and `STACKED_TONE_MARK`;
- current `BASE_CHARACTER` pairs are valid for Stage 0 but are not assumed
  size-matched for Stage 2;
- each pair member records `lexical_status` as `REAL`, `CONSTRUCTED`, or
  `UNCERTAIN`, and constructed strings remain admissible;
- blank images are language/candidate-bias controls without visual ground
  truth and must not be scored as OCR/visual accuracy;
- the provisional SESOI is 10 percentage points absolute differential
  degradation for Stage 0 planning and Advisor Readiness only.

**Already approved unless a new methodological issue is found:** Kaggle T4,
the pinned Qwen2.5-VL-3B revision, fixed prompt, exact A/B parser, pair-level
splitting, registered metrics, rendering-condition candidate pool, and
`FULL_INFORMATION`-only calibration.

**Operational backend status:**
`KAGGLE_T4_APPROVED_FOR_STAGE0_CALIBRATION`.

**Still prohibited:** Qwen calibration before final freeze, locked validation,
Gate 0 approval, Stage 1A, and every compression intervention.

**Revision presented for final freeze:** immutable review packet
`20260905T204206Z_e1ad6f35` contains 200 pairs (40/category), a proposed
20/20 pair split per category, 2,000 proposed calibration calls including the
exact rerun, and zero automated validation issues. The planning floor is not a
power guarantee. `ฬา/ฬ่า` was replaced before model exposure after the new
shaping audit detected a contextual base-glyph change.

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

## 2026-09-06 — Stage 0 preparation and calibration authorization

**Stage/Gate:** Steps 4–6 / Stage 0 Measurement Validity

**Decision owner:** Human researcher

**Decision:** Record Step 3 as `COMPLETE`. Authorize Stage 0 dataset,
measurement-pipeline, and calibration preparation, including an uncompressed
Qwen2.5-VL-3B baseline and optional use of the verified Kaggle backend.

Locked Stage 0 validation may not begin until candidate/design review,
calibration evidence, a Gate 0 criteria proposal, and a separate human freeze
are recorded. Gate 0 itself is not approved.

### Evidence

- research contract: `docs/RESEARCH_SPEC.md`
- protocol: `docs/EXPERIMENT_PROTOCOL.md`
- execution plan: `docs/exec-plans/active/STAGE0_MEASUREMENT_VALIDITY.md`
- backend record: `docs/architecture/KAGGLE_BACKEND.md`

### Reasoning

Step 3 resolved primary-backbone feasibility. Stage 0 now needs to test the
measurement system at full information before any compression intervention.
Pair inclusion must be decided without viewing model outcomes, and Gate 0
criteria must be derived from calibration rather than invented in advance.

### Alternatives considered

- proceed directly to locked validation;
- run compression before measurement validity;
- use a fixed candidate count or universal accuracy threshold.

All are inconsistent with the approved protocol.

### Known limitations

- The candidate inventory and rendering-factor pool are not human-frozen.
- No Stage 0 model outcome exists yet.
- The smallest later-stage effect of interest and numeric Gate 0 criteria are
  unresolved.
- Kaggle engineering feasibility does not guarantee a valid scientific run.

### Consequence for next stage

Prepare Checkpoint A: candidate-pair inventory, automated Unicode/rendering
audit, proposed calibration allocation, prompt/parser, metrics, and backend
workload contract. Do not open model outcomes until the human freezes the
Checkpoint A design.

### Files/configs affected

- `configs/stage0/`
- `docs/exec-plans/active/ADVISOR_READINESS.md`
- `docs/exec-plans/active/STAGE0_MEASUREMENT_VALIDITY.md`

---

## 2026-09-06 — Human smoke approval and Step 3 completion

**Stage/Gate:** Step 3 — Sequential backbone feasibility

**Decision owner:** Human researcher

**Human approval record:** `Step 3 smoke review: APPROVED` for both frozen
Latin A/B controls.

**Decision:** Step 3 = `COMPLETE`. Retain
`Qwen/Qwen2.5-VL-3B-Instruct@66285546d2b821cf421d4f5eb2576359d3770cd3`
as the primary backbone. Do not open the secondary backbone.

### Evidence

- local run IDs: `20260904T064824Z_3280bbdf`,
  `20260904T064919Z_3280bbdf`, and `20260904T065945Z_3280bbdf`;
- architecture record: `docs/architecture/QWEN2_5_VL_3B.md`;
- human approval instruction received on 2026-09-06 for the two frozen smoke
  images.

### Reasoning

The processor, prompt, and runtime Vision Encoder counts agree at 256 visual
positions for each control; deterministic inference reproduced A→A and B→B;
and the human researcher approved the rendered smoke images. No recorded
secondary-backbone trigger remains.

### Known limitations

- The controls contain Latin A/B, not Thai linguistic stimuli.
- This is an engineering-feasibility decision, not Stage 0 measurement
  validity or evidence for H1–H4.
- Completion does not authorize Step 4, candidate-pair work, Stage 0, or any
  compression intervention.

### Consequence for next stage

The Step 3 prerequisite is resolved. Steps 4 and later remain blocked until
the human researcher explicitly authorizes them and records their required
decisions.

### Files/configs affected

- `docs/ARCHITECTURE.md`
- `docs/architecture/QWEN2_5_VL_3B.md`
- `docs/CLAIMS.md`
- `docs/CONSISTENCY_REVIEW.md`
- `docs/exec-plans/active/ADVISOR_READINESS.md`

---

## 2026-09-06 — Kaggle T4 backend feasibility proposal

**Stage/Gate:** Engineering backend feasibility; not a scientific gate

**Decision owner:** Human researcher; Codex recommendation recorded below

**Decision:** `KAGGLE_BACKEND_FEASIBLE_PROPOSED`. The backend implementation
is merged into `main`, the branch designated for continued research. Final
backend adoption remains a human decision.

### Evidence

- run ID: `kaggle-step3-6c17245ae8a6`;
- source commit: `6c17245ae8a6f25b1f428bcba9a12336674ade3f`;
- Kaggle kernel status: `COMPLETE`;
- local artifact verification: `VERIFIED`;
- observed accelerator: Tesla T4, compute capability 7.5;
- architecture record: `docs/architecture/KAGGLE_BACKEND.md`.

### Reasoning

The remote run reproduced A→A and B→B, matched all three token-count
observations at 256, used the pinned model and processor revision, and passed
all hard provenance, environment, accelerator, checksum, and artifact checks.
This demonstrates a viable execution path for the Step 3 smoke workload.

### Known limitations

- The run is one non-scientific two-image smoke workload, not a benchmark or
  experiment.
- The immutable run manifest predates human smoke approval and therefore keeps
  `PENDING_HUMAN_REVIEW`; the later approval is recorded in the preceding
  Decision Log entry rather than rewriting the artifact.
- The verified run sourced `refs/heads/infra/kaggle-phase1`; the operational
  profile now targets `refs/heads/main` and must pin each future run's exact
  commit.
- No Stage 0, Thai-rendering, Resolution Reduction, Token Pruning, H1, or
  cross-architecture claim follows from this proposal.

### Consequence for next stage

The Kaggle T4 backend may be considered for separately authorized future work.
The proposal neither starts Stage 0 nor approves a scientific gate.

### Files/configs affected

- `configs/runtime/kaggle_t4.yaml`
- `docs/ARCHITECTURE.md`
- `docs/architecture/KAGGLE_BACKEND.md`
- `docs/CLAIMS.md`
- `docs/exec-plans/active/ADVISOR_READINESS.md`

---

## 2026-09-04 — Primary-backbone feasibility proposal

**Stage/Gate:** Step 3 — Sequential backbone feasibility

**Decision owner:** Human researcher; Codex recommendation recorded below

**Decision:** `PRIMARY_FEASIBLE_PROPOSED`. Keep
`Qwen/Qwen2.5-VL-3B-Instruct` as the primary backbone. Do not open the
secondary backbone. Final Step 3 completion awaits human review of the two
non-scientific smoke images.

### Evidence

- run IDs: `20260904T064824Z_3280bbdf`,
  `20260904T064919Z_3280bbdf`, `20260904T065945Z_3280bbdf`
- analysis artifact: `docs/architecture/QWEN2_5_VL_3B.md`
- relevant official model revision:
  `Qwen/Qwen2.5-VL-3B-Instruct@66285546d2b821cf421d4f5eb2576359d3770cd3`

### Reasoning

The pinned primary processor and model run locally. Processor grid accounting,
language-model image-token positions, and runtime Vision Encoder output length
agree at 256 for both smoke images across two deterministic inference runs.
The raw outputs are reproducible, and local RAM is sufficient for this tiny
smoke configuration.

### Alternatives considered

- open Qwen3-VL as a secondary backbone;
- select a backbone based on degradation behavior.

Neither is justified: the primary did not hit a recorded secondary trigger,
and no compression effect was evaluated.

### Known limitations

- Smoke images are Latin A/B controls, not Thai linguistic data.
- Smoke-image human review is pending.
- CPU latency is high and only two examples were timed.
- The first model-load time includes the initial weights download.
- No Stage 0 measurement validity or H1 evidence has been produced.

### Consequence for next stage

After human smoke-image approval, Step 3 can be marked complete. Step 4 remains
blocked until that approval and explicit authorization to proceed.

### Files/configs affected

- `configs/step3/qwen25_vl_3b.yaml`
- `docs/ARCHITECTURE.md`
- `docs/architecture/QWEN2_5_VL_3B.md`
- `docs/exec-plans/active/ADVISOR_READINESS.md`

---

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
