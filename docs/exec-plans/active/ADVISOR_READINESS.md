# Advisor Readiness Execution Plan

**Status:** CONDITION C AMENDED; FINAL VISUAL/PROTOCOL APPROVAL PENDING

## Objective

Produce sufficient, traceable evidence for a human advisor to recommend
`GO`, `GO WITH PIVOT`, `INCONCLUSIVE`, or `STOP` without assuming that a
new compression method is required.

## Current authorization boundary

1. Complete the evidence foundation.
2. Complete literature and novelty triage.
3. Reconcile the research Source of Truth.
4. Step 3 is complete after human approval of the A/B smoke controls.
5. The amended A/B/C pilot may receive deterministic rendering, contact-sheet,
   and pixel-identity validation only.
6. Do not run pilot inference before final visual/protocol human approval.
7. Do not run locked validation before calibration-derived Gate 0 criteria and
   Checkpoint B human freeze.
8. Backbone screening, Stage 1A, and every compression intervention remain
   unauthorized.

## Implementation status

| Step | Status | Evidence / blocker |
|---|---|---|
| Step 0 — Evidence foundation | `COMPLETE` | Git history, normalized `docs/` tree, dependency lock, preflight and tests |
| Step 1 — Literature / Novelty Triage | `COMPLETE_PROVISIONAL` | Human-approved evaluation/diagnostic framing; refresh on new evidence |
| Step 2 — Research-spec reconciliation | `COMPLETE` | H1 frozen as non-directional; consistency review valid |
| Step 3 — Sequential backbone feasibility | `COMPLETE` | Human-approved A/B smoke review; pinned Qwen2.5-VL-3B retained as primary; no secondary trigger |
| Kaggle T4 backend | `KAGGLE_T4_APPROVED_FOR_STAGE0_CALIBRATION` | Proof run verified; exact frozen config and artifact verification remain mandatory |
| Steps 4–6 — Stage 0 | `PILOT_COMPLETE_HUMAN_REVIEW_REQUIRED` | The verified 25-pair Qwen3.5 pilot produced A=49.5%, B=0%, C=0%; Condition C crossed the frozen output-failure flag, so the decision is `MIXED_TARGETED_INSTRUMENT_REVIEW` and execution is stopped; backbone screening, Gate 0, locked validation, and compression remain unauthorized |
| Step 7 — Stage 1A | `BLOCKED` | Requires human-approved `Gate 0 = PASS` |
| Step 8 — Advisor Readiness report | `NOT_STARTED` | Accumulates evidence from eligible prior steps |

## Dependency order

```text
Evidence foundation
   ↓
Literature/novelty triage + research-spec reconciliation
   ↓
Sequential primary-backbone feasibility
   ↓
Stage 0 calibration and locked validation
   ↓ human Gate 0 decision
Stage 1A Resolution Sensitivity Pilot
   ↓
Advisor Readiness report
```

## Non-negotiable boundaries

- Resolution Reduction is not post-encoder Token Pruning.
- Stage 1A is preliminary and cannot approve Gate 1.
- The independent sampling/analysis unit is the linguistic `pair_id`;
  render variants are repeated observations.
- Gate 0 criteria are derived from calibration precision, measurement
  ceiling/headroom, and the intended later-stage effect, then frozen by a
  human before locked validation.
- Backbone selection must not use the observed degradation effect.
- Codex may propose but cannot approve scientific gates.
