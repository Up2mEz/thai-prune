# MODEL_SURVEY W4 — results on the locked split (all eight models)

**Status: registered analysis of all three phases, read once.** Registration:
`MODEL_SURVEY_W4_LOCKED_REGISTRATION_DRAFT.md` (APPROVED, Decision Log 2026-10-12f and 2026-10-13a). Choices the
registration leaves open, fixed before any locked score was computed: `MODEL_SURVEY_W4_ANALYSIS_NOTES.md`
(Up2mEz; read and agreed by PELY334 before the B and C scores existed). Claim level
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. **Nothing here is a `CLAIMS.md` entry**; those need Up2mEz's human approval.
This file supersedes the provisional Holm family and pooled S2 of `MODEL_SURVEY_W4A_RESULTS.md`; that file's
per-model numbers for phase A are reproduced here unchanged.

**Scope.** Eight models, 352 locked items (128 Full-page OCR, 224 Text recognition), each read once:

| phase | run | models · primary prompt | T4-hours (cap) |
|---|---|---|---|
| A | `kaggle-model-survey-w4a-37b0d59989de` (Up2mEz) | Typhoon · BQ, base · BQ, Wayu · `OCR:`, Pathumma · card (BQ secondary) | 11.53 (18) |
| B | `kaggle-model-survey-w4b-1c57af591e7e` | Qwen3-VL-4B · BQ, PaddleOCR-VL · `OCR:` | 6.97 (10) |
| C | `kaggle-model-survey-w4c-1c57af591e7e`, `-w4cd-1c57af591e7e` | SEA-LION-4B · BQ; DeepSeek-OCR-2 · card `Free OCR.` | 4.84 + 3.16 (15) |

Total 26.5 T4-hours of the 43 approved. **DeepSeek-OCR-2 caveat, beside every DeepSeek number:** fp16 only (fp32
does not fit a T4) and its own runner (`remote_m6b`, eager attention; M6 Addendum 1).

Analysis: `scripts/model_survey_w4_analyze.py` at commit `0743f13` (clean tree), phase A from
`W4A_OUTPUTS_37b0d59989de.json.gz`, B and C from the fetched runs (checksums verified). Output
`docs/stage0/data/W4_ANALYSIS_0743f13.json` (no reference text, no output text). Outputs without references:
`W4B_`, `W4C_`, `W4CD_OUTPUTS_1c57af591e7e.json.gz`. 352 items, 352 distinct images, so the page bootstrap equals an
item bootstrap. Bootstrap: 10,000 resamples, seed 20261012, percentile 95% intervals.

## 1. Mark F1 per cell (order-free v2, and repeat-aware beside it)

| model · prompt | task | looped | greedy v2 | + stop v2 | greedy repeat-aware | + stop repeat-aware |
|---|---|---|---|---|---|---|
| Typhoon · BQ | Full-page | 4 | 92.6 | 94.1 | 91.6 | 94.1 |
| Typhoon · BQ | Text rec. | 2 | 73.7 | 77.2 | 73.5 | 77.2 |
| base · BQ | Full-page | 34 | 54.3 | 72.8 | 47.7 | 72.8 |
| base · BQ | Text rec. | 36 | 19.9 | 55.4 | 17.2 | 55.4 |
| Wayu · `OCR:` | Full-page | 25 | 73.6 | 78.4 | 72.1 | 78.4 |
| Wayu · `OCR:` | Text rec. | 49 | 35.8 | 64.9 | 35.4 | 64.9 |
| Pathumma · card | Full-page | 4 | 91.0 | 92.4 | 90.6 | 92.4 |
| Pathumma · card | Text rec. | 6 | 64.7 | 67.6 | 64.2 | 67.6 |
| Pathumma · BQ | Full-page | 8 | 88.0 | 91.5 | 87.4 | 91.5 |
| Pathumma · BQ | Text rec. | 5 | 65.7 | 72.7 | 65.3 | 72.7 |
| Qwen3-VL-4B · BQ | Full-page | 26 | 56.7 | 73.0 | 52.5 | 73.0 |
| Qwen3-VL-4B · BQ | Text rec. | 31 | 21.6 | 28.5 | 20.3 | 28.5 |
| Paddle · `OCR:` | Full-page | 33 | 60.2 | 68.6 | 57.4 | 68.6 |
| Paddle · `OCR:` | Text rec. | 30 | 42.3 | 51.0 | 40.6 | 51.0 |
| SEA-LION · BQ | Full-page | 39 | 43.3 | 58.4 | 35.6 | 58.4 |
| SEA-LION · BQ | Text rec. | 19 | 22.7 | 29.6 | 20.6 | 29.6 |
| DeepSeek · card (fp16) | Full-page | 43 | 35.4 | 52.5 | 28.8 | 52.5 |
| DeepSeek · card (fp16) | Text rec. | 35 | 17.8 | 47.8 | 17.4 | 47.8 |

"Looped" = reached `max_new_tokens` (3072). Text recognition precision is low for most models after the stop
(Qwen3-VL-4B 17.7%, SEA-LION 19.5%, DeepSeek 41.6%, Paddle 43.1%; Typhoon 77.9%): the items show a whole page while
the question asks for part of it (M1's finding; not tested here).

## 2. H-stop

**S1** (Δ mark F1, stop − greedy, in points; tested when the model looped on at least 5% of calibration items in that
task; one Holm family of 22 tests: 13 S1, S2, 8 R1):

| model · task | calibration loop share | Δ F1 [95%] | Holm p | S1 |
|---|---|---|---|---|
| base · Full-page | 43.5% | +18.4 [+14.3, +22.2] | 0.0021 | passes |
| base · Text rec. | 14.7% | +35.6 [+29.6, +40.9] | 0.0021 | passes |
| Wayu · Full-page | 26.1% | +4.8 [+1.8, +8.3] | 0.0021 | passes |
| Wayu · Text rec. | 20.2% | +29.1 [+18.7, +38.0] | 0.0021 | passes |
| **Pathumma · Full-page** | 5.8% | **+1.3 [0.0, +3.5]** | **0.13** | **does not pass** |
| Qwen3-VL-4B · Full-page | 27.5% | +16.3 [+11.7, +20.3] | 0.0021 | passes |
| Qwen3-VL-4B · Text rec. | 11.9% | +7.0 [+4.2, +10.1] | 0.0021 | passes |
| Paddle · Full-page | 39.1% | +8.4 [+4.5, +12.0] | 0.0021 | passes |
| Paddle · Text rec. | 14.7% | +8.8 [+2.2, +14.6] | 0.0036 | passes |
| SEA-LION · Full-page | 31.9% | +15.2 [+11.9, +18.4] | 0.0021 | passes |
| SEA-LION · Text rec. | 6.4% | +6.9 [+3.8, +10.0] | 0.0021 | passes |
| DeepSeek · Full-page (fp16) | 39.1% | +17.1 [+12.8, +21.5] | 0.0021 | passes |
| DeepSeek · Text rec. (fp16) | 9.2% | +30.0 [+21.8, +36.3] | 0.0021 | passes |
| not tested (under 5%): Typhoon Full-page / Text rec., Pathumma Text rec. | 2.9% / 0.9% / 1.8% | +1.5 [−0.5, +4.1] / +3.5 [0.0, +11.0] / +3.0 [0.0, +6.7] | | descriptive |

- **Reading, as registered:** 12 of the 13 eligible cells pass: the stop raises mark F1 on unseen items for the
  models that loop often (base, Wayu, Qwen3-VL-4B, Paddle, SEA-LION, DeepSeek), on both tasks. The registered
  criterion asks every eligible cell to pass, and **Pathumma's Full-page cell does not** (named, as in phase A):
  its gain is small and its interval reaches 0. Adding B and C did not change that cell's adjusted p (0.13, the
  largest p in the family).
- The repeat-aware variant gives the same direction in every cell (descriptive).
- Pathumma's secondary prompt (descriptive): +3.4 [+0.7, +6.6] Full-page, +7.0 [+1.3, +13.1] Text rec.

**S2** (ended outputs the stop changes): **1 of 2,400** ended outputs (0.04%), pooled over the eight models and both
tasks; S2 **passes as written**. Upper 95% bound: 0.20% (exact one-sided binomial), 0.13% (cluster bootstrap).

- By model: Typhoon 1 of 346, base 0 of 282, Wayu 0 of 278, Pathumma 0 of 342, Qwen3-VL-4B 0 of 295, Paddle 0 of
  289, SEA-LION 0 of 294, DeepSeek 0 of 274. The one changed output is phase A's Typhoon case (a real loop that
  ended on its own; `MODEL_SURVEY_W4A_RESULTS.md` §2). B and C add no changed output.

## 3. H-read: R1 (Full-page, stopped outputs; (line missing + span missing) ÷ (misread with base right))

| model | ratio [95%] | Holm p | R1 |
|---|---|---|---|
| Typhoon | 8.2 [5.5, 14.3] | 0.0021 | passes |
| base | 7.8 [5.0, 11.7] | 0.0021 | passes |
| Wayu | 10.8 [7.1, 16.0] | 0.0021 | passes |
| Pathumma (card) | 15.8 [7.5, 32.0] | 0.0021 | passes |
| Qwen3-VL-4B | 6.1 [3.7, 9.2] | 0.0069 | passes |
| Paddle | **4.7 [3.2, 6.7]** | 0.029 | passes, narrowly |
| SEA-LION | 7.8 [5.6, 10.4] | 0.0021 | passes |
| DeepSeek (fp16) | 7.8 [5.8, 10.5] | 0.0021 | passes |

All eight lower bounds are above 3. **Reading:** for each of the eight registered models, on locked Full-page pages,
marks are lost mainly because the text is **absent from the output** (whole lines and spans), not misread where the
base consonant is right. Absence is observed; a failure to read is not (W1 §3). The registration allows the claim to
be stated for the models that pass, which is all eight; it is a statement about these eight models on this
benchmark, not about Thai OCR VLMs beyond them. Paddle's lower bound (3.2) is the closest to the threshold.

Attribution counts of reference marks on stopped Full-page outputs (correct / line missing / span missing /
misread, base right / misread, other), B and C: Qwen3-VL-4B 20,370 / 5,220 / 1,175 / 1,042 / 1,845; Paddle
17,016 / 6,122 / 2,359 / 1,821 / 2,376; SEA-LION 14,717 / 6,529 / 3,931 / 1,346 / 3,195; DeepSeek 13,570 / 6,527 /
4,453 / 1,405 / 3,703. Phase A's are in `MODEL_SURVEY_W4A_RESULTS.md` §3 (unchanged).

## 4. H-rank (reported, not tested): Typhoon minus the model, mark F1 in points, paired 95% bootstrap

| comparison | Full-page | Text recognition |
|---|---|---|
| Typhoon − base (BQ) | +38.3 [+30.4, +45.4] | +53.8 [+43.6, +63.2] |
| Typhoon − Wayu (`OCR:`) | +19.0 [+11.7, +26.1] | +37.9 [+23.7, +50.5] |
| Typhoon − Pathumma (BQ) | +4.5 [−2.0, +10.7] | +8.0 [−5.5, +20.9] |
| Typhoon − Pathumma (card) | +1.5 [−3.1, +6.5] | +9.0 [−3.6, +21.3] |
| Typhoon − Qwen3-VL-4B (BQ) | +35.8 [+27.9, +42.8] | +52.1 [+41.8, +61.4] |
| Typhoon − Paddle (`OCR:`) | +32.3 [+24.0, +40.2] | +31.4 [+17.2, +44.3] |
| Typhoon − SEA-LION (BQ) | +49.3 [+42.5, +55.3] | +51.0 [+40.3, +60.6] |
| Typhoon − DeepSeek (card, fp16) | +57.2 [+50.0, +63.4] | +55.9 [+43.4, +66.0] |

- Against the six models other than Pathumma, Typhoon's mark F1 is higher on both tasks (intervals above 0).
- Against Pathumma on either prompt and either task, **no difference is shown at n = 128 (Full-page, half-width
  about ±6) and n = 224 (Text rec., about ±13)**; the intervals include 0. This is not "equivalent".
- On Text recognition the F1 gap to Qwen3-VL-4B, Wayu and base is a precision gap: recall differences are −2.0
  [−12.2, +7.8], −7.9 [−19.9, +4.5] and +2.1 [−6.2, +10.0] (descriptive). Pathumma's recall is higher than
  Typhoon's there (Typhoon − Pathumma −18.6 [−28.7, −8.8] BQ), and its precision lower.
- "Best" is **not used**: Typhoon's lower bound is not above 0 against Pathumma.
- Contamination, beside every Typhoon and Pathumma number: Typhoon is from ThaiOCRBench's group, and Pathumma's
  377K training samples are unnamed.

## 5. Markup audit and the registered upper bound

Read before the scores. Qwen3-VL-4B, Paddle and SEA-LION have no output with a tag. DeepSeek has one (`B3FAC114`,
Text rec.: `<img src="imgs/…">` and `<sub>`), which extraction v2 removes. None of the four has a `<figure>` or a
JSON-wrapped output, so the unclosed-figure upper bound applies to Pathumma only, as in phase A: Pathumma's
Full-page F1 would be 90.1 (BQ, 4 outputs, 1,309 marks) and 92.4 (card, 3 outputs, 857 marks); Typhoon minus
Pathumma would be +2.5 [−3.6, +8.4] and +0.2 [−4.3, +4.9]. It does not change the H-rank reading. Markdown
(bold, headings, tables) in raw outputs of all four B/C models is removed by extraction v2 (checked per run).

## 6. What this shows, and does not

- **Shows (eight models, locked split, one read each):**
  - the stop is a gain in every eligible cell but one; that cell (Pathumma Full-page) is named, so H-stop's S1 is
    met for seven of the eight models, not all;
  - the stop does not alter outputs that ended (1 of 2,400, a real loop);
  - on Full-page pages, lost marks are dominated by absence from the output in all eight models (Paddle narrowly).
- **Does not show:** that Typhoon is "best" (Pathumma is not separated from it); that stopping at decode time works
  live (the stop is offline; the decode-time criterion was replayed on calibration text, 185 / 185, and has not
  generated live); anything about other models, benchmarks or prompts; DeepSeek in fp32.
- **Not a gate.** W4 opens or passes no gate.

## 7. Disclosures

- The first launch of the eight-model analysis was stopped before it wrote any output (the session ended); it was
  started again unchanged from the same commit. No score was seen in between.
- The locked split was read once per model, by phases A, B and C. No locked run was repeated. B and C each had a
  2-item calibration smoke first.
- Phase A's per-model sections of the two analysis files (cells, audit, S1, R1, H-rank, upper bound) are identical
  (compared key by key); only the Holm-adjusted p-values and the pooled S2 changed, as that file said they would.
  One rounding differs in prose: Wayu Full-page S1 is +4.849 points, shown here as +4.8 and in
  `MODEL_SURVEY_W4A_RESULTS.md` as +4.9.
