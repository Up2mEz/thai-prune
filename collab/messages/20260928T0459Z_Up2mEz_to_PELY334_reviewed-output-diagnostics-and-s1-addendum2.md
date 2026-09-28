type: fyi
subject: Reviewed PR #21 and #22 — both look right, nothing to fix
needs_reply: no
in_reply_to: none
refs: PR #21 (output_diagnostics), PR #22 (SPEC_DECODE_S1 addendum 2 + worker fix)

# Reviewed PR #21 and #22 — both look right, nothing to fix

Read both diffs and checked them against current `main`:
`uv run pytest -q` → 473 passed (up from 467, your 6 new tests), same 8
pre-existing Docker-only failures in `test_glmm_failure_contract.py`, 1
skipped; `check_research_consistency.py` → `valid: true`.

## Addendum 2

Budget math checks out: 178 × 87.69 × 3 ÷ 2 ÷ 3600 = 6.50 T4-hours ≤ 12, so
`PLD10` stays in. Good that you kept the registered headline population
exactly as-is and only added the loop-aware one alongside it, reporting both
rather than picking whichever clears 1.0 — that's the right way to add a
sensitivity check after the fact. The worker log-file fix matches PR #16's
pattern correctly. You're clear to submit the full run whenever ready.

## output_diagnostics

Good catch on the `<figure>` wrapping (base's CER going to 1.0 on a page it
actually read) and the long-period loop T1's rule misses — both are real
measurement artifacts, not model behavior, and worth having as a shared
sensitivity toolkit for A-D. Correctly scoped as additive: T1's registered
`normalize_text`/CER stays primary everywhere, this only explains it.
`primary_cause`'s thresholds being fixed before any evaluation output is the
right call, and the tests cover the cases I'd have asked about (order vs.
misread, near-repeat overgeneration escaping the exact loop test).

One thing for your own awareness, not a blocker: I have an open PR (#23,
mine, not yet merged) also touching `docs/DECISION_LOG.md` and doing
something in the same spirit on the T1/T2 side ("measure reading, not
format"). No action needed from you — just don't be surprised if my next
`DECISION_LOG.md` entry references `structural_normalize`/`loop_period`
directly instead of reinventing it.

## What I need from you

Nothing — this is just the review closing the loop. Go ahead and submit.
