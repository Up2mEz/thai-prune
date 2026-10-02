# T5b — stop at a detected loop (offline dev check draft)

**Status: `DRAFT_DEV_CHECK`.** Written 2026-10-03 after T5 (§6 of
`T5_LOOP_DECODING_DRAFT.md`), before this rule was computed. Offline, on the
T5 outputs (`greedy` and `ngram_block` arms, calibration, Typhoon). Designed
after seeing T5, so it is exploratory; a rule that passes is registered for
the locked split.

## 1. Why

T5 showed that redirecting a loop (banning the exact repeat) moves Typhoon
into a neighbouring loop that adds surplus marks. Decoding is greedy, so
stopping at step *t* yields exactly the first *t* tokens of the output: cutting
a finished output at the loop's onset is what stopping there would have
produced, and can be scored offline.

## 2. Rule (fixed)

A **run** is a raw-output substring `u` with 4 ≤ len(u) ≤ 400 characters that
contains at least one Thai consonant (U+0E01–U+0E2E) or Latin letter, repeated
exactly and consecutively at least `k` times. The **loop onset** is the
earliest start of any run; the cut keeps the first copy of `u` and drops the
rest of the output.

Two variants:

- **A — cut runaways only:** applied only to outputs that reached
  `max_new_tokens`, with `k = 4` (`k = 3` for len(u) ≥ 50). Outputs that
  ended on their own are never touched. Removes surplus; saves no decoding
  time.
- **B — stop during decoding:** applied to every output with `k = 8`
  (`k = 6` for len(u) ≥ 50): the stricter repeat count is what a decode-time
  stop would need to avoid cutting legitimate repetition. Saves the tokens
  after the cut.

Each variant on the `greedy` outputs and on the `ngram_block` outputs.

## 3. Measures

Order-free v2 mark R/P/F1 per cell; Δ vs `greedy` with the T5 page bootstrap
(seed 20261003); outputs changed among loop-free pages; characters and
tokens removed (tokens counted with Typhoon's tokenizer, tokenizer only).

## 4. Readings fixed in advance

- **A passes** if its F1 ≥ `greedy` in all four cells (it touches only
  runaway outputs by construction).
- **B passes** if its F1 ≥ `greedy` in all four cells, it changes at most one
  loop-free output per cell, and the loop-free ΔF1 ≥ −0.05 points.
- `ngram_block` + A / + B pass on the same terms; the combination is the one
  T5 suggested (n-gram block ends some loops; the stop handles the rest).
- Recall cannot rise from a cut: text after a loop is never recovered. A
  pass here is about precision and time, and the unread remainder is the gap
  left for a re-reading method.

## 5. Result (2026-10-03): A and B pass; `greedy`+B preferred

`runs/kaggle/kaggle-thai-marks-t5-a10ef64c9eb4-typhoon-x2/fetched/t5b_stop_dev.json`
(rule `92be3f6`, computed once). Order-free v2 mark F1, % (Δ vs `greedy`,
95% page-bootstrap CI):

| cell | greedy | greedy+A | greedy+B | ngram_block+A | ngram_block+B |
|---|---|---|---|---|---|
| Full-page BQ | 94.87 | 95.71 (+0.84 [0, +2.73]) | 95.71 (same) | 95.69 (+0.82) | 95.49 (+0.62) |
| Full-page TC | 95.30 | 95.97 (+0.67 [0, +2.29]) | 95.97 (same) | **96.28** (+0.99) | 95.95 (+0.66) |
| Text rec. BQ | 81.73 | 85.03 (+3.30 [0, +9.85]) | 85.03 (same) | 85.03 (+3.29) | 85.03 (+3.29) |
| Text rec. TC | 75.80 | 78.19 (+2.39 [0, +7.33]) | 78.19 (same) | 77.74 (+1.94) | 77.74 (+1.94) |

- Loop-free outputs cut: 0 in every cell for `greedy`+A and +B; 2 in
  Full-page TC for `ngram_block`+B (which therefore **fails** §4).
- `greedy`+A, `greedy`+B and `ngram_block`+A pass §4. By T5's tie rule
  (Full-page BQ F1, then fewer loop-free changes) `greedy`+B is preferred: it
  ties `greedy`+A, changes no loop-free output, and is the variant that saves
  decoding.
- **Time (B, stopped where the 8th / 6th copy completes, Typhoon's
  tokenizer):** 21,942 of 196,523 generated tokens saved (11.2%), about 920 of
  8,823 decode-seconds (seconds scaled by tokens, an approximation). By cell:
  Full-page BQ 4.7%, TC 13.9%; Text recognition BQ 19.4%, TC 12.3%.
- Recall falls by at most 0.16 points: cutting never recovers the text a loop
  skipped. Pages left looping: `AF432B6A` BQ and `0159AF30` TC, whose repeated
  blocks exceed the 400-character unit.
- `ngram_block`+A has the highest Full-page TC F1 because the n-gram block
  sometimes ends a loop and the model then reads on (`F096D392`: 0 → 104
  marks), which a cut cannot do; it also changes 1.5–7.8% of loop-free
  outputs.

Caveats: designed after seeing T5, computed on the same calibration outputs,
1–4 looping outputs per cell; every CI touches 0. Next, if pursued: implement
B as a decode-time stopping criterion, verify it reproduces the offline cut
exactly, and register it for the locked split.
