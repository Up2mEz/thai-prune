# Status — Up2mEz-pzoom

**Updated:** 2026-10-04 (pzoom, sixth work block)

## Track

P-ZOOM, P-ZOOM-2, P-ZOOM-3, P-BAND (`docs/stage0/P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md`, `P_ZOOM2_VIEWS_PROBE_DRAFT.md`,
`P_ZOOM3_CONTROLS_DRAFT.md`, `P_BAND_PILOT_DRAFT.md`). Protocol: `docs/exec-plans/active/PARALLEL_SESSIONS.md`.

## Done

- P-ZOOM (2x2 tiles): the registered label was an artifact of the grid's seam (draft §10b); "P-ZOOM stops" withdrawn.
- P-ZOOM-2 + P-ZOOM-3: Typhoon is reproducible on the pinned stack (same image, same output, 21/21 pages); any
  change of the image flips 11-19% of the marks it left out; zoom (1.85x vs 1.0x on the same bands) adds 0.0
  points; cropping into three bands at page scale recovered +8.0 points of the omitted marks on those 21 pages.
- P-BAND pilot (researcher: "รันเลย"; `DECISION_LOG.md` 2026-10-04e/f): reading all 69 Full-page calibration pages as
  three bands, scored with order-free v2 (surplus charged): **`hurts`**. F1 95.30% → 88.49% (−6.81 points,
  interval −11.59 to −2.54), recall −2.3, precision −11.0, decode time +22%. The +8 on the omitted lines did not
  carry to whole pages. Exploratory only: the loss sits in small, near-square and landscape pages and comes from
  paragraphs straddling band edges, merged lines the overlap rule cannot remove, and flat strips on landscape pages.
  The naive band method is not adopted. The P-ZOOM question set is closed.

## Running now

Nothing on Kaggle.

## GPU-hours used this week (main account)

2.7 to 3.0 of the pzoom budget of 3, depending on how two T4s are counted: 0.55 P-ZOOM, 1.02 P-ZOOM-2, 0.73
P-ZOOM-3, 0.39 (longest leg) to 0.71 (sum of legs) P-BAND (`PARALLEL_SESSIONS.md` §3). Smokes ran on the
secondary account.

## Waiting on

The researcher: whether to try a geometry-aware cut with text-level stitching. It cannot be tuned and scored on
the 69 calibration pages without optimism and the locked split is closed, so it needs a decision on data.
Until a yes, the assistant runs nothing further.
