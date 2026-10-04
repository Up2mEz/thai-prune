# T5 — Typhoon's repetition loops: vendor penalty vs DeepSeek-OCR n-gram blocking

**Status: `APPROVED`** by the researcher 2026-10-03 (`DECISION_LOG.md` 2026-10-03c). Written 2026-10-03 before any T5
output. Typhoon only (one new factor per round), calibration split, both
prompts, Full-page OCR and Text recognition. Gap G2/G3 of
`docs/exec-plans/active/PARALLEL_SESSIONS.md`.

## 1. Why

Offline, from run `kaggle-thai-marks-t1-t2-a44199c29759` (greedy, no penalty):

- 11 of 356 Typhoon outputs hit `max_new_tokens` (3072). Nine are short
  loops: a 20–53-character unit repeated 50–150 times, starting 1–19% into
  the output (`MFA\n`, `QMS\n`, `ซอยจุฬาภรณ์ `, `<td></td>`, a chant line).
  Two repeat whole blocks (`AF432B6A` BQ, `0159AF30` TC).
- On Full-page OCR these pages hold **76% (BQ) / 68% (TC) of Typhoon's
  surplus output marks** and 14% / 48% of its missed reference marks.
  Without them, order-free mark F1 would be 97.4% instead of 94.9% (BQ) and
  97.8% instead of 95.3% (TC). That is a ceiling, not an expected gain.
- Loops also cost time: a looping page decodes the full 3072 tokens
  (~120 s on T4) instead of stopping.

Two existing training-free remedies, so no new method is assumed:

- **`rep_penalty`**: `repetition_penalty = 1.1`. The official `typhoon-ocr`
  package (0.4.1, `ocr_utils.py`) sets 1.1 for v1.5 (with temperature 0.1,
  top_p 0.6, max_tokens 16384). It penalizes *every* token already
  generated, which on a long Thai page includes most common syllables and
  their marks.
- **`ngram_block`**: DeepSeek-OCR's windowed no-repeat n-gram logits
  processor, `ngram_size 30`, `window_size 90`, table-cell tags whitelisted
  (`loop_guard.py`, verified against the reference code in tests). It only
  acts when 29 generated tokens repeat within the last 90.

Decoding stays greedy in every arm (`DECISION_LOG.md` 2026-09-28b: p = 0
only); the vendor's sampling settings are therefore not run, and
`rep_penalty` is the vendor's anti-repetition setting under greedy, not the
vendor's full configuration.

## 2. Arms (all greedy, `max_new_tokens` 3072 as T1)

| arm | `repetition_penalty` | logits processor |
|---|---|---|
| `greedy` | 1.0 | none (T1's decoding, rerun in the same session) |
| `rep_penalty` | 1.1 | none |
| `ngram_block` | 1.0 | `WindowedNoRepeatNGram(30, 90)`, whitelist = every token piece of `<td>`, `</td>`, `<td></td>` |

**Deviation from DeepSeek-OCR, stated:** its `<td>` and `</td>` are single
tokens; in Qwen's tokenizer they are not (`<td>` = [6868, 29], `<td></td>` =
[6868, 1472, 1296, 29], checked 2026-10-03). Whitelisting their pieces keeps
the intent (runs of table cells, including empty ones, are never blocked)
and also exempts the common `>` (29) at the single step where it would
complete a repeat; the ban then applies at the next step. The ids are
recorded per run.

Items: the 178 calibration items (69 Full-page OCR, 109 Text recognition),
`BENCHMARK_QUESTION` and `TYPHOON_CARD`, Typhoon at the pinned revision,
dtype as T1. Every record stores the arm, the resolved generation config,
generated tokens, seconds, and for `ngram_block` the number of steps at
which the ban removed greedy's choice (`interventions`).

## 3. Measures, fixed before the run

Per arm × task × prompt:

1. Full-page OCR: order-free v2 mark recall / precision / F1
   (`ORDER_FREE_MARK_METRIC_DRAFT.md` §6), micro over pages; page-cluster
   bootstrap 95% CI (seed 20261003, 2000 resamples) of ΔF1 vs `greedy`.
2. Text recognition: v2 anchored mark error and located share
   (`THAI_MARKS_T1_SCORING_V2.md`), as T1.
3. Loop rate: share of outputs reaching `max_new_tokens`.
4. **Non-loop pages** (those where `greedy` does not reach the limit): share
   of outputs identical to `greedy`, and mark F1 change on them. This is
   where a remedy can only do harm.
5. Speed: median and total generated tokens and seconds per item.
6. Mark misreads (`misread_with_base`, `misread_other` under
   `attribute_marks(approximate_reorder=True)`), to test the specific risk
   that `rep_penalty` changes Thai syllables.

Determinism check: `greedy` outputs are compared with the T1 run's; the
identical share is reported (fp16 GPU kernels may differ slightly).

## 4. Readings fixed in advance

- An arm **helps** if, in both Full-page cells, its F1 is above `greedy`'s,
  its loop rate is lower, and on non-loop pages its F1 drop is at most 0.2
  points; and in both Text recognition cells its mark error does not rise
  by more than 0.2 points.
- If both help, the one with the higher Full-page F1 (BQ, the primary
  prompt) is preferred; ties go to the one that changes fewer non-loop
  outputs.
- `rep_penalty` changing many non-loop outputs and raising misreads would
  support the hypothesis that a global repetition penalty costs Thai marks.
- `ngram_block` is not expected to stop the two whole-block repetitions
  (their period is far beyond 90 tokens); if it does not, that is reported as
  the gap that remains, not fixed post hoc.
- Calibration split only, n = 69 pages with ~2–6 looping: this can show the
  mechanism, not a population rate. A remedy that helps is then registered
  for the locked split.

## 5. Cost

3 arms × (138 page reads + 218 crop reads). At T1's timings
(~45 s per page read, ~5 s per crop read) about 6 GPU-hours on one T4, ~3 h
on 2×T4 with `--shards 2`. Infrastructure change (new test `t5`), so a
4-item smoke runs first on the secondary account.

## 6. Result (2026-10-03): neither arm passes §4

Run `kaggle-thai-marks-t5-a10ef64c9eb4-typhoon-x2` (git `a10ef64`), 1068 / 1068
records, 0 failures, checksums verified, fp16. **Two GPUs verified:**
`SUCCESS.json` `gpus: 2`; two shards on separate Tesla T4s (wall 12,279 s and
13,323 s); kernel 18:52:13 → 22:37:14Z = 13,501 s, close to the slower shard,
not the 25,602 s sum. `greedy` reproduces T1 exactly in every cell (identical
share 1.0). Summary: `runs/kaggle/kaggle-thai-marks-t5-a10ef64c9eb4-typhoon-x2/fetched/t5_summary.json`.

Order-free v2 mark F1, % (Δ vs `greedy`, 95% page-bootstrap CI), loop rate:

| cell | greedy | `ngram_block` | `rep_penalty` |
|---|---|---|---|
| Full-page BQ | 94.87, loops 2/69 | 94.19 (−0.68 [−2.09, 0.00]), loops 2/69 | 95.76 (+0.89 [−2.70, +4.81]), loops 2/69 |
| Full-page TC | 95.30, loops 5/69 | 95.16 (−0.13 [−1.37, +1.02]), loops 2/69 | 94.12 (−1.18 [−4.86, +1.79]), loops 3/69 |
| Text rec. BQ | 81.73, loops 1/109 | 85.03 (+3.29 [0.00, +9.82]), loops 0 | 76.30 (−5.43 [−18.3, +7.0]), loops 1 |
| Text rec. TC | 75.80, loops 3/109 | 77.74 (+1.94 [−1.33, +7.00]), loops 1 | 78.16 (+2.36 [−0.59, +7.21]), loops 1 |

On **loop-free pages** (where an arm can only do harm):

| cell | `ngram_block` identical / ΔF1 | `rep_penalty` identical / ΔF1 |
|---|---|---|
| Full-page BQ | 98.5% / −0.02 | 0% / −1.30 |
| Full-page TC | 92.2% / −0.05 | 7.8% / −1.14 |
| Text rec. BQ | 100% / 0.00 | 36.1% / −8.85 |
| Text rec. TC | 99.1% / 0.00 | 11.3% / +0.29 |

Text recognition BQ, v2 tone-mark error: greedy 17.1%, `ngram_block` 17.1%,
`rep_penalty` 22.6%. Full-page BQ `misread_other`: 1.11% → 1.80% of marks
under `rep_penalty`.

**Readings.**

- `rep_penalty` fails: it changes almost every output and costs 1.1–1.3 F1
  points on loop-free full pages and 5.5 points of tone-mark error on Text
  recognition BQ. This supports the stated risk: a global repetition penalty
  (the vendor's anti-loop setting under greedy) costs Thai marks.
- `ngram_block` fails §4 (Full-page F1 below greedy in both cells; BQ loop
  rate not lower), but it is **safe where there is no loop** (≤ 0.05 F1
  points, 92–100% identical) and ends 6 of 11 loops (`F096D392` TC: 0 → 104
  marks correct). Where it does not end a loop, raw outputs show the model
  escaping into **near-repeats** (`ซอยจุฬาภรณ์ → ซอยนวมินทร์ → ซอยนวมนิมิต →
  ซอยนวบินิต`; `ภควโต → ภวิทํ`) or a block loop longer than the 90-token
  window; these carry more marks, so surplus rises (`5300A462` BQ: output
  marks 402 → 680).
- Mechanism (inference): a loop is an attractor of the decoder, not a single
  repeated token; banning the exact repeat moves the model to a neighbouring
  attractor. Redirecting decoding does not recover the page; it would have to
  be stopped, or the unread part re-read.
- n = 69 pages with 2–5 loops per cell: every CI includes 0. Mechanism, not
  rate.
