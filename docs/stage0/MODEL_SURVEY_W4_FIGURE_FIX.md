# MODEL_SURVEY W4: two extraction defects in Pathumma's Full-page outputs, rescored (post hoc, descriptive)

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** Written 2026-10-18 by Up2mEz's session. This is a
second reading of the locked phase-A outputs with the extraction rule changed. It is **post hoc**, it is not
one of the registered tests, and it replaces no number in `MODEL_SURVEY_W4_RESULTS.md`.

## The two defects

1. **Unclosed `<figure>`.** Extraction v2 (`thai_marks/extract.py`) follows the `TYPHOON_CARD` contract: a
   `<figure>` holds a description of an image, so its content is dropped. A `<figure>` that is never closed
   therefore runs to the end of the output. In nine Pathumma Full-page outputs (five under
   `BENCHMARK_QUESTION`, four under the card prompt; seven distinct pages) the tag is never closed and real
   page text follows it (in `BFE7C5A8`, the page's flowchart text). The registered analysis bounded this
   (`upper_bound_unclosed_figure`).
2. **JSON-wrapped answers.** Pathumma sometimes answers as `{"natural_text": "..."}` (Typhoon's format), with
   newlines as `\n` escapes. The W4 analysis scored these as written, so the escapes are literal characters
   inside the text: 30 Full-page outputs (21 under `BENCHMARK_QUESTION`, 9 under the card prompt), none from
   any other model. M5 registered `m5.unwrap_natural_text` as the secondary reading for this case; the W4
   analysis did not apply it.

## What was done

`scripts/model_survey_w4_figure_fix.py` rescored Typhoon and Pathumma (phase A, locked) under four rules, with
the registered scoring, bootstrap (10,000 resamples, seed 20261012, paired by page) and paired difference:

- `as_registered`: reproduces `MODEL_SURVEY_W4_RESULTS.md`.
- `figure_text_kept`: the opening tag of a `<figure>` with no `</figure>` is removed, so the text after it is kept
  (the figure's own description is kept too and adds surplus marks).
- `json_unwrapped`: `unwrap_natural_text` applied.
- `json_unwrapped_figure_kept`: both, unwrap first. **This is the reading with both defects removed.**

Output: `docs/stage0/data/W4_EXTRACTION_FIX_5ba3e6d.json` (no output or reference text). The first run, with the
figure rule only, is `W4_FIGURE_FIX_ba61f71.json`; it is superseded.

## Result (Full-page OCR, locked split, order-free v2)

Pathumma's own scores (the registered values are in the first row of each prompt):

| prompt | rule | F1 | recall | precision |
|---|---|---|---|---|
| card | as registered | 91.0 | 89.7 | 92.4 |
| card | both removed | 90.1 | 90.0 | 90.3 |
| `BENCHMARK_QUESTION` | as registered | 88.0 | 88.6 | 87.5 |
| `BENCHMARK_QUESTION` | both removed | 87.4 | 88.2 | 86.7 |

Typhoon minus Pathumma, points, 95% interval:

| prompt | rule | F1 | recall | precision |
|---|---|---|---|---|
| card | as registered | +1.5 [-3.1, +6.5] | +4.2 [+0.4, +8.4] | -1.1 [-9.5, +7.4] |
| card | figure only | +1.4 [-3.4, +6.5] | +2.0 [-0.8, +4.7] | +0.9 [-8.3, +10.0] |
| card | JSON only | +1.5 [-3.1, +6.5] | +4.2 [+0.4, +8.4] | -1.1 [-9.5, +7.4] |
| card | **both removed** | **+2.4 [-2.6, +7.8]** | **+3.8 [+0.2, +8.0]** | +1.1 [-8.2, +10.2] |
| `BENCHMARK_QUESTION` | as registered | +4.5 [-2.0, +10.7] | +5.2 [+0.4, +10.4] | +3.8 [-5.6, +13.0] |
| `BENCHMARK_QUESTION` | figure only | +3.5 [-2.7, +9.4] | +1.9 [-1.7, +5.4] | +5.0 [-4.7, +14.2] |
| `BENCHMARK_QUESTION` | JSON only | +4.8 [-1.8, +11.1] | +6.5 [+1.4, +11.9] | +3.2 [-6.5, +12.6] |
| `BENCHMARK_QUESTION` | **both removed** | **+5.1 [-1.4, +11.4]** | **+5.6 [+0.7, +10.9]** | +4.7 [-5.2, +14.3] |

Text recognition is unchanged (no affected output). No Typhoon output changes under any rule.

- Removing only the figure defect lowers the recall gap; removing only the JSON defect raises it. With both
  removed the gap is about the registered size. A single fix pointed in the direction that looked like a bias
  against Pathumma; the complete fix does not.
- The F1 difference stays small and its interval contains 0 in both prompts: "no difference shown" stands.
- The recall difference (Typhoon higher) has an interval above 0 in three of the four readings for each prompt,
  with lower ends between +0.2 and +1.4 points. That is a small difference at this n.

## The `+ stop` arm, S1 and R1 (Pathumma, Full-page)

The stop is frozen: `loop_cut.variant_b` cuts the raw output, as in the registered analysis and in the decode-time
check. Only the extraction of the scored text changes (unwrap, then keep the text after an unclosed `<figure>`).
`scripts/model_survey_w4_stop_arm_fix.py`, output `docs/stage0/data/W4_STOP_ARM_FIX_de794e0.json`. The
`as_registered` rows reproduce the registered S1 and R1 values.

| prompt | rule | greedy F1 | + stop F1 | S1: stop minus greedy [95%] | one-sided p |
|---|---|---|---|---|---|
| card (primary) | as registered | 91.0 | 92.4 | +1.3 [0.0, +3.5] | 0.130 |
| card (primary) | both removed | 90.1 | 92.3 | **+2.2 [0.0, +4.9]** | **0.046** |
| `BENCHMARK_QUESTION` | as registered | 88.1 | 91.5 | +3.4 [+0.7, +6.6] | 0.0075 |
| `BENCHMARK_QUESTION` | both removed | 87.4 | 91.3 | +3.8 [+0.8, +7.2] | 0.0065 |

- The registered S1 cell for Pathumma (card, Full-page) is the one that did not pass (Holm-adjusted p 0.13). With
  both defects removed its p is 0.046. It is the largest p in the family, so its Holm-adjusted value is the same
  number, below 0.05. By the registered criterion this reading would pass.
- **The registered result is unchanged: S1 as registered is not met (12 of 13 cells).** This reading was made
  after the locked outputs had been seen, it changes the extraction rule, and its p is close to the threshold, so
  it is not a 13 of 13. What it shows is that this cell was sensitive to the extraction defects.
- The change comes from the greedy arm (91.0 to 90.1, the JSON and figure defects cost the stop-free output
  more); the stop arm hardly moves (92.4 to 92.3).
- R1 for Pathumma: ratio 15.8 [7.5, 32.0] as registered, 14.1 [6.6, 28.4] with both removed; passes either way
  (adjusted p 0.0021).
- S2 does not depend on extraction (it compares the cut and the raw text).

## Other models

Every output of all eight models (phase A, B, C archives) was scanned for the two defects
(`defect_scan_all_models` in the JSON): Pathumma has 30 JSON-wrapped and 9 unclosed-`<figure>` outputs; the other
seven models have none. No other model's score is affected, so none was redone.

## Not shown

- That Pathumma and Typhoon are equal: the intervals are about +/-5 to 6 points on Full-page.
- That keeping a figure's description is the right rule: dropping it (the contract) is the registered rule.
- Anything about the `+ stop` arms: the stop was not rescored here.

Code: `scripts/model_survey_w4_figure_fix.py`, tests `tests/test_w4_figure_fix.py`.
