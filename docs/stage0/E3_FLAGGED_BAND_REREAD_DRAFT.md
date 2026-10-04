# E3 — confidence-flagged band re-read with word-level choice (calibration pilot)

**Status: `APPROVED`** by the researcher 2026-10-04 ("ทำfull เลย1-2"), written
before any E3 output. Typhoon only; calibration split; the locked split stays
closed. Also serves session pzoom's proposed band pilot (its 2026-10-04d entry):
one run, both sessions read it.

## 1. Why (evidence so far)

- E1: Typhoon's lowest token log-probability finds its mark misreads (AUROC
  0.92–0.94 after the `fix2` correction).
- E1-B1: its own alternatives cannot fix them (perfect top-5 swap: 17–29%).
- E2 (`fix2`, with P-ZOOM-3 reads): at flagged places, full-width bands at
  **1.85×** are right on 50% of the page read's mark errors and wrong on 6.4%
  of its correct flagged clusters; the same crops at **1.0×** 30% / 16.4%;
  an identical re-read 0% / 3.9% (the measurement's noise floor). For marks,
  zoom matters (pzoom found it does not for omitted text; cropping does).
- E2b: a positional majority vote helped (+0.17 F1) but made crude edits.

## 2. Method (fixed)

Per Full-page page read (`greedy`, both prompts):

1. **Stop at loop**: the T5b-B cut (repeat runs of 8 / 6 copies).
2. **Flag** clusters with `s_min` ≥ 0.043 (E1 scores of the page read).
3. **Flagged lines**: raw output lines (≥ 8 characters) holding a flagged
   cluster.
4. **Band choice** (no reference, no re-read needed to choose): the line's
   relative position in the page output, `start / len(output)`, is taken as
   its vertical position; bands whose vertical span (`tiling` grid 3×1,
   overlap 0.15) contains that position ± 0.10 are re-read.
5. **Band re-read**: `TYPHOON_CARD`, greedy as T1, image =
   `tiling.view_images(page, {kind: grid, rows: 3, cols: 1, overlap: 0.15,
   zoom: 1.85})`, same as P-ZOOM-2 `bands`; then one teacher-forced forward
   for its token confidence (`runtime.score_own_output`).
6. **Word choice**: align the flagged line (anchored) to each chosen band read,
   keep the read with the lowest CER (< 0.4). Segment the line with `newmm`;
   for each word holding a flagged cluster, its band counterpart is the span
   of band characters aligned to it, widened to `newmm` word boundaries in the
   band read. Replace the word if the band word differs, contains Thai, has
   0.5–2× the length, and its lowest token log-probability (band confidence)
   is **higher** than the page word's.

No parameter is tuned on E3 outputs.

## 3. Run

New test `e3`: for every calibration Full-page item, the 3 bands are read and
scored (all bands, so that band choice can be evaluated; the method's cost
counts only the chosen bands). Records: band index and box, zoom, generated
tokens, seconds of generation and of scoring, token confidences. Typhoon,
fp16, 2×T4 shards; smoke on the secondary account first.

## 4. Measures

Per prompt cell (BQ, TC), three outputs: (a) greedy, (b) + stop at loop, (c)
+ flagged band re-read. Order-free v2 mark R/P/F1, paired page bootstrap
(seed 20261003) for (c) − (b); mean anchored CER; among E1-labelled clusters
(`fix2`), fixed and broken; edits by type; band choice accuracy (the chosen
bands include the best-matching band read of the line); **cost**: extra seconds
per page = E1 forward + chosen band generation + chosen band scoring, as a share
of the page read's generation seconds. Reported separately for the 21 pages
used in E2 design and the 48 others.

## 5. Readings fixed in advance

- **PASS** if, in both prompts, F1(c) > F1(b); pooled fixed ≥ 2 × broken;
  CER(c) ≤ CER(b); and mean extra time ≤ 50% of the page read's.
- Otherwise **FAIL**, naming the conditions that failed. A pass is still a
  calibration pilot (`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`); confirmation needs
  the locked split, which is the researcher's decision.
