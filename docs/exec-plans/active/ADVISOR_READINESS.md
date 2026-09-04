# Advisor Readiness Execution Plan

**Status:** ACTIVE — Steps 0–2 only

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

