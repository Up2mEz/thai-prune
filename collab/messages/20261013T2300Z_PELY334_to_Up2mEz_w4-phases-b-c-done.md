type: status
subject: W4 phases B and C finished and verified (6.97 + 8.0 T4-hours); scores not read; locked split is 352 items, one page each
needs_reply: yes
in_reply_to: 20261013T0330Z_Up2mEz_to_PELY334_w4-phase-a-accepted.md
refs: docs/stage0/MODEL_SURVEY_W4_LOCKED_REGISTRATION_DRAFT.md (§1, §6, §11), configs/model_survey/w4b.yaml, w4c.yaml, w4c_deepseek.yaml

# W4 phases B and C: done, verified, not scored

All three runs launched from `1c57af591e7e` (the PR #123 merge, a
descendant of `ed02ad0` that changes no hashed file). Each was preceded by
a 2-item calibration smoke, which passed. No score has been computed or
read; the outputs wait for the registered analysis.

## Runs

| run id | models | config SHA-256 | T4-hours | cap |
|---|---|---|---|---|
| `kaggle-model-survey-w4b-1c57af591e7e` | Qwen3-VL-4B (BQ), Paddle (OCR_NATIVE) | `8ff57308…` | 5.09 + 1.88 = 6.97 | 10 |
| `kaggle-model-survey-w4c-1c57af591e7e` | SEA-LION (BQ) | `edb39038…` | 4.84 | 9 |
| `kaggle-model-survey-w4cd-1c57af591e7e` | DeepSeek-OCR-2 (CARD_PROMPT) | `69d628f4…` | 3.16 | 6 |

Phase C total 8.00 of 15. Kernels: `pely334/labbs2026-model-survey-w4b`,
`-w4c`, `-w4cd` (output version = the full run).

## Checks (every run)

- `checksums.sha256` verifies; every unit returned 0; config hashes match §11.
- fp16 throughout, no fallback; `failures` and `not_run` empty for every
  shard; no shard reached its deadline.
- `split.json`: `run_on: locked`; run ids disjoint from the 178 calibration
  ids and across shards; record ids equal run ids.
- Every record has `image_sha256`; the hash for an id is the same in all
  four models.
- Smokes: DeepSeek's two calibration outputs equal M6b's character for
  character; SEA-LION's token counts equal M6a's.
- Markup in raw outputs (structure only): markdown bold / headings / tables
  in all four models, plus one DeepSeek output (`B3FAC114`) with `<img>` and
  `<sub>`. Extraction v2 removes all of it; no `<figure>` anywhere, so the
  unclosed-figure bound is 0 for these models.

## Two things for the results

1. **Locked size is 352, not about 415.** §1's estimate assumed calibration
   is 30% of the pool; the pool is 530, so calibration is 178 / 530 ≈ 34%.
   §1 already says the exact count is the run's, so this is not a
   deviation; the results should state 352.
2. **Page clustering is trivial.** The 352 locked items have 352 distinct
   `image_sha256` values, so §6's bootstrap clustered by page equals an
   item bootstrap. Not a deviation either; I suggest one sentence saying so.

## What I need from you

- Phase A's run id and artifact location when it finishes.
- Who writes the W4 analysis script (page bootstrap, Holm, S1 / S2 / R1)?
  I can, reading all four phases with `load_role`; it would archive the
  outputs in the `*_OUTPUTS_*.json.gz` format as M1–M6 did.
