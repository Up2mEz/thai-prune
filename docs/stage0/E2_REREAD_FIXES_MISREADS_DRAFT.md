# E2 — do enlarged re-reads fix the misreads E1 flags? (offline probe)

**Status: `DRAFT_DEV_CHECK`,** under the researcher's standing instruction of
2026-10-04 (turn the literature into experiments and run them). Written before
computing. Offline: no new inference. Calibration split, Typhoon only.

## 1. Why

E1: Typhoon's lowest-confidence tokens find its mark misreads (AUROC 0.94–0.95
on full pages), but its own alternatives cannot fix them (E1-B1: a perfect
top-5 swap fixes 17–29%). The fix must bring new pixels: re-read the flagged
place from the image (uncertainty-guided re-reading: UG-Search, arXiv
2510.00705; small details and crop size: ViCrop, ICLR 2025). Session pzoom
already made enlarged and control re-reads of 21 calibration pages
(`TYPHOON_CARD`), so the question can be asked now, offline.

## 2. Data

- Pages: the 21 P-ZOOM pages (Full-page OCR, `TYPHOON_CARD`).
- Page read and E1 scores: T5 `greedy` output, E1 run
  `kaggle-thai-marks-t6-7934890c22f6-typhoon-x2`.
- Re-reads (session pzoom, read-only from its worktree):
  `tiles` (2×2, P-ZOOM, `kaggle-thai-marks-t4-0b2d191e31c5-typhoon`),
  `bands` (3 full-width bands at 1.85×), and the no-zoom controls `pad` and
  `scale90` (P-ZOOM-2, `kaggle-thai-marks-t6-6a7840fe40d4-typhoon`). Re-reads
  that reached `max_new_tokens` are kept (a real method would meet them too).
- Clusters: E1's labelled mark-bearing clusters (`confidence.label_clusters`
  on lines read at CER < 0.2). **Flagged** = `s_min` at or above the 95th
  percentile of `s_min` over all labelled clusters of the Full-page
  `TYPHOON_CARD` cell in E1 (the gate's 5%, page set wider than these 21).

## 3. Measure

For each cluster: take its reference line and the reference index of its base
consonant. For a view, align the line (reference-anchored) against each of
the view's reads and keep the read with the lowest CER; the view is **right**
at the cluster if, at the aligned position, the base consonant and its marks
equal the reference's, **wrong** if they differ, **not found** if the line's
best CER is ≥ 0.4.

Per view, among flagged mark errors: fix rate = right / all. Among flagged
correct clusters: break rate = wrong / all. Zoom effect = fix rate of a zoom
view − mean fix rate of `pad` and `scale90`.

## 4. Readings fixed in advance

- **`zoom_fixes_misreads`:** `bands` (or `tiles`) fixes ≥ 30% of flagged mark
  errors, at least 15 points above the no-zoom controls, and breaks fewer
  flagged correct clusters than it fixes errors. Next: a registered method —
  E1 flags a line, the band holding it is re-read, the line is replaced.
- **`any_reread_fixes`:** fix rate ≥ 30% but within 15 points of the controls:
  a different read, not zoom, does the fixing; a cheaper method (re-read the
  whole page once, vote) is the next candidate.
- **`reread_does_not_fix`:** otherwise. Flagged misreads are then beyond what
  Typhoon reads from these pixels.
- Counts are small (about 20–30 flagged errors on 21 pages): direction, not a
  rate. Reported with every count.
