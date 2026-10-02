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
