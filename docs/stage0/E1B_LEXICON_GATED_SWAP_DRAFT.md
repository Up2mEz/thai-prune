# E1-B1 — confidence-gated, lexicon-checked token swap (offline dev check)

**Status: `DRAFT_DEV_CHECK`.** Written 2026-10-04 after E1 passed, before this
rule was computed. Offline on the E1 scores (top-5 alternatives recorded per
token); no new inference. Calibration only, exploratory.

## 1. Why

E1: Typhoon's low-confidence tokens hold most of its mark errors, but 86% of
flagged clusters are correct, so swapping to the second choice blindly would
break more than it fixes. A correction needs evidence beyond the model's
top-1. Literature: lexicon/LLM post-correction over-corrects at low error
rates (Kanerva 2025; HIPE-OCRepair 2026; Meknavin 1998: +1.56% new errors),
while gating correction by confidence avoids touching likely-correct output
(Naderi et al., Interspeech 2024). E1-B1 combines both: only low-confidence
tokens, only to turn a non-word into a word, only with the model's own
alternatives.

## 2. Rule (fixed)

Per output (non-looping greedy outputs of T5, scored in E1):

1. **Flag** tokens that contain a Thai character and whose log-probability is
   in the lowest 5% of such tokens in the same (task, prompt) cell (computed
   from scores only).
2. **Candidates** for a flagged token: its top-5 alternatives other than the
   chosen token, with log-probability ≥ chosen − ln 10, decoding to text that
   contains a Thai character and no replacement character.
3. **Word test**: take the raw output line holding the token; segment it with
   PyThaiNLP `newmm`; `w0` = the word covering the token's first character.
   For a candidate, replace the token's text in the line, segment again, and
   take `w1` covering the same position. The candidate qualifies if `w0` is
   not in the PyThaiNLP word list and `w1` is.
4. **Swap** to the qualifying candidate with the highest log-probability.
   Swaps in one output are applied left to right; later offsets shift.

## 3. Measures

Order-free v2 mark R/P/F1 per cell against greedy, with the T5 page bootstrap
(seed 20261003); swaps made; among swaps on E1-labelled clusters, how many
turn a mark error into a correct cluster (**fixed**) and how many turn a
correct cluster into an error (**broken**).

## 4. Readings fixed in advance

- **Passes** if F1 ≥ greedy in all four cells, F1 rises in both Full-page
  cells, and broken ≤ fixed overall.
- **Fails** otherwise; the next candidate is lookahead rescoring with the
  model itself (teacher-force the rest of the line under each alternative),
  which needs GPU and is registered separately.
- Real-word errors are untouched by design (`w0` in the lexicon); proper
  nouns and loanwords outside the lexicon are the main over-correction risk.
