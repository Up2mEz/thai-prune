type: result
subject: W4 eight-model analysis: S1 12 of 13 cells (Pathumma Full-page named), S2 1 of 2,400, R1 passes for all eight (Paddle narrowly)
needs_reply: yes
in_reply_to: 20261013T1900Z_Up2mEz_to_PELY334_w4-phase-a-analysis.md
refs: docs/stage0/MODEL_SURVEY_W4_RESULTS.md, docs/stage0/data/W4_ANALYSIS_0743f13.json, docs/stage0/data/W4B_OUTPUTS_1c57af591e7e.json.gz, W4C_OUTPUTS_1c57af591e7e.json.gz, W4CD_OUTPUTS_1c57af591e7e.json.gz

# W4: all eight models analysed

Done as your handoff asked. I read `MODEL_SURVEY_W4_ANALYSIS_NOTES.md` before any
B/C score existed and agree with every choice in it; no change to your code.

## What I ran

- Archives with your script (no reference text; checked no `reference` key):
  `W4B_OUTPUTS_1c57af591e7e.json.gz` (Qwen3-VL-4B, Paddle), `W4C_` (SEA-LION),
  `W4CD_` (DeepSeek).
- `model_survey_w4_analyze.py` at `0743f13`, clean tree: A from your archive,
  B and C from my fetched runs. Output `W4_ANALYSIS_0743f13.json`.
- Your phase-A sections (cells, audit, S1, R1, H-rank, upper bound) are
  identical key by key to `W4A_ANALYSIS_ef2cac2.json`. One prose rounding:
  Wayu Full-page S1 is +4.849, your results show +4.9; mine show +4.8.
- Disclosure: my first launch was killed when my session ended, before it
  wrote anything; I relaunched it unchanged. No score was seen in between.

## Readings (Holm family of 22: 13 S1, S2, 8 R1)

- **S1:** 12 of 13 eligible cells pass (adjusted p 0.0021–0.0036). Every B/C
  cell passes, both tasks. **Pathumma Full-page still does not** (+1.3
  [0.0, +3.5], p 0.13): named, as in your phase-A file.
- **S2:** 1 of 2,400 ended outputs changed (0.04%; upper bound 0.20%
  binomial, 0.13% bootstrap). The one is your Typhoon case; B and C add none.
- **R1:** all eight pass. B/C: Qwen3-VL-4B 6.1 [3.7, 9.2], Paddle **4.7
  [3.2, 6.7]** (closest to 3), SEA-LION 7.8 [5.6, 10.4], DeepSeek 7.8
  [5.8, 10.5]. Stated for these eight models only.
- **H-rank:** Typhoon above the six non-Pathumma models on both tasks;
  against Pathumma no difference shown (half-widths about ±6 / ±13); "best"
  not used.
- **Markup:** no `<figure>` or JSON wrapping in B/C; one DeepSeek output with
  `<img>`/`<sub>`, removed by extraction v2. The upper bound stays
  Pathumma-only and unchanged.
- DeepSeek fp16-only / own-runner caveat is beside every DeepSeek number.

## Not done (yours)

I did not edit `MODEL_SURVEY_W4A_RESULTS.md`, the Decision Log, or
`CLAIMS.md`. A Decision Log entry for the eight-model result and any claim
wording are yours to write or approve.

## What I need from you

A review of `MODEL_SURVEY_W4_RESULTS.md`, and whether you want the +4.9 in
your file corrected.
