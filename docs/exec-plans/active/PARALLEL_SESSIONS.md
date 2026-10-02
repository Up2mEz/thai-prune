# Two parallel sessions of the owner (Up2mEz) — protocol and P-ZOOM brief

Written 2026-10-03. Both sessions belong to the same researcher (`Up2mEz`) and
work on Typhoon OCR 1.5's remaining gaps at the same time. This file is the
whole briefing a new session needs; read it instead of any old transcript.

## 1. Who does what

| session | collab name | folder | branch | owns |
|---|---|---|---|---|
| **gaps** (the original session) | `Up2mEz` | `D:\KMITL\LabBS2026` | `fix/t1-scoring-v2` (PR Up2mEz/thai-prune#23) | Typhoon's non-graphic gaps: G1–G4 below |
| **pzoom** (new) | `Up2mEz-pzoom` | `D:\KMITL\LabBS2026-worktrees\p-zoom` (git worktree) | `feat/p-zoom` | text inside infographics/charts: `docs/stage0/P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md` |

Gaps owned by **gaps**: G1 Text recognition question-following (Typhoon,
`BENCHMARK_QUESTION`: 10/109 answers never locate the asked text, 54% of its
error characters); G2 repetition loops / truncation; G3 surplus output marks
(order-free precision 93.7%, BQ); G4 misreads (1.5% of marks), spans missing
inside kept lines (0.7%), the rare body paragraph left out.

## 2. Rules both sessions follow (from the shared memory — do not skip)

The researcher's auto-memory lives in **one** directory for both sessions:
`C:\Users\acer\.claude\projects\D--KMITL-LabBS2026\memory\`. A session opened
in the worktree does **not** load it automatically (memory is keyed by
folder). At the start, read `MEMORY.md` there and every file it lists; save
new lessons **there** (absolute path), not in the worktree's own memory
folder. The binding ones, in short:

1. Reply to the researcher in Thai; technical terms may stay in English.
2. Goal: close Typhoon OCR 1.5's remaining Thai mark gaps, training-free,
   at similar speed. Not pruning, not the base model.
3. Before scoring any output against a reference, open real raw outputs per
   condition, design extraction for their actual format, split by task and
   prompt, report reading accuracy apart from over-generation, and stop on any
   implausible number (e.g. CER > 100%) until explained.
4. Generation parameters all pinned in config (greedy) and the resolved
   values recorded in every run manifest.
5. Model inference runs on Kaggle GPU, never the local CPU (no GPU here).
   Offline analysis of fetched files may run locally.
6. A risky worker/pipeline change is smoke-tested first on the **secondary**
   Kaggle account `thanakrit2505` via a scoped
   `KAGGLE_CONFIG_DIR=C:\Users\acer\.kaggle-thanakrit2505`. Never edit
   `~/.kaggle/kaggle.json` or `configs/kaggle_local.yaml` of the main account
   `thanakritsamoena`. Never commit credentials.
7. When a long remote job is launched, set up real monitoring at once.
8. One new factor per round: Typhoon only until a method's mechanics are
   proven.
9. Do not call a reimplementation by a published method's name unless it
   matches the paper's insertion point and handling.
10. Do not hand-build figures for presentations.
11. Give a recommendation with the plain consequences of each option; if the
    researcher delegates a decision, decide, log it, say how to reverse it.
12. `AGENTS.md`: never overwrite results; never silently change conditions;
    no stage advances without a PASS in `docs/DECISION_LOG.md`; every run
    records config, seed, model revision, git commit, environment, token counts.
13. Register before running: readings and checks fixed in a draft before
    the first output; a check that fails means the method is not used.

## 3. Collisions and how they are avoided

- **Git:** separate worktrees and branches. Never `checkout` the other
  session's branch in your own folder.
- **Kaggle kernels:** `scripts/thai_marks_kaggle.py --kernel-slug`.
  gaps uses the default `labbs2026-thai-marks-t1-t2`; pzoom uses
  `labbs2026-thai-marks-pzoom`. Fetch with
  `scripts/thai_marks_analyze.py --kernel-id thanakritsamoena/<slug>`.
  Datasets derive from the slug, so they do not collide either.
- **GPU quota:** one 30 h/week on the main account, shared. Each session
  writes the GPU-hours it used in its status file. pzoom's probe budget is
  ≤ 3 h this week; more needs the researcher's yes.
- **Git-ignored data** exists only in the main folder. pzoom reads it there,
  read-only: T1 records
  `D:\KMITL\LabBS2026\runs\kaggle\kaggle-thai-marks-t1-t2-a44199c29759\fetched\artifacts\kaggle-thai-marks-t1-t2-a44199c29759\t1\<role>\records.jsonl`;
  page images from the local HF cache of `typhoon-ai/ThaiOCRBench@ca610d1ab330`
  (calibration only; never redistribute images). pzoom writes its own runs
  under its own worktree's `runs/`.
- **Shared files:** pzoom adds new files (`src/labbs2026/thai_marks/tiling.py`,
  its config `configs/thai_marks/p_zoom.yaml`, tests, scripts). Edits to
  shared files are additive only: a new test entry in `remote.py` and the
  worker, a new top entry in `docs/DECISION_LOG.md`. gaps does not edit
  pzoom's files. Conflicts in `DECISION_LOG.md` are resolved by keeping both
  entries, newest first.
- **Locked split:** stays closed for both.

## 4. Talking to each other

- Status: gaps updates `collab/status/Up2mEz.md`; pzoom keeps
  `collab/status/Up2mEz-pzoom.md`. Update at the end of each work block.
- Messages: `uv run python scripts/collab_inbox.py --new --me <name> --to <other> --slug "..."`,
  committed on your own branch. The other session reads them without
  switching branches:
  `git show feat/p-zoom:collab/status/Up2mEz-pzoom.md`,
  `git log feat/p-zoom --oneline -- collab/` then `git show feat/p-zoom:<path>`
  (or `fix/t1-scoring-v2` the other way). Both worktrees share one `.git`, so
  no fetch is needed.
- Write a message only for: a shared-file change, a result the other needs,
  GPU budget, or a decision for the researcher.

## 5. pzoom: where things stand, what to read

State (all calibration split, `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`):

- Typhoon, Full-page OCR, order-free v2 mark F1 94.9% (BQ) / 95.3% (TC);
  misses 3.9% / 5.5% of reference marks.
- Whole lines absent: 2.3% of marks (BQ). On the 3 pages where Typhoon (BQ)
  wrote an image placeholder, 26% of their marks are absent (166 marks).
- T3: at those lines the image barely supports reading them (+1 to +2 nats
  vs −9 to −10 at ordinary transitions).
- Typhoon's own report: infographics are its weakest category
  (ROUGE-L 0.527 vs Gemini 2.5 Pro 0.677; arXiv 2601.14722).

Read, in order (nothing else is needed to start):

1. `docs/stage0/P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md` — your task (DRAFT; the
   researcher must approve the run).
2. `docs/stage0/TYPHOON_FAILURE_PROFILE.md` §2d — what is absent and how it
   is counted (`attribution.whole_line_causes`, `find_elsewhere`).
3. `docs/stage0/ORDER_FREE_MARK_METRIC_DRAFT.md` §6–§7 — the metric for any
   method that adds text.
4. `docs/DECISION_LOG.md` entries 2026-10-03 and 2026-10-02c — scope and
   metric decisions.
5. `docs/stage0/THAI_MARKS_T1_SCORING_V2.md` — extraction and generation
   rules.
6. Code you will reuse: `src/labbs2026/thai_marks/{attribution,order_free,extract,remote,runtime}.py`,
   `scripts/thai_marks_kaggle.py`, `infra/kaggle/thai_marks_worker.py`.

Verification before declaring anything done: `uv run pytest` (only the 8
Docker tests in `tests/test_glmm_failure_contract.py` may fail) and
`uv run python scripts/preflight.py`.
