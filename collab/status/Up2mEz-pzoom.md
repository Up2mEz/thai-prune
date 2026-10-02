# Status — Up2mEz-pzoom

**Updated:** 2026-10-03 (pzoom, second work block)

## Track

P-ZOOM — `docs/stage0/P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md`. Protocol:
`docs/exec-plans/active/PARALLEL_SESSIONS.md`.

## Done

- Tiling, frozen page list, `t4` in the worker, offline scorer (`p_zoom_analysis.py`), tests (505 pass).
- Probe authorized under delegation: `DECISION_LOG.md` 2026-10-03d. Reading rule amended before any tile output (draft §7): tiles must beat the zoom-free `TYPHOON_CARD` whole-page read by 15 points.
- Smoke on the secondary account passed (`kaggle-thai-marks-t4-76165db98ea8-typhoon-smoke1`).

## Running now

Full probe on the main account: kernel `thanakritsamoena/labbs2026-thai-marks-pzoom`
(own slug; the default `labbs2026-thai-marks-t1-t2` is not touched), run id
`kaggle-thai-marks-t4-0b2d191e31c5-typhoon`, 84 reads, one T4 session, expected 1 to 1.5 h.

## GPU-hours used this week (main account)

0 so far; this run expected 1 to 1.5 (limit 2, session budget 3).

## Waiting on

The run to finish; then `scripts/thai_marks_pzoom_analyze.py` and a write-up.
