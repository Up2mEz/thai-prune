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

## 5. Result (2026-10-04): `any_reread_fixes` (zoom one tie short)

`runs/e2/e2_reread_dev.json` (rule `3ce5734`, computed once). 21 pages; flag
threshold `s_min` ≥ 0.043 (E1's 5% over the whole cell); 36 flagged mark
errors and 281 flagged correct clusters.

| view | fixed / 36 flagged errors | broken / 281 flagged correct | not found (errors / correct) |
|---|---|---|---|
| `bands` (1.85×, full width) | **18 (50%)** | **18 (6.4%)** | 5 / 21 |
| `tiles` (2×2) | 10 (28%) | 37 (13.2%) | 8 / 24 |
| `pad` (no zoom) | 10 (28%) | 32 (11.4%) | 0 / 3 |
| `scale90` (no zoom) | 10 (28%) | 32 (11.4%) | 11 / 66 |

`bands` beats the no-zoom controls by 22 points and breaks about half as
many correct clusters, but `zoom_fixes_misreads` also asks it to break
*fewer* than it fixes; 18 = 18, so the registered reading is
`any_reread_fixes`. Inference: zoom without cutting lines carries real extra
evidence for flagged misreads, but replacing flagged places wholesale with
the re-read would fix as many as it breaks. A selection rule is needed: E2b.

## 6. Measurement corrections (2026-10-04, found while testing E2b, before E2b was computed)

1. `fix1`: the anchored window can start on a combining mark, pairing a
   consonant with the read's mark. Re-reads are now compared at the mark's
   consonant (`runs/e2/e2_reread_dev_fix1.json`).
2. `fix2`: the same tie occurs on the reference side: 19 of 232 E1
   mark-error labels sat on a reference mark. `confidence.label_clusters` and
   the probe now use the mark's consonant (`base_of`). Inspected: the changed
   labels are mostly real errors that the old version called correct
   (`สถานี → สถาบัน`, `แท้ → ท่าน`).

E1 recomputed with `fix2` (`.../e1_summary_fix1.json`) still passes: AUROC
0.918 (BQ) / 0.935 (TC), recall@5% 0.672 / 0.718.

E2 with `fix2` (`runs/e2/e2_reread_dev_fix2.json`), 40 flagged errors, 280
flagged correct:

| view | fixed | broken |
|---|---|---|
| `bands` | **20 (50%)** | **18 (6.4%)** |
| `tiles` | 12 (30%) | 36 |
| `pad` | 12 (30%) | 32 |
| `scale90` | 10 (25%) | 32 |

Reading under the corrected measurement: `zoom_fixes_misreads (bands)` (20 >
18, +22.5 points over the no-zoom controls). It is **borderline**: the
registered computation read `any_reread_fixes`, the margin is two clusters,
and it moved only through a measurement correction. Both are reported.

## 7. Zoom versus cropping, for misreads (2026-10-04, with P-ZOOM-3 reads)

`runs/e2/e2_reread_dev_fix2_with_pzoom3.json`: same flagged set (40 errors,
280 correct), adding P-ZOOM-3's `bands100` (the same crops at page scale) and
`repeat` (the identical input re-read).

| view | fixed | broken |
|---|---|---|
| `bands` 1.85× | 20 (50%) | 18 (6.4%) |
| `bands100` 1.0× | 12 (30%) | 46 (16.4%) |
| `repeat` (identical input) | 0 | 11 (3.9%) |

`repeat` reproduces the page read, so its 11 "broken" are the measurement's
noise floor (line matching in labels versus in the probe). For misread marks
the zoom matters: the same crop without zoom fixes fewer and breaks more.
Session pzoom found the opposite for omitted text (cropping, not zoom). E3
uses 1.85×.
