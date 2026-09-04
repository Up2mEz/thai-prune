# Advisor Readiness Execution Plan

**Status:** ACTIVE — Step 3 only

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
| Step 1 — Literature / Novelty Triage | `COMPLETE_PROVISIONAL` | Human-approved evaluation/diagnostic framing; refresh on new evidence |
| Step 2 — Research-spec reconciliation | `COMPLETE` | H1 frozen as non-directional; consistency review valid |
| Step 3 — Sequential backbone feasibility | `IN_PROGRESS` | Primary Qwen2.5-VL architecture and local feasibility audit |
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
