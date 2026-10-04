# P-BAND — does reading a page as three bands raise Typhoon's whole-page mark recall, with surplus charged?

**Status: `APPROVED` 2026-10-04 by the researcher ("รันเลย", answering a proposal that named this run,
its order-free v2 scoring and that it exceeds this week's remaining pzoom budget).** Typhoon only,
calibration split only, locked split closed. A pilot of a candidate method: it adopts nothing.
Rules fixed 2026-10-04, before any of its 144 new reads exist.

## 1. Why this, and how small the prize is

P-ZOOM-3 (`P_ZOOM3_CONTROLS_DRAFT.md` §9) found, on the 21 pages where Typhoon's BQ read left lines
out, that three full-width bands read at page scale recover 58.7% of the left-out marks against 50.6%
for the whole page (+8.0 points, interval +0.6 to +22.8), lose no ordinary lines, and take about 50%
more decode time; zoom itself added nothing. That is the one positive lead for the goal in
`research-goal-reduce-thai-mark-errors`: fewer Thai mark errors, training-free, at a similar speed.

The arithmetic before the run (stored T1 `TYPHOON_CARD` whole-page reads, 69 Full-page calibration
items, order-free v2):

| | recall | precision | F1 | marks |
|---|---|---|---|---|
| whole page, 69 items | 94.47% | 96.14% | **95.30%** | 16,266 reference, 15,366 correct, 900 missing (5.53%) |
| of which the 21 pages | 93.93% | 98.29% | | 5,269 reference |
| of which the 48 other pages | 94.73% | 95.15% | | 10,997 reference |

The 387 marks of lines Typhoon left out are 2.4% of all reference marks. P-ZOOM-3's +31 marks on the
21 pages is **+0.19 points of recall over the 69 pages**; recovering all 387 would be +2.4 points.
So any gain this pilot can show is small, per-page recall is very uneven (median 99.5%, 10th
percentile 59.9%), and the interval will probably be wide. **A `not_distinguishable` outcome is the
likely one even if the effect is real**; the interval half-width is reported with every number so
it can be read as a minimum detectable effect, not as "no effect".

## 2. Reads (Typhoon, `TYPHOON_CARD`, greedy as T1, fp16): 144 new, 63 existing

| set | pages | reads |
|---|---|---|
| band reads of the 48 Full-page calibration items P-ZOOM never read | 48 | **144 new** (3 bands each) |
| band reads of P-ZOOM's 21 pages (`bands100` of P-ZOOM-3, exist) | 21 | 63, reused |
| whole-page reads (T1 `TYPHOON_CARD`, stored; P-ZOOM-3's `repeat` reproduced them byte for byte on 21 of 21 pages) | 69 | 0 |

Bands are defined exactly as P-ZOOM-3's `bands100`: three full-width bands, 15% overlap, cropped from
source pixels and read at page scale (zoom 1.0, within the trained 1,800 px). Config
`configs/thai_marks/p_band.yaml`, page list `p_band_pages.json` (ids only, sha256 pinned).

## 3. Variants and measures (`labbs2026.thai_marks.p_band_analysis`)

Text variants, built from the raw reads: `figure` blocks removed before the line split; every line
extracted as in `extract`.

- `whole`: the stored whole-page read.
- `bands_concat`: the three band outputs one after another, nothing removed: what the 15% overlap
  duplicates cost.
- `bands_dedup`: the same, but a line in the first 30% of a band's lines (at least 3) is dropped
  when the last 30% of the previous band's lines already hold it (`attribution.find_elsewhere`:
  8+ characters, CER < 0.2). Lines under 8 characters are never dropped.

Primary measure: order-free v2 micro mark precision/recall/F1 (`order_free.mark_counts(...,
residual=True)`, `DECISION_LOG.md` 2026-10-03 and `ORDER_FREE_MARK_METRIC_DRAFT.md` §7), which charges
surplus text. Paired bootstrap over pages (seed 20261004, 2,000 resamples) for each variant's F1
minus `whole`'s. Also reported, not used by the label: recall and precision separately; generated
tokens, visual tokens and generation seconds of the bands against the whole page (the cost); reads
that reach `max_new_tokens`; per-category and per-page results (best and worst five pages); the same
numbers for the 21 pages chosen for omissions and for the 48 others; the stack signature of this run
against P-ZOOM-3's (model revision, dtype, torch, transformers, device, resolved generation); the
visual-token check.

## 4. Readings, fixed in advance (`p_band_analysis.reading`)

Headline contrast: `bands_dedup` against `whole`, the variant that costs about one half read more.
Thresholds are judgements, not derived from data (§1 explains why they are small).

- **`helps`**: `ΔF1 ≥ +0.2` points, the 95% interval lies above 0, and the precision change is
  `≥ −0.5` points.
- **`hurts`**: `ΔF1 ≤ −0.2` points and the interval lies below 0.
- **`not_distinguishable`**: otherwise. Inconclusive, not "no effect".
- If the two sessions' stack signatures differ, no label is made (`stack_differs`).

`bands_concat` carries the same label for reference only. Consequences, each a *next draft*, never a
run: `helps` ⇒ a registered replication that does not reuse these pages and charges the cost
against the gain; `hurts` ⇒ bands are not a remedy for these pages; `not_distinguishable` ⇒ no
claim either way. The locked split stays closed in all cases; nothing here is a gate.

## 5. Limits that stay whatever the outcome

Typhoon only (`Qwen-only` rule applies to Typhoon too: no claim about other VLMs); 69 pages of the
calibration split; the stored baseline is `TYPHOON_CARD`, while the primary Full-page prompt of
`THAI_MARKS_T1_SCORING_V2.md` §5 is `BENCHMARK_QUESTION`: this compares like with like (both
`TYPHOON_CARD`), not the benchmark's own prompt. The 21 pages were selected because the BQ read left
lines out, so they are enriched for omissions; the 48 are not. The dedup rule's 30% window and the
thresholds are judgements. This is an input-resolution-neutral change of how the page is cut
(zoom 1.0); nothing is pruned or merged after the encoder.

## 6. What had been seen before this was written (disclosure)

P-ZOOM-3's registered analysis of the 21 pages' band reads (absent-line outcomes only; no order-free
F1 of any variant was computed), the whole-page baseline numbers of §1, and per-read sizes and token
counts. None of the 48 new pages' band outputs exists yet.

## 7. Cost

144 band reads at about 25 s each is about 1.0 GPU-hours on one T4; run as two shards on the two
T4s of one Kaggle session it should take about half the wall time. This week's pzoom budget used is
2.30 of 3 hours; the run takes it to about 2.8 to 3.3 hours depending on how the quota counts two
GPUs, which the researcher's "รันเลย" accepts. Smoke on the secondary account first (infrastructure:
a new config and the two-shard path for `t6`).

## 8. Result (2026-10-04)

Runs: P-BAND `kaggle-thai-marks-t6-f08158c5044f-typhoon-x2` (144 reads, two shards on two T4s, 23.1 and
19.4 minutes wall, no failed read, checksums verified, fp16, same stack signature as P-ZOOM-3) and
P-ZOOM-3's 63 band reads of the other 21 pages. Scored by `scripts/thai_marks_pband_analyze.py` at git
`f08158c`, the rules of §3-§4 fixed before the 144 reads existed. Visual tokens match the size read on
all 207 band reads. GPU: 0.39 hours (longest leg) to 0.71 (sum of legs); pzoom total this week 2.7 to
3.0 of 3. Calibration split, Typhoon only, 69 Full-page items, `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

**Registered result (order-free v2, micro, 69 pages):**

| variant | recall | precision | F1 | ΔF1 vs `whole` [95% paired bootstrap over pages] | ΔR | ΔP | label |
|---|---|---|---|---|---|---|---|
| `whole` | 94.47% | 96.14% | 95.30% | | | | |
| `bands_concat` | 92.21% | 78.94% | 85.06% | −10.23 [−14.29, −6.31] | −2.26 | −17.20 | `hurts` |
| **`bands_dedup`** (headline) | 92.16% | 85.10% | 88.49% | **−6.81 [−11.59, −2.54]** | −2.31 | −11.04 | **`hurts`** |

By the rule fixed in advance the band method as defined is **`hurts`**: it lowers recall as well as
precision. Page by page (`bands_dedup`, correct marks): 19 better, 18 equal, 32 worse; 458 marks gained
on the better pages, 834 lost on the worse. Cost: generated tokens ×1.24 (99,321 vs 80,033),
generation time ×1.22 (4,027 s vs 3,289 s), reads reaching `max_new_tokens` 5 vs 5. The 21 pages chosen
for omissions: recall 93.93% → 90.81%, precision 98.29% → 90.25%; the other 48: 94.73% → 92.80%,
precision 95.15% → 82.88%. Worst pages: `0B5CA667` (−148 marks), `52A433B2` (−99), `69A67416` (−74),
`AF432B6A` (−66), `E6803A95` (−66); best: `0159AF30` (+125), `F096D392` (+97), `5300A462` (+66).

**What this means.** P-ZOOM-3's +8.0 points on the lines Typhoon left out (+31 marks) did not carry to
the whole page: those pages lose far more elsewhere. The naive band method is not a remedy for these
pages and is not adopted. This answers the question it was built to answer; it does not say bands
cannot help in any form (below).

**Exploratory, after seeing the result, not registered.** The splits below were chosen after the fact;
treat them as hypotheses, not findings.

- *Where it loses.* 7 landscape pages: recall 98.92% → 89.30%. 62 portrait pages: 94.11% → 92.38%.
  Portrait pages with a source height under 1,200 px (20 pages): 97.06% → 89.81% (−7.25 points);
  1,200 px or more (42 pages): 92.75% → 93.57% (+0.83 points, precision still lower).
- *Mechanisms visible in the raw outputs.* (1) A paragraph that straddles a band edge is held in
  pieces by two bands, not whole by either (`33067A35`: a 557-character, 100-mark paragraph sits at CER
  0.29 in band 1 and 0.34 in band 2); the order-free metric credits a reference line only if it is
  found as one stretch, and charges the overlap copy as surplus. (2) Typhoon merges a paragraph into one
  long output line, so the line-level overlap rule cannot remove its duplicate (`0B5CA667`: two paragraph
  lines, 319 marks, found whole by the page read and by no band). (3) Full-width bands of a landscape
  page are flat strips (`52A433B2`, 4032×3024: 1800×500 px, aspect 3.6:1) and 12 of its 23 lines are
  missing from all three bands. (4) Overlap duplicates cost 11 points of precision with the dedup rule
  and 17 without.
- *Not tested and not testable here without tuning to these pages:* a cut that follows the layout
  (white-space gaps) or adapts the number of bands to the page, with text-level stitching of the
  overlap. Any such variant tuned on these 69 pages would be scored on its own tuning data; an honest
  test needs pages not used here, and the locked split is closed.
