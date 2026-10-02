# Order-free mark precision/recall for full pages — diagnostic draft

**Status: `DRAFT_DIAGNOSTIC`, not adopted.** Written 2026-10-02 before the
first run. It changes no primary metric of `THAI_MARKS_T1_SCORING_V2.md`;
adopting it as a reported metric is the researcher's decision
(`DECISION_LOG.md` 2026-10-02b, open item 1). Calibration split only.

## 1. Why

`TYPHOON_FAILURE_PROFILE.md` §2d: on multi-column and multi-panel pages,
Typhoon reads some lines in a different order from the reference. Both the
reference-anchored alignment and the global alignment then count those lines
as deleted (and, globally, their copy as inserted). A coverage remedy, which
adds text, can only be judged by a measure that neither charges reading order
nor rewards surplus text (the `CAT` lesson, `TYPHOON_FAILURE_PROFILE.md` §3).

## 2. Definition (`labbs2026.thai_marks.order_free`)

Reference lines are `attribution.reference_lines`; the output is
`extract.extract_text`.

- **Line matching.** Lines of 8+ characters are placed longest first (ties
  in reference order). Each is aligned reference-anchored against the output
  with already-claimed output characters masked (a masked character matches
  nothing). A line is *matched* if its CER is below `LINE_MATCH_CER = 0.4`;
  its stretch of output is then claimed. 0.4 lies between the reorder
  credit threshold (0.2) and the chance level of lines this long (median
  5th percentile 0.63–0.74 against other pages' outputs); sensitivity at 0.2
  and 0.6 is reported.
- **Lines under 8 characters** are never matched (they match anywhere by
  chance). Their marks stay in the recall denominator, so recall is a lower
  bound; their share of reference marks is reported.
- **Mark recall** = reference marks whose character is reproduced exactly
  at their aligned position in a matched line / all reference marks.
- **Mark precision** = the same count / all mark characters in the output.
  Surplus text (repeats, a second read, descriptions) adds output marks and
  lowers precision; unmatched output is never credited.
- **F1** of the two.

`mode="global"` computes the same three numbers from one global alignment of
the joined reference against the output, as used for the R-FUSE correction.

## 3. Checks fixed before the first run

1. Unit tests: reordered lines get full recall; a duplicated output keeps
   recall and halves precision; one output stretch never credits two lines.
2. **`CAT` control** (Typhoon `BENCHMARK_QUESTION` + `TYPHOON_CARD` reads
   concatenated, Full-page OCR): its F1 must be below the better single
   read's. If not, the metric rewards surplus text and is not used.
3. **Base** has almost no reordering (§2d: 0.2% of marks): its order-free
   recall should be close to its global recall. A large gain for base would
   mean chance matches are being credited.
4. Order-free recall ≥ global recall in every cell is expected, not a
   check; it is reported.

## 4. Reported

Per model × task × prompt cell: recall, precision, F1 under `global` and
`line_matched`, the matched share of lines and of marks, the short-line mark
share, and the `CAT` control.
