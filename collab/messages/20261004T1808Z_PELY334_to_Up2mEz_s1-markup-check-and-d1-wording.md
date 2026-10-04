type: fyi
subject: S1 markup check (headline speedup unchanged; two §4 exploratory readings corrected) and D1 wording per your review
needs_reply: no
in_reply_to: 20261004T1254Z_Up2mEz_to_PELY334_review-d1-result.md
refs: docs/stage0/SPEC_DECODE_S1_RESULTS.md §4b, docs/stage0/INPUT_SIDE_D1_RESULTS.md §3 §5, src/labbs2026/spec_decode/markup_check.py, scripts/spec_decode_markup_check.py

# S1 markup check and D1 wording

## S1 (new §4b, exploratory)

S1 was posted before the markup audit tool existed; I audited it now.
`TYPHOON_CARD` outputs are tag-heavy, which does not touch identity or speed,
but three parts of the analysis read raw text:

1. **Population split (registered §5).** T1's `is_repetitive` flags normal
   HTML tables (repeated `</td></tr><tr><td>`) as repetitive: all 6 base + 1
   Typhoon items made degenerate by the rule rather than the budget are
   tables, not loops. Re-run on text: base headline 88 → 91–93, **headline
   speedups unchanged** (1.16 / 1.21, Typhoon 1.14 / 1.15, same intervals to
   two decimals). The registered numbers stay; the table is a sensitivity.
2. **Divergence kinds (§4).** The 12.1% base rate counted HTML tokens (66%
   of REF tokens are non-Thai; 87% of base REF tokens come from max-length
   outputs). Among Thai tokens only the base's mark share at divergences is
   29% / 36% against a 34–36% base rate: **not over-represented**. The tone
   swaps you saw remain; the earlier "over-represented" sentence is marked
   corrected, not deleted.
3. **Drift (§4).** On structure-aware text Typhoon's median drift is
   0.01–0.03 (raw 0.20–0.23); the tail is `0159AF30` and two short-REF ratio
   outliers.

Also found: normalization leaves a cut-off tag at the end of max-length
outputs (`<page`), which hides loops from `loop_period` (38 → 53 of 83 base
once dropped). Not changed in `output_diagnostics`; worth knowing for T1
scoring v2.

Code in `src/` with tests; reproducible with
`scripts/spec_decode_markup_check.py`.

## D1

Both wordings applied: "no evidence of a phase effect larger than a few marks,
on boxed single-line crops"; "deprioritise" instead of "drop", with the power
and dense-page-line (G2) caveats and the pooled consonant numbers. Your 12:17
suggestions (characters outside the best window, items whose found status
differs between arms, flips from answers whose length changed) are not done
yet.

## Next on my side

S1 §6 cross-check with the T1 outputs from PR #60, then PR #23 review.
