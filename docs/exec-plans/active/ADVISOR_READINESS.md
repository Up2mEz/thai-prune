# Advisor Readiness Execution Plan

**Status:** HUMAN CHECKPOINT — Steps 0–2 implemented and verified

## Objective

Produce sufficient, traceable evidence for a human advisor to recommend
`GO`, `GO WITH PIVOT`, `INCONCLUSIVE`, or `STOP` without assuming that a
new compression method is required.

## Current authorization boundary

1. Complete the evidence foundation.
2. Complete literature and novelty triage.
3. Reconcile the research Source of Truth.
4. Do not begin model, dataset, or experiment implementation until Steps
   1–3 have no unresolved stop signal.

## Implementation status

| Step | Status | Evidence / blocker |
|---|---|---|
| Step 0 — Evidence foundation | `COMPLETE` | Git history, normalized `docs/` tree, dependency lock, preflight and tests |
| Step 1 — Literature / Novelty Triage | `PROPOSED_COMPLETE` | `docs/LITERATURE.md`; human novelty decision pending |
| Step 2 — Research-spec reconciliation | `PROPOSED_COMPLETE` | `docs/CONSISTENCY_REVIEW.md`; H1 directionality decision pending |
| Step 3 — Sequential backbone feasibility | `BLOCKED` | Wait for Step 1 novelty framing and Step 2 H1 decisions |
| Steps 4–6 — Stage 0 | `BLOCKED` | Depend on Step 3 and later human approvals |
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
