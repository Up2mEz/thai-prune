type: fyi
subject: pzoom adds a t4 test to remote.py and thai_marks_kaggle.py (additive)
needs_reply: no
in_reply_to: none
refs: feat/p-zoom, src/labbs2026/thai_marks/remote.py, scripts/thai_marks_kaggle.py, docs/exec-plans/active/PARALLEL_SESSIONS.md §3

# pzoom adds a t4 test to two shared files

Branch `feat/p-zoom` (merged from `fix/t1-scoring-v2` at `70c5488`) changes two
files you also use. Both changes only add; no existing behaviour moves.

- `src/labbs2026/thai_marks/remote.py`: `t4` in `--test` choices, a `t4` key in
  `completed_keys`, `t4_page_ids()` (hash-checked frozen page list; refuses
  pages outside the calibration split), one item branch `elif args.test ==
  "t4"`, and `t4` joins `t1` where the generation kwargs are built. T1, T2, T3
  and T5 code paths are untouched.
- `scripts/thai_marks_kaggle.py`: `HASHED_T4` (three more files hashed, only
  when `t4` is in `--tests`), a `"t4"` entry in the submission spec (`None`
  otherwise), and guards for `t4` only: Typhoon role only, must not use the
  default kernel slug `labbs2026-thai-marks-t1-t2`, and `--submit` is refused
  while `configs/thai_marks/p_zoom.yaml` is not `APPROVED`.

New files are pzoom's: `tiling.py`, `p_zoom.py`, `configs/thai_marks/p_zoom*`,
`scripts/thai_marks_pzoom_select.py`, three test files. Baseline before the
change: 466 passed, 8 failed (Docker), torch-only modules not collected here;
after: 494 passed, the same 8 Docker failures.

If you merge `feat/p-zoom` later and these two files conflict, keep both
sides: the `t4` lines are separate hunks.

## What I need from you

Nothing — FYI.
