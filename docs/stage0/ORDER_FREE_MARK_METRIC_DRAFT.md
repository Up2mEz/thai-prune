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

## 5. v1 result: check 3 failed (2026-10-02)

Run `order_free_v1.json` (git `0a3b7b8`). `global` reproduces the R-FUSE
correction exactly (Typhoon Full-page F1 93.1% BQ, 93.7% TC, `CAT` 64.6%).

| cell | global R / P / F1 | line_matched@0.4 R / P / F1 |
|---|---|---|
| typhoon · Full-page · BQ | 94.3 / 91.9 / 93.1 | 95.5 / 93.1 / 94.3 |
| typhoon · Full-page · TC | 92.9 / 94.5 / 93.7 | 93.8 / 95.5 / 94.6 |
| typhoon · Full-page · CAT | 97.2 / 48.4 / 64.6 | 97.6 / 48.6 / 64.9 |
| base · Full-page · BQ | 64.9 / 29.9 / 40.9 | **49.2** / 22.6 / 31.0 |
| base · Text rec. · BQ | 83.3 / 14.2 / 24.2 | **70.0** / 11.9 / 20.3 |

- Check 2 (`CAT` below the better single read) passes for both models.
- **Check 3 fails:** base recall falls 15.7 points instead of staying close.
  A line read at CER ≥ 0.4 loses every mark, including marks read right, so
  v1 measures "located *and* read well", not location-free reading. Typhoon
  Text recognition falls too (−2.3 points), for the same reason.
- v1 is therefore not used. For Typhoon Full-page it is a lower bound on the
  order effect (lines it drops would only add credit): reading order costs at
  least ~1.2 points of mark recall and of mark precision.

## 6. v2 (designed after the v1 failure; checks fixed before its run)

`residual=True`: after the v1 line matching, the unmatched reference lines
(all of them, short lines included, in reference order) are globally aligned
against the output with the claimed characters removed, and their correct
marks are credited. A matched line is thus credited order-free; everything
else is scored as `global` scores it, on the output no line has claimed.

Checks for v2, all on the same run:

1. Unit tests as §3.1, plus: a poorly read line keeps the marks it got right.
2. `CAT` F1 below the better single read, both models.
3. Base recall within 2 points of `global` or above, every cell.
4. Typhoon Full-page recall ≥ `global` recall.

If any fails, v2 is not used either and the order question is reported from
`attribution_v2b.json` alone.

## 7. v2 result: all four checks pass (2026-10-02)

Run `runs/kaggle/kaggle-thai-marks-t1-t2-a44199c29759/fetched/order_free_v2.json`
(git `ceacf79`, clean; record hashes inside). Mark recall / precision / F1, %:

| cell | global | v2 @0.4 | Δ recall |
|---|---|---|---|
| typhoon · Full-page · BQ | 94.3 / 91.9 / 93.1 | **96.1 / 93.7 / 94.9** | +1.8 |
| typhoon · Full-page · TC | 92.9 / 94.5 / 93.7 | **94.5 / 96.1 / 95.3** | +1.6 |
| typhoon · Full-page · CAT | 97.2 / 48.4 / 64.6 | 98.5 / 49.0 / 65.5 | +1.3 |
| typhoon · Text rec. · BQ | 83.1 / 80.7 / 81.8 | 82.9 / 80.6 / 81.7 | −0.1 |
| typhoon · Text rec. · TC | 97.4 / 61.9 / 75.7 | 97.6 / 62.0 / 75.8 | +0.1 |
| base · Full-page · BQ | 64.9 / 29.9 / 40.9 | 65.0 / 29.9 / 41.0 | +0.1 |
| base · Full-page · TC | 17.9 / 39.2 / 24.5 | 17.8 / 39.0 / 24.4 | −0.1 |
| base · Full-page · CAT | 67.3 / 25.6 / 37.1 | 67.9 / 25.8 / 37.4 | +0.6 |
| base · Text rec. · BQ | 83.3 / 14.2 / 24.2 | 83.6 / 14.2 / 24.3 | +0.3 |
| base · Text rec. · TC | 26.1 / 52.1 / 34.7 | 25.9 / 51.8 / 34.5 | −0.1 |

1. Unit tests pass (12).
2. `CAT` F1 is far below the better single read for both models.
3. Base recall stays within 0.3 points of `global` in every cell.
4. Typhoon Full-page recall rises (+1.8 BQ, +1.6 TC).

Thresholds 0.2 and 0.6 change no cell by more than 0.6 points.

**Reading.** Reading order costs Typhoon about 1.6–1.8 points of mark recall
and of mark precision on full pages, and nothing on single regions. Base has
no measurable order effect. Order-free, Typhoon misses 3.9% (BQ) / 5.5% (TC)
of reference marks. Base's full-page mark precision is 30%: it writes about
twice as many marks as the reference holds (over-generation, already
reported separately in T1), which no reading remedy for its misreads would
touch.

Status stays `DRAFT_DIAGNOSTIC`: whether v2 becomes a reported metric
alongside the anchored one is the researcher's decision.
