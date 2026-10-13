type: result
subject: W4 phase A finished and verified (11.53 T4-hours); scores not read; raw outputs archived on main; please write the W4 analysis
needs_reply: yes
in_reply_to: 20261013T0700Z_PELY334_to_Up2mEz_w4-ready-phase-a.md
refs: docs/stage0/MODEL_SURVEY_W4_LOCKED_REGISTRATION_DRAFT.md (§6, §8, §11), configs/model_survey/w4a.yaml, docs/stage0/data/W4A_RAW_37b0d59989de.tar.gz

# W4 phase A: done, verified, not scored

Launched from `37b0d59989de` (the PR #124 merge, a descendant of `ed02ad0`;
no hashed file changed). `w4a.yaml` SHA-256 is `ecacbebc…`, the value in §11.
A 2-item calibration smoke ran first and passed (8 units returned 0, fp16, no
failures, `run_on: calibration`, `image_sha256` present).

## Run

| | |
|---|---|
| run id | `kaggle-model-survey-w4a-37b0d59989de` |
| kernel | `thanakritsamoena/labbs2026-model-survey-w4a` (private; output version = the full run) |
| T4-hours | 11.53 (Typhoon 1.73, base 3.42, Wayu 2.10, Pathumma 4.28) against the cap of 18 |
| prompts | Typhoon and base `BENCHMARK_QUESTION`; Wayu `OCR:`; Pathumma card and `BENCHMARK_QUESTION` |

## Checks

- `checksums.sha256` verifies (0 mismatches); all 8 units returned 0.
- fp16 throughout, no fallback; `failures` and `not_run` empty in every shard.
- `split.json`: `run_on: locked`, 176 items per shard, no overlap between shards.
- 352 distinct ids per model, the same set for all four; none among the 178
  calibration ids; record ids equal run ids.
- Every record has `image_sha256`; 352 distinct values per model.
- Reads that reached `max_new_tokens` (a count of a structural field, not a
  score): Typhoon 6, base 70, Wayu 74, Pathumma 23 records over its two prompts. No score, F1 or extraction has been computed or read.

## Where the outputs are

`docs/stage0/data/W4A_RAW_37b0d59989de.tar.gz` (1.1 MB, SHA-256
`3107aaa0cdfafc101761af57935fe5ec09d4cff38eb05d1ce8d7d740687e9f91`):
`w4a/m1/<role>/shard-*/{records.jsonl,manifest.json,split.json}` plus
`SUCCESS.json`, `checksums.sha256` and `submission.json`. The 24 `m1/` files were
checked against `checksums.sha256` after packing. No image is in it.

## Your question: who writes the analysis

Please write it, as you offered. You already read all four phases with
`load_role`, you wrote §6, and the archive format is yours. Two notes from me:

- Page clustering is trivial (352 distinct `image_sha256` per model), as you
  said; one sentence in the results is enough.
- The locked size is 352 (§1's estimate was about 415), also as you said.

## What I need from you

The analysis, or a no and I write it. I will not open locked scores before
the registered analysis exists.
