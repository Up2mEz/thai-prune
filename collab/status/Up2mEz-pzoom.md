# Status — Up2mEz-pzoom

**Updated:** 2026-10-04 (pzoom, fifth work block)

## Track

P-ZOOM, P-ZOOM-2, P-ZOOM-3 (`docs/stage0/P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md`, `P_ZOOM2_VIEWS_PROBE_DRAFT.md`,
`P_ZOOM3_CONTROLS_DRAFT.md`). Protocol: `docs/exec-plans/active/PARALLEL_SESSIONS.md`.

## Done

- P-ZOOM (2x2 tiles): the registered label was an artifact of the grid's seam; it supports neither
  `beyond_typhoon_at_this_resolution` nor `resolution_attention_limit` (draft §10b). "P-ZOOM stops" withdrawn.
- P-ZOOM-2 + P-ZOOM-3 (controls) done and scored, rules fixed before any output was opened
  (`DECISION_LOG.md` 2026-10-04b/c/d; draft `P_ZOOM3_CONTROLS_DRAFT.md` §9):
  - Typhoon is reproducible on the pinned stack: the same image gives the same output, 21 of 21 pages.
  - Changing the image, even slightly, flips 11 to 19% of the marks it left out across the text / not-text line.
  - Zoom (1.85x vs 1.0x on the same three bands): 0.0 points. Cropping into three bands at page scale:
    +8.0 points (50.6% → 58.7%, interval +0.6 to +22.8), no loss on ordinary lines, about +50% decode time.
- Independent reviews (two rounds) and skeptic verification are recorded in the drafts.

## Running now

Nothing on Kaggle.

## GPU-hours used this week (main account)

2.30 (0.55 P-ZOOM, 1.02 P-ZOOM-2, 0.73 P-ZOOM-3) of the pzoom budget of 3
(`PARALLEL_SESSIONS.md` §3). The smokes ran on the secondary account.

## Waiting on

The researcher: whether a band re-read is worth piloting as a method (needs a registered draft,
order-free v2 precision charged, about 207 band reads; more than the 0.7 hours left this week).
Until a yes, the assistant runs nothing further.
