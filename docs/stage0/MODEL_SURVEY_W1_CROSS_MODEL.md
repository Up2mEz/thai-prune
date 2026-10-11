# MODEL_SURVEY W1 — cross-model failure profile and the stop at a loop

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** Calibration split
only. Exploratory and offline: no new run, nothing generated. The task is W1
of Up2mEz's work split (collab
`20261011T1315Z_Up2mEz_to_PELY334_paper-prep-work-split.md`), which fixed
every rule used here before any of these numbers were computed. The only
computed numbers that existed were Typhoon's (T5b, the failure profile) and
Wayu's (M2); both reproduce (§1).

| | |
|---|---|
| outputs | M1's archived greedy outputs at each model's primary prompt (run `kaggle-model-survey-m1-3431d9f9dccf`): Qwen3-VL-4B `BENCHMARK_QUESTION`, PaddleOCR-VL-1.6 `OCR:`, Wayu `OCR:`; T1's archived Typhoon OCR 1.5 and base Qwen3-VL-2B outputs, `BENCHMARK_QUESTION` (`T1_OUTPUTS_a44199c29759.json.gz`) |
| items | M1's 178 calibration items (69 Full-page OCR, 109 Text recognition); references from M1's run records, checksums verified |
| code | `src/labbs2026/model_survey/w1.py`, `scripts/model_survey_w1.py` (tests `tests/test_model_survey_w1.py`); imports `thai_marks.loop_cut`, `order_free` and `attribution` read-only |
| data | `docs/stage0/data/W1_PROFILE_8252b99e735d.json`: no reference text, no output text |

## Method (as the work split fixed it)

- **Stop.** `loop_cut.variant_b` (exact repeat run of 8 copies, 6 for
  units of 50+ characters; the first copy is kept, the rest of the output
  dropped). Applied offline, as in M2.
  - A **non-looping** output ended before `max_new_tokens`.
  - Reported: Δ F1 over all items and over non-looping items, each with a
    95% item bootstrap (2,000 resamples, seed 20261010), and the share of
    non-looping outputs the stop changed.
- **Scores.** Order-free v2 (registered primary), with the repeat-aware
  variant (`mark_counts(..., repeat_aware=True)`, PR #85) beside it.
- **Surplus.** An output's surplus marks are its output marks minus its
  correct marks (v2). The loop share is the share of all surplus marks that
  sits in outputs the stop cuts.
- **Attribution.** `attribute_marks(..., approximate_reorder=True)` on
  Full-page, as shares of all reference marks (as
  `TYPHOON_FAILURE_PROFILE.md` §2d).
  - It is reported on the raw outputs and on the stopped outputs.
  - Anchored alignment is valid only for outputs of about reference length
    (`attribution.py`), and a looping output is many times longer. The
    stopped column is the one to read for looping models.

## 1. Reproduction checks

- **Typhoon.** The stop gives +0.84 (Full-page) and +3.3 (Text
  recognition), changes 0 non-looping outputs, and leaves the non-looping
  Δ F1 at 0.00. These are T5b's numbers. The raw Full-page attribution
  reproduces §2d of the failure profile:
  - correct 93.8%;
  - read in another order 0.5% verbatim and 1.1% approximate;
  - whole line absent 2.3%;
  - span missing 0.7%;
  - misread, base right 0.4%;
  - misread with base 1.1%.
- **Wayu.** The stop gives +10.8 and +24.4, as in M2.

## 2. The stop, per model (order-free v2 mark F1, %)

| model | task | loops / items | F1 greedy → + stop | Δ F1, all items [95%] | non-looping changed | Δ F1, non-looping | repeat-aware F1 greedy → + stop | loop share of surplus |
|---|---|---|---|---|---|---|---|---|
| Typhoon OCR 1.5 | Full-page | 2 / 69 | 94.9 → 95.7 | +0.8 [0.0, +2.7] | 0 / 67 | 0.00 | 94.8 → 95.7 | 28% |
| | Text rec. | 1 / 109 | 81.7 → 85.0 | +3.3 [0.0, +9.9] | 0 / 108 | 0.00 | 81.7 → 85.0 | 40% |
| base Qwen3-VL-2B | Full-page | 30 / 69 | 41.0 → 65.4 | **+24.4** [+19.1, +29.6] | 0 / 39 | 0.00 | 34.4 → 65.4 | 95% |
| | Text rec. | 16 / 109 | 24.3 → 66.9 | **+42.6** [+33.1, +48.8] | 0 / 93 | 0.00 | 22.6 → 66.9 | 91% |
| Qwen3-VL-4B | Full-page | 19 / 69 | 45.9 → 68.8 | **+22.9** [+17.4, +27.6] | 0 / 50 | 0.00 | 39.4 → 68.8 | 94% |
| | Text rec. | 13 / 109 | 23.5 → 29.9 | **+6.5** [+2.2, +11.6] | 0 / 96 | 0.00 | 23.4 → 29.9 | 33% |
| PaddleOCR-VL-1.6 | Full-page | 27 / 69 | 53.3 → 58.4 | **+5.2** [+2.3, +7.9] | **2 / 42** | +0.94 [−0.02, +2.78] | 51.7 → 58.4 | 79% |
| | Text rec. | 16 / 109 | 47.9 → 61.8 | +13.9 [0.0, +26.6] | 0 / 93 | 0.00 | 47.6 → 61.8 | 62% |
| Wayu | Full-page | 18 / 69 | 65.2 → 76.0 | **+10.8** [+5.3, +16.1] | 0 / 51 | 0.00 | 62.2 → 76.0 | 86% |
| | Text rec. | 22 / 109 | 46.0 → 70.4 | **+24.4** [+10.7, +35.7] | 0 / 87 | 0.00 | 45.6 → 70.4 | 71% |

Readings:

- **The stop raises F1 for every model on both tasks.** No interval lies
  below 0. Seven of ten cells exclude 0. The three that touch 0 are Typhoon's
  two (one or two loops in a task) and Paddle's Text recognition.
- **It leaves ended outputs alone.** It changed no output that ended on its
  own, except two of Paddle's 42 Full-page outputs. On those two pages a
  legitimate repeat ended without reaching the limit, and the cut raised
  their F1 (+0.94 over the 42).
- **Precision rises and recall falls.** Recall drops by 10.2 points
  (Qwen3-VL-4B) and 10.6 (base) on Full-page; elsewhere by at most 3.3.
  Part of the raw recall was credit earned by loop copies. The repeat-aware
  variant removes that credit, so its greedy F1 is lower and its gain from
  the stop larger (base Full-page +31.0, Qwen3-VL-4B +29.4). The rest is text
  after the loop that the cut drops. No stop recovers text the model did not
  read.
- **Loops carry most of the surplus.** For the four non-Typhoon models on
  Full-page, 79–95% of all surplus marks sit in the outputs the stop cuts.
  For Typhoon the share is 28%, because only two of its 69 pages loop.

## 3. Where the marks go (Full-page; share of all reference marks, %)

Stopped outputs, for comparability across models that loop and models that
do not (raw in brackets):

| model | correct | read in another order (verbatim + approx.) | **whole line absent** | span missing in a kept line | misread, base right | misread with base |
|---|---|---|---|---|---|---|
| Typhoon OCR 1.5 | 93.8 (93.8) | 1.6 (1.6) | **2.7** (2.3) | 0.5 (0.7) | 0.4 (0.4) | 0.9 (1.1) |
| base Qwen3-VL-2B | 53.8 (58.5) | 0.2 (0.2) | **33.4** (4.4) | 5.0 (13.8) | 3.4 (7.3) | 4.2 (15.8) |
| Qwen3-VL-4B | 58.8 (62.9) | 0.1 (0.1) | **24.8** (4.1) | 6.6 (10.4) | 4.3 (7.0) | 5.4 (15.6) |
| PaddleOCR-VL-1.6 | 44.6 (45.2) | 0.0 (0.0) | **37.6** (20.7) | 6.3 (13.9) | 4.2 (5.8) | 7.3 (14.4) |
| Wayu | 61.7 (63.5) | 0.4 (0.4) | **20.6** (4.5) | 8.3 (15.5) | 2.7 (4.4) | 6.3 (11.7) |

Readings:

- **Not reading dominates for every model.** On the stopped outputs, whole
  lines absent plus spans missing are 3.2% of marks for Typhoon and 29–44%
  for the other four. A wrong mark on a correctly read base consonant is
  0.4% for Typhoon and 2.7–4.3% for the others. For every model, not reading
  costs between 7 and 11 times more marks than misreading a mark on a base
  read right.
- **Why raw and stopped differ.** On raw outputs a loop's copies are aligned
  against lines the model never read, and turn "line absent" into "span
  missing" or "misread". These are alignment artefacts on outputs many times
  the reference's length, the case `attribution.py` says the alignment does
  not cover.
- **The stop's cut makes lines absent.** In the stopped column, "whole line
  absent" includes the lines after a loop: the model never reached them, and
  the cut removes what came after. For looping models this column measures
  "not read", whether the cause is the loop or a failure to read. W1 does
  not separate the two (the same caution as `MODEL_SURVEY_SUMMARY.md`'s
  closing line).

## 4. What this supports for the paper (proposal; claims are Up2mEz's to word)

- **Claim (2).** Marks are lost mostly by not reading, not by misreading. The
  claim now has five models from three families, with the alignment caveat
  of §3. It stays calibration-only and exploratory.
- **Claim (3).** The stop leaves ended outputs alone (2 changed of 726
  non-looping outputs across ten cells) and raises F1 for every model. The
  gain is large where a model loops (base, Qwen3-VL-4B, Wayu, Paddle) and
  small where it rarely does (Typhoon).
- **Not shown.** That the stop helps on unseen items: the locked-split run
  (W4) is the test. Also not shown: that the attribution of looping outputs
  is exact (§3).
