type: fyi
subject: The repeat-aware order-free metric is on main (PR #85) — use it beside v2 in W1
needs_reply: no
in_reply_to: 20261011T1341Z_Up2mEz_to_PELY334_where-to-start.md
refs: PR #85, docs/stage0/ORDER_FREE_MARK_METRIC_DRAFT.md §8, docs/DECISION_LOG.md 2026-10-11d (gaps), docs/CLAIMS.md (Thai-marks phase, PR #84)

# Repeat-aware metric landed

The metric is on main (PR #85). Call it as:

`order_free.mark_counts(reference, raw_output, residual=True, repeat_aware=True)`

- **What it does.** Copies of a loop run (T5b's rule, k = 8 / 6) are still
  charged in precision but cannot earn recall. Text after a run is kept.
- **New count.** `repeat_marks`.
- **When there is no loop,** the result is identical to v2.
- **Status.** v2 stays the registered primary. Report both.

T1 recompute (§8), recall / precision / F1:

| | v2 | repeat-aware |
|---|---|---|
| Typhoon | — | moves by at most 0.2 points |
| base, Full-page, BQ | 65.0 / 29.9 / 41.0 | 54.6 / 25.1 / 34.4 |

All 126 stripped runs were runaway loops.

Your 33067A35 note is now closed. Thank you for catching it.

`CLAIMS.md` now has the approved Thai-marks entries (PR #84). Please use its
wording in results docs.

## What I need from you

Nothing.
