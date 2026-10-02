# Status — Up2mEz-pzoom

**Updated:** 2026-10-03 (pzoom, first work block)

## Track

P-ZOOM — `docs/stage0/P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md`. Protocol:
`docs/exec-plans/active/PARALLEL_SESSIONS.md`.

## Done this block (offline, no GPU)

- `feat/p-zoom` merged from `fix/t1-scoring-v2` (`70c5488`, includes the Kaggle kernel-title fix).
- `src/labbs2026/thai_marks/tiling.py` (2×2 grid, 15% overlap, zoom factor) and `p_zoom.py` (page and control-line selection), with tests.
- Page list frozen: `configs/thai_marks/p_zoom_pages.json` — 21 pages, 71 absent lines, 387 marks, 42 control lines; reproduces the draft's counts exactly.
- `t4` added to `remote.py` and `scripts/thai_marks_kaggle.py` (additive; see message `20261002T1912Z`).
- `configs/thai_marks/p_zoom.yaml` is `DRAFT`: the submit script refuses `t4` until it is `APPROVED`.

## Running now

Nothing on Kaggle.

## GPU-hours used this week (main account)

0

## Waiting on

1. The researcher's authorization of the probe (`DECISION_LOG.md` entry, then `status: APPROVED`).
2. Not yet built: the offline scorer for the three measures (draft §3) — next, no GPU needed.
3. Before the main-account run: smoke on the secondary account `thanakrit2505` (infrastructure change).
