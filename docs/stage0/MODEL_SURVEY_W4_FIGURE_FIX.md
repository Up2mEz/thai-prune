# MODEL_SURVEY W4: extraction v2.1 for Pathumma's Full-page outputs (primary extraction, Decision Log 2026-10-18)

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** Written 2026-10-18 by Up2mEz's session. Extraction v2.1 is the
primary extraction for the paper, the slides and `CLAIMS.md`. The registered values in `MODEL_SURVEY_W4_RESULTS.md`
stay in place as the reference.

## The rule

Extraction v2 (`thai_marks/extract.py`) follows the `TYPHOON_CARD` contract: the content of a `<figure>` is dropped.
Two properties of Pathumma's outputs interact badly with it, and v2.1 handles both:

1. **JSON-wrapped answers.** Pathumma sometimes answers as `{"natural_text": "..."}` (Typhoon's format) with
   newlines as `\n` escapes, which stay literal characters inside the text. They are unwrapped with
   `m5.unwrap_natural_text` (M5 Addendum 1, secondary).
2. **Unclosed `<figure>`.** A tag that is never closed runs to the end of the output, so the page text after it is
   dropped. For an output that **ended on its own** the opening tag is removed and the text after it is scored. An
   output that reached `max_new_tokens` is left as it is: there the unclosed figure is a loop inside a description.

The same rule is applied to every model. The stop is not changed (`loop_cut.variant_b` on the raw output).
Code: `scripts/model_survey_w4_figure_fix.py` (`rule_text`), tests `tests/test_w4_figure_fix.py`.

## Which outputs it touches

A scan of every output of all eight models (phase A, B, C archives, locked split) finds the two properties only in
Pathumma: 30 JSON-wrapped and 9 unclosed-`<figure>` outputs. The other seven models have none, so no other model's
score changes. On the calibration split Pathumma has 5 JSON-wrapped and 6 unclosed, Typhoon 0 and 2 (both at the
token limit, so v2.1 does not change them).

## Locked split, Full-page OCR (order-free v2)

`docs/stage0/data/W4_EXTRACTION_V21_GREEDY.json` and `W4_EXTRACTION_V21_STOP_ARM.json`; the `as_registered` rows
reproduce the registered values.

Pathumma's own F1:

| prompt | as registered | v2.1 | recall as registered | recall v2.1 |
|---|---|---|---|---|
| card (primary) | 91.03 | 91.03 | 89.69 | 89.69 |
| `BENCHMARK_QUESTION` | 88.05 | 88.06 | 88.61 | 87.94 |

Typhoon minus Pathumma, points, 95% interval (v2.1):

| prompt | F1 | recall | precision |
|---|---|---|---|
| card | +1.5 [-3.1, +6.5] | +4.2 [+0.4, +8.4] | -1.1 [-9.5, +7.4] |
| `BENCHMARK_QUESTION` | +4.5 [-2.0, +10.7] | +5.9 [+1.1, +11.1] | +3.2 [-6.5, +12.6] |

For the card prompt every value equals the registered one. Text recognition is unchanged for both prompts.

## The `+ stop` arm, S1, R1 and Holm (Pathumma, Full-page)

| prompt | rule | greedy F1 | + stop F1 | S1: stop minus greedy [95%] | one-sided p |
|---|---|---|---|---|---|
| card (primary) | as registered | 91.0 | 92.4 | +1.3 [0.0, +3.5] | 0.130 |
| card (primary) | v2.1 | 91.0 | 92.4 | +1.3 [0.0, +3.5] | 0.130 |
| `BENCHMARK_QUESTION` | as registered | 88.1 | 91.5 | +3.4 [+0.7, +6.6] | 0.0075 |
| `BENCHMARK_QUESTION` | v2.1 | 88.1 | 91.2 | +3.2 [+0.5, +6.4] | 0.019 |

- S1 for Pathumma's card cell is the same under v2.1, so **S1 stays not met (12 of 13 cells)**.
- R1 for Pathumma: 15.8 [7.6, 32.1] (registered 15.8 [7.5, 32.0]); passes under both, adjusted p 0.0021.
- The largest Holm-adjusted p in the family of 22 is 0.13 under both rules.
- S2 does not depend on extraction (it compares the cut and the raw text).

## Calibration split

`docs/stage0/data/M5_EXTRACTION_V21.json` (script `scripts/model_survey_calibration_extraction_fix.py`, both models,
both prompts, both tasks). Pathumma's Full-page F1 greedy / `+ stop`: card 89.8 / 92.8, `BENCHMARK_QUESTION`
91.5 / 92.3; Text recognition: card 77.6 / 77.7, `BENCHMARK_QUESTION` 69.1 / 81.1. All equal to the registered
values to the first decimal. Typhoon minus Pathumma Full-page F1: +5.1 (card), +3.3 (BQ), unchanged.

## Earlier readings

Two earlier rules were tried on the same outputs and are kept only as files: `W4_FIGURE_FIX_ba61f71.json`,
`W4_EXTRACTION_FIX_5ba3e6d.json` and `W4_STOP_ARM_FIX_de794e0.json` (every unclosed figure kept). That rule also
scores Typhoon's looping outputs on the loop (Typhoon's card Full-page F1 on calibration falls from 95.3 to 93.7),
so it is not used, and the figures in those files (for instance Typhoon minus Pathumma +2.4, S1 +2.2) are not
results of v2.1.

## Not shown

- That Pathumma and Typhoon are equal: the intervals are about +/-5 to 6 points on Full-page.
- W3's Pathumma "greedy at correct-base sites" was not recomputed: it needs the T2 oracle records, which are on
  PELY334's side.
