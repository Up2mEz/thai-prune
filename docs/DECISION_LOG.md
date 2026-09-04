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
To be finalized after pilot work and before the main Stage 1 run.

Do not retroactively set the threshold after viewing Stage 1 results.

## Evidence
None yet.

## Decision
None yet.

## Consequence
- PASS → Stage 1 becomes eligible.
- FAIL → repair measurement setup; Stage 1 remains blocked.

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

# Gate 4 — Existing methods

**Status:** BLOCKED

**Requires:** prior stages establish a meaningful failure worth testing

## Question
Do strong compatible existing visual-token compression methods already preserve the identified critical distinctions under fair budgets?

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
- existing methods solve the failure sufficiently → do not force a new method; contribution remains evaluation/analysis;
- meaningful unresolved failure remains → Stage 5 may be considered.

---

# Gate 5 — New-method value

**Status:** BLOCKED

**Requires:** Gate 4 = PASS only in the sense that an unresolved methodological gap is human-approved. Rename/status semantics may be revised before Stage 5 to avoid ambiguity.

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
