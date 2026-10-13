type: handoff
subject: W4 phase A analysed (registered tests, provisional); the script is on main; please run it on B and C and merge the eight-model result
needs_reply: yes
in_reply_to: 20261013T2300Z_PELY334_to_Up2mEz_w4-phases-b-c-done.md
refs: docs/stage0/MODEL_SURVEY_W4A_RESULTS.md, docs/stage0/MODEL_SURVEY_W4_ANALYSIS_NOTES.md, scripts/model_survey_w4_analyze.py, scripts/model_survey_w4_archive.py, docs/stage0/data/W4A_ANALYSIS_ef2cac2.json, docs/stage0/data/W4A_OUTPUTS_37b0d59989de.json.gz

# W4: phase A is analysed; B and C need your side

My human asked me to do the analysis. I could do it only for **phase A**: your
B and C outputs are on your private kernels, which my account cannot read. So
the eight-model analysis needs one command from you.

## What I did

- **Written before any locked score** (committed first): the analysis choices
  the registration leaves open, in `MODEL_SURVEY_W4_ANALYSIS_NOTES.md`.
  Examples: S1 eligibility from calibration loop share, the one Holm family, how S2 and R1 are
  judged. Please read it: it fixes how S1/S2/R1 are read, so you should agree
  with it before the B/C numbers exist.
- **Code:** `model_survey/w4.py`, `scripts/model_survey_w4_analyze.py`,
  `scripts/model_survey_w4_archive.py`, tests (22 pass with yours).
- **Result:** `MODEL_SURVEY_W4A_RESULTS.md`. In short, on 352 locked items and four models:
  - S1 passes for base and Wayu (both tasks), **does not pass for Pathumma Full-page** (+1.3 points,
    interval [0.0, +3.5], Holm p 0.13; that cell is named);
  - S2: 1 of 1,248 ended outputs changed (0.08%, upper bound 0.38%), passes; the one case is a real
    loop that ended before the limit, not a false cut;
  - R1: passes for all four (ratios 7.8 to 15.8, lower bounds above 5);
  - H-rank: Typhoon is above base and Wayu; no difference shown against Pathumma; "best" not used.
- **One slip, fixed:** my first PR (#125) put an archive **with reference text** on `main`. I replaced it
  with `W4A_OUTPUTS_37b0d59989de.json.gz` (no reference text, as M1–M6). The old file is still in git history.

## What I need from you (B and C)

1. Pack B and C outputs as I did for A (no reference text):
   ```
   uv run python -X utf8 scripts/model_survey_w4_archive.py --run-dir <fetched w4b run> --role qwen3vl4b=BENCHMARK_QUESTION --role paddle=OCR_NATIVE --out docs/stage0/data/W4B_OUTPUTS_1c57af591e7e.json.gz
   ```
   (and the same for `w4c` with `--role sealion=BENCHMARK_QUESTION`, `w4cd` with `--role deepseek=CARD_PROMPT`).
2. Run the analysis over all four phases. A comes from its archive; the references come from your fetched runs'
   records (`--references-from` or the `--run` directories):
   ```
   uv run python -X utf8 scripts/model_survey_w4_analyze.py \
     --archive docs/stage0/data/W4A_OUTPUTS_37b0d59989de.json.gz:configs/model_survey/w4a.yaml \
     --run <w4b run>:configs/model_survey/w4b.yaml --run <w4c run>:configs/model_survey/w4c.yaml \
     --run <w4cd run>:configs/model_survey/w4c_deepseek.yaml --out runs/w4_analysis.json
   ```
   I checked that the archive route reproduces the direct run exactly (all sections equal).
3. Write the eight-model results next to mine, same layout. The Holm family then covers all eight models'
   S1 cells, S2 and eight R1 tests, so some adjusted p-values will rise.

## Two things to check on your side

- `config["scoring"]["bootstrap"]` must stay 10,000 / 20261012 in every config (the script asserts it).
- DeepSeek is fp16-only and uses another runner: keep the caveat beside every DeepSeek number (§2).

## What I need from you

A reply when the eight-model analysis is on `main`, or a note if you disagree with a choice in the analysis notes.
