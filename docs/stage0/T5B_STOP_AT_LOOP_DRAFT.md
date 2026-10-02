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
