# MODEL_SURVEY W4: Pathumma's unclosed `<figure>` read as page text (post hoc, descriptive)

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** Written 2026-10-18 by Up2mEz's session. This is a
second reading of the locked phase-A outputs with one extraction rule changed. It is **post hoc**, it is not
one of the registered tests, and it replaces no number in `MODEL_SURVEY_W4_RESULTS.md`.

## What was wrong

Extraction v2 (`thai_marks/extract.py`) follows the `TYPHOON_CARD` contract: a `<figure>` holds a description of
an image, so its content is dropped. A `<figure>` that is never closed therefore runs to the end of the output.
In nine Pathumma Full-page outputs (five under `BENCHMARK_QUESTION`, four under the card prompt; seven distinct
pages) the tag is never closed and real page text follows it. In `BFE7C5A8` the page's own flowchart text sits
after the tag, in `78BB936B` the rest of a table page does. The registered analysis kept this and bounded it
(`upper_bound_unclosed_figure`: those items credited with a perfect read, ended outputs only).

## What was done

`scripts/model_survey_w4_figure_fix.py`: the opening tag of a `<figure>` with no `</figure>` anywhere in the output
is removed, so the text after it is kept (the figure's own description is kept too, and adds surplus marks).
The rule is applied to Typhoon and Pathumma alike (it changes no Typhoon output). Scoring, bootstrap (10,000
resamples, seed 20261012, paired by page) and the paired difference are the registered ones. Output:
`docs/stage0/data/W4_FIGURE_FIX_ba61f71.json` (no output or reference text).

## Result (Full-page OCR, locked split, order-free v2)

Typhoon minus Pathumma, points, 95% interval:

| Pathumma prompt | | F1 | recall | precision |
|---|---|---|---|---|
| card (primary) | as registered | +1.5 [-3.1, +6.5] | +4.2 [+0.4, +8.4] | -1.1 [-9.5, +7.4] |
| card (primary) | unclosed figure kept | +1.4 [-3.4, +6.5] | +2.0 [-0.8, +4.7] | +0.9 [-8.3, +10.0] |
| `BENCHMARK_QUESTION` | as registered | +4.5 [-2.0, +10.7] | +5.2 [+0.4, +10.4] | +3.8 [-5.6, +13.0] |
| `BENCHMARK_QUESTION` | unclosed figure kept | +3.5 [-2.7, +9.4] | +1.9 [-1.7, +5.4] | +5.0 [-4.7, +14.2] |

Text recognition is unchanged (no affected output).

- The F1 difference hardly moves and its interval still contains 0 in both prompts: the reading "no difference
  shown" stands.
- The recall difference shrinks from about +4 to +5 points to about +2 points and its interval now contains 0 in
  both prompts. The recall advantage reported for Typhoon in the registered table was partly the extraction.
- The registered upper bound (+0.2 and +2.5 on F1) was a limit, not an estimate; the rescoring lands between the
  registered figure and that bound.

## Not shown

- That Pathumma and Typhoon are equal: the intervals are about +/-6 points on Full-page.
- That keeping the figure's description is the right rule; it is one of two bounds (dropping it all is the
  registered rule, crediting it all is the upper bound).
- Anything about the nine JSON-wrapped Pathumma outputs: their `\n` sequences are literal characters in
  extraction v2. This was not changed here.

Code: `scripts/model_survey_w4_figure_fix.py`.
