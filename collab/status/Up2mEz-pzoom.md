# Status — Up2mEz-pzoom

**Updated:** 2026-10-04 (pzoom, fourth work block)

## Track

P-ZOOM — `docs/stage0/P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md`, then P-ZOOM-2 and P-ZOOM-3 (`docs/stage0/P_ZOOM2_VIEWS_PROBE_DRAFT.md`,
`P_ZOOM3_CONTROLS_DRAFT.md`). Protocol: `docs/exec-plans/active/PARALLEL_SESSIONS.md`.

## State

- P-ZOOM (2x2 tiles): done; registered label `beyond_typhoon_at_this_resolution`, but an independent review
  showed it rests on one line near its cutoff and overstates (draft §10; `DECISION_LOG.md` 2026-10-04b).
- P-ZOOM-2 (`pad`, `scale90`, full-width `bands` at 1.85x): run complete on the main account
  (`kaggle-thai-marks-t6-6a7840fe40d4-typhoon`, 105 reads, 1.02 GPU-hours), **not opened or scored yet**.
- P-ZOOM-3 controls (`repeat` = T1 input unchanged, `bands100` = same crops at zoom 1.0), readings registered before
  any output is read (`DECISION_LOG.md` 2026-10-04b). Smoke on the secondary account, then the main account.

## Running now

See the run list in the latest commit message; kernel `thanakritsamoena/labbs2026-thai-marks-pzoom` (own slug; the
default `labbs2026-thai-marks-t1-t2` is not touched).

## GPU-hours used this week (main account)

1.57 so far (0.55 P-ZOOM + 1.02 P-ZOOM-2); P-ZOOM-3 expected 0.5 to 0.7 (pzoom budget 3, limit in
`PARALLEL_SESSIONS.md` §3).

## Waiting on

Nothing from the researcher. Decisions made by the assistant under "ทำไปเรื่อยๆเลย" are marked as such in
`DECISION_LOG.md`; the researcher can reverse any of them.
