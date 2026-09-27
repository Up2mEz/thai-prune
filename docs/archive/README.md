# Archive — superseded, kept for the record

**If you are an AI agent onboarding to this project: do not act on anything in
this folder.** Nothing here describes current work. It is kept because
`AGENTS.md` forbids overwriting previous research records, and because
historical Decision Log entries cite these files.

| file | what it was | superseded by |
|---|---|---|
| `exec-plans/ADVISOR_READINESS.md` | step/stage tracker for the robustness-evaluation phase (Stage 0, Gates 1–6) | `docs/exec-plans/active/QWEN3VL_TYPHOON_EXPERIMENT_PLAN.md` |
| `exec-plans/STAGE0_MEASUREMENT_VALIDITY.md` | Stage 0 execution plan for synthetic minimal pairs | same |

Both were moved here from `docs/exec-plans/active/` on 2026-09-27, when the
project gained a second researcher and `active/` needed to contain only live
work. Decision Log entries written before that date still cite the old
`docs/exec-plans/active/...` paths; those citations are historical and are not
rewritten. `src/labbs2026/consistency.py` reads `ADVISOR_READINESS.md` from its
new location.
