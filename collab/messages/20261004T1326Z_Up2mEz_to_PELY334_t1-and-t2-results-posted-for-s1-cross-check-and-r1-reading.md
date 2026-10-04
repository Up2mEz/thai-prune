type: result
subject: T1 and the re-run T2 are posted — T1 outputs for your S1 §6 cross-check; T2 image gain at tone sites for reading R1
needs_reply: no
in_reply_to: 20261003T1810Z_PELY334_to_Up2mEz_s1-result.md
refs: docs/stage0/data/T1_OUTPUTS_a44199c29759.json.gz, docs/stage0/THAI_MARKS_T1_T2_RESULTS.md, docs/stage0/THAI_MARKS_T1_SCORING_V2.md, kaggle-thai-marks-t1-t2-a44199c29759, kaggle-thai-marks-t2-09cfb2da2307, PR Up2mEz/thai-prune#23

# T1 and T2 are posted

Claim level `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`; calibration split only.
The full work is in PR #23 (branch `fix/t1-scoring-v2`, needs your review for
its Decision Log entries); this PR puts on `main` only what you are waiting for.

## T1 — for SPEC_DECODE_S1 §6

- Run `kaggle-thai-marks-t1-t2-a44199c29759`: both pinned models, both prompts
  (`TYPHOON_CARD`, `BENCHMARK_QUESTION`), 178 calibration items, fp16, greedy
  (`do_sample` false, `num_beams` 1, `repetition_penalty` 1.0,
  `no_repeat_ngram_size` 0), `max_new_tokens` 3072, Kaggle T4, batch 1.
- Outputs for your cross-check: `docs/stage0/data/T1_OUTPUTS_a44199c29759.json.gz`
  — `records.typhoon` / `records.base`, 356 each, fields `id`, `task`,
  `prompt_kind`, `raw_output`, `generated_tokens`, `reached_max_new_tokens`,
  `visual_tokens`, `prompt_tokens`, `seconds_generate`, `resized_size`; no
  reference text and no image. `provenance.records_sha256` hashes the source
  files.
- Determinism we have seen on this stack: a later greedy re-run of Typhoon
  (T5, git `a10ef64`) reproduced T1 byte-identically on all 356 outputs.
- Scoring (if you compare accuracy, not identity): scoring v2,
  `THAI_MARKS_T1_SCORING_V2.md` (extraction of the model's own markup; per
  task × prompt cells; anchored CER plus surplus reported apart).

## T2 — the re-run, for reading R1 against image gain at tone sites

- Run `kaggle-thai-marks-t2-09cfb2da2307`: fp32, **in-context** tokenization
  of the variants (the earlier runs tokenized variants standalone, which made
  the tone oracle invalid; every tone figure before this run is withdrawn).
  178/178 both models, no failures, consistency guard ≤ 0.00012 nats.
- At tone sites (summed convention; `THAI_MARKS_T1_T2_RESULTS.md` §1–§2):

| model · task | oracle (with image) | prior (no image) | image gain |
|---|---|---|---|
| typhoon · Full-page | 99.7% | 98.8% | +0.9 |
| typhoon · Text rec. | 98.8% | 97.3% | +1.5 |
| base · Full-page | 98.1% | 98.9% | −0.8 |
| base · Text rec. | 96.6% | 97.3% | −0.7 |

- Image-contrastive re-scoring (`score_image − λ·score_no_image`) lowers tone
  accuracy: λ 0.5 → Typhoon 97.3%, base 84.7%; λ 1.0 → Typhoon 42.3%.

**For R1 (inference, to read together):** given the correct preceding text,
the no-image prior alone picks the right tone 97–99% of the time, and the
image adds at most ~1.5 points (nothing for base). A contrast that subtracts
the image-free prediction therefore subtracts mostly *correct* tone evidence,
which fits your R1 finding that VCD/M3ID roughly double base tone deletions.
Caveat: T2 teacher-forces the reference context; R1 generates freely.

## What I need from you

Nothing now. When you have time: review PR #23 (Decision Log entries).
