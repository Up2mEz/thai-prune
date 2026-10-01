# T3 — why does Typhoon skip lines? A line-boundary oracle

**Status: `APPROVED`** by the researcher 2026-10-01 (`DECISION_LOG.md` 2026-10-01d), both prompts. Diagnostic only; it
evaluates no remedy. Calibration split, existing T1 outputs as context.

## 1. Question

Half of Typhoon's wrong marks on Full-page OCR are marks in reference lines
its output lacks entirely (`line_missing`: 50% under `BENCHMARK_QUESTION`, 48%
under `TYPHOON_CARD`, `attribution.py`); a further 7–13% are lines read in
another order. A misread mark with its base consonant correct is only 7–8%.
Before choosing a remedy, T3 asks **at the moment Typhoon skipped a line, how
close was it to reading that line?**

- **Near-tie** (the skipped line's start was almost as probable as what the
  model wrote instead): the evidence is in the model and the decision slipped.
  A decoding-time remedy at line boundaries has headroom, at small cost.
- **Not considered** (the skipped line's start was far less probable): the
  line did not reach the decision. The remedy must act on the input (e.g.
  re-reading a crop), which costs more reads.

The image/no-image contrast of T2 is reused to tell whether the image
supports the skipped line at all.

## 2. Population

Typhoon, Full-page OCR, `BENCHMARK_QUESTION` (the primary prompt), the 69
calibration pages. A **skip boundary** is a point in Typhoon's own greedy
output where the reference line `L_k` is `line_missing` and the output text
aligned just before the skip is the end of an earlier line. Only lines
containing at least one Thai mark are scored (mark relevance), with all
missing lines reported as a count.

**Control boundaries:** points where the output moves correctly from a line
to the next reference line, sampled on the same pages (seeded), so "close"
is judged against the model's ordinary line transitions rather than an
assumed threshold.

## 3. Measurement

Teacher-force the prompt plus Typhoon's **own** output up to the boundary
(its context when it decided), with explicit M-RoPE positions as in T2, then
score two continuations from the same cache, each over the same number of
characters:

- `ACTUAL` — what the model wrote next;
- `SKIPPED` — the start of the missing line `L_k`.

Per boundary, under the first-divergent-token convention (the decision greedy
makes) and the summed convention (sensitivity): the margin
`log P(ACTUAL) − log P(SKIPPED)`, and, without the image, the same margin, so
image support for `L_k` is its margin change.

At control boundaries, the same margin between the correct next line and the
line after it (the skip the model did *not* make).

Precision fp32, as T2 since 2026-09-28; consistency guard as T2.

## 4. Readings fixed in advance

- Skip margins overlapping control margins, with image support for `L_k`:
  a decision slip; next candidate is coverage-aware decoding at line
  boundaries (e.g. checking a few alternatives when a newline is emitted).
- Skip margins far larger than control margins: the line was not a
  candidate; next candidate is input-side re-reading of uncovered regions.
- No image support for `L_k`: the line's evidence does not reach the decoder
  under this input; resolution and crop choices become the question.

Whatever the result, T3 changes no number of T1 or T2.

## 5. Size and cost — counted, not estimated

On the 69 calibration pages under `BENCHMARK_QUESTION`, 178 reference lines
are missing from Typhoon's output (verbatim absent, ≥80% deleted); 60 contain
Thai marks (514 marks). Missing lines come in blocks, so only **26** are the
first missing line after a line that was read — **26 scorable boundaries on
13 pages.** That is enough to see whether skip margins sit inside or far
outside the control distribution, not to estimate a rate precisely. To widen
it without new data: (a) score all 178 missing lines, not only marked ones,
since the skip decision is made before any mark; (b) add `TYPHOON_CARD`
(§6.2). The locked split stays closed.

Built by `line_skip.boundaries` (unit-tested; 12-character continuations,
2 seeded controls per page). A boundary is kept only if the previous line's
last 8 characters are found in the output near the aligner's estimate (so the
cut is where that line really ends), its two continuations differ, and its
prefix maps back into the raw output (the model decided on raw text). That
leaves **19 skip boundaries on 11 pages under `BENCHMARK_QUESTION`** and
**15 on 15 pages under `TYPHOON_CARD`** (3 more unplaceable), with 119 and
103 control boundaries. All missing lines are scored; the marked subset is
reported separately. With n ≈ 34 skips, T3 can show whether skips sit inside
or far outside the control distribution; it cannot estimate a rate. Cost: under one T4-hour at T2's fp32
rate.

## 6. Decisions needed

1. Approve T3 as drafted, or change it.
2. Whether `TYPHOON_CARD` is scored too (its 48% share is similar).
