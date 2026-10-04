# G1 — read-then-point for Text recognition (dev check draft)

**Status: `DRAFT_DEV_CHECK`.** Written 2026-10-03 before the rule was
computed. Offline, on existing outputs of run
`kaggle-thai-marks-t1-t2-a44199c29759` (calibration split, Typhoon, Text
recognition, 109 items). The rule is fixed here and computed once; this is a
development check on data already seen in aggregate, not evidence. A rule that
passes is registered for the locked split.

## 1. Why

- Typhoon's model card: the model "is intended to be used with a specific
  prompt only". Under the benchmark's own question (`BENCHMARK_QUESTION`,
  BQ), 10 of 109 Text recognition answers never locate the asked text
  (paraphrase, wrong attribute, first line only, refusal); they hold 54% of
  its error characters (`TYPHOON_FAILURE_PROFILE.md` §2c).
- Under its own prompt (`TYPHOON_CARD`, TC) Typhoon transcribes all text in
  the crop, and reads better: on items both prompts locate, median anchored
  CER 0.019 (TC) vs 0.05 (BQ). But a TC answer is not an answer to the
  question: it contains the other text too.
- So: let TC read, and use the BQ answer only to point at which part of the
  TC transcription the question asked for.

## 2. Rule (fixed)

Inputs per item: the BQ and TC raw outputs. No reference is used.

1. `a` = `extract_text(BQ output)`.
2. TC lines = `extract_text` of each raw TC line, empty lines dropped.
3. Candidates = every run of 1 to 5 consecutive TC lines, joined by a space.
4. Similarity of a candidate `c`: `1 − lev(a, c) / max(len(a), len(c))`
   (code points, after the same extraction).
5. Pick the candidate with the highest similarity; ties go to the shorter,
   then the earlier.
6. If the best similarity is below 0.5, or TC has no lines, the answer is `a`
   (the pointer failed; keep the question's own answer).
7. Answer = the chosen candidate.

## 3. Measures (as T1 v2 Text recognition, BQ cell)

Anchored micro CER and mark error, located share under the BQ cell's
permutation-null threshold (seed 20260928), global mark precision/recall/F1
(answer length matters here: a TC-length answer must not be rewarded),
answer length / reference length. Reported for: BQ alone, TC alone, the
rule, and the oracle bound "the better of BQ and the rule per item" (an
upper bound, not a method). Also how often step 6 fell back.

## 4. Readings fixed in advance

- **Passes** if, against BQ alone: global mark F1 rises, located share does
  not fall, and median answer/reference length stays within 0.8–1.25.
- Gains only in located share with F1 falling: the pointer picks text but
  the wrong text; not used.
- The 10 unlocated items are listed with what the rule picked, whatever the
  aggregate.

## 5. Result (2026-10-03): fails; not pursued

`runs/kaggle/kaggle-thai-marks-t1-t2-a44199c29759/fetched/g1_read_then_point_dev.json`
(git `41112fd` rule, computed once). Typhoon, Text recognition, 109 items,
located threshold from the BQ cell:

| answers | micro CER | median CER | located | global mark R / P / F1 | median length ratio |
|---|---|---|---|---|---|
| BQ | 22.3% | 5.0% | 90.8% | 83.1 / 80.7 / **81.9** | 1.00 |
| TC (all text, not an answer) | 6.0% | 1.9% | 98.2% | 97.5 / 61.9 / 75.7 | 1.27 |
| read-then-point | 31.4% | 17.8% | 89.9% | 73.8 / 78.9 / **76.2** | 1.00 |
| oracle: better of BQ and rule per item (bound) | 21.8% | 3.1% | 90.8% | — | — |

F1 falls and located share falls: **fails** §4. Fell back on 27 items; none
of the 10 unlocated items is recovered (the pointer itself points elsewhere).

Why (raw outputs read on the 5 worst items): TC breaks a paragraph into the
crop's short visual lines, and the 5-line cap of step 3 makes the rule pick a
middle stretch of a long answer and drop the rest. That flaw is fixable, but
the oracle bound shows the ceiling is small (micro CER 22.3% → 21.8% at best),
because BQ already locates 99/109 and the misses are question-following,
which a pointer built from the same BQ answer cannot fix. G1 by this route is
closed.
