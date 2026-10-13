# MODEL_SURVEY W4, phase A — results on the locked split (provisional: four of eight models)

**Status: registered analysis of phase A, read once.** Registration:
`MODEL_SURVEY_W4_LOCKED_REGISTRATION_DRAFT.md` (APPROVED, Decision Log 2026-10-12f and 2026-10-13a). Choices the
registration leaves open, fixed before any locked score was computed: `MODEL_SURVEY_W4_ANALYSIS_NOTES.md`.
Claim level `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. **Nothing here is a `CLAIMS.md` entry**; those need
Up2mEz's human approval.

**Scope.** Phase A only: Typhoon OCR 1.5 2B, Qwen3-VL-2B (base), Wayu, Pathumma (card prompt primary,
`BENCHMARK_QUESTION` secondary), 352 locked items, 128 Full-page OCR and 224 Text recognition, each read once
(`kaggle-model-survey-w4a-37b0d59989de`, 11.53 T4-hours). **Phases B and C (Qwen3-VL-4B, PaddleOCR-VL, SEA-LION,
DeepSeek-OCR-2) ran on PELY334's account and are not analysed here.** So the readings below are for these four
models, S2 is pooled over four models, and the Holm family is the phase-A one: with B and C added the family grows
and adjusted p-values can only rise. A claim about "Thai OCR VLMs" needs all eight.

Analysis: `scripts/model_survey_w4_analyze.py` at commit `ef2cac2` (clean tree), output
`docs/stage0/data/W4A_ANALYSIS_ef2cac2.json` (no reference text, no output text). Outputs without references:
`docs/stage0/data/W4A_OUTPUTS_37b0d59989de.json.gz`. 352 items, 352 distinct images, so the page bootstrap equals
an item bootstrap. Bootstrap: 10,000 resamples, seed 20261012, percentile 95% intervals.

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

"Looped" = reached `max_new_tokens` (3072). Text recognition has a low precision for several models (Wayu 22.7%,
base 11.4%, Pathumma 49–50%): the items show a whole page while the question asks for part of it, and `OCR:` or
a generic prompt transcribes everything (M1's finding; not tested here).

## 2. H-stop

**S1** (Δ mark F1, stop − greedy, in points; a cell is tested when the model looped on at least 5% of calibration
items in that task; Holm-adjusted one-sided p):

| model · task | calibration loop share | Δ F1 [95%] | Holm p | S1 |
|---|---|---|---|---|
| base · Full-page | 43.5% | +18.4 [+14.3, +22.2] | 0.0009 | passes |
| base · Text rec. | 14.7% | +35.6 [+29.6, +40.9] | 0.0009 | passes |
| Wayu · Full-page | 26.1% | +4.9 [+1.8, +8.3] | 0.0009 | passes |
| Wayu · Text rec. | 20.2% | +29.1 [+18.7, +38.0] | 0.0009 | passes |
| **Pathumma · Full-page** | 5.8% | **+1.3 [0.0, +3.5]** | **0.13** | **does not pass** |
| not tested (under 5%): Typhoon Full-page / Text rec., Pathumma Text rec. | 2.9% / 0.9% / 1.8% | +1.5 [−0.5, +4.1] / +3.5 [0.0, +11.0] / +3.0 [0.0, +6.7] | | descriptive |

- **Reading, as registered:** the stop raises mark F1 on unseen items for the models that loop a lot (base, Wayu).
  The registered criterion needs every eligible cell to pass, and **Pathumma's Full-page cell does not**: its gain
  is small and its interval reaches 0. That cell is named as the cell where the gain does not replicate.
- The lower bound 0.0 is not a rounding: with 8 looping pages of 128, many resamples draw few or none of them and
  give Δ = 0 exactly.
- The repeat-aware variant gives the same direction in every cell (Pathumma Full-page +1.8, descriptive).
- Pathumma's secondary prompt (descriptive): +3.4 [+0.7, +6.6] Full-page, +7.0 [+1.3, +13.1] Text rec.

**S2** (ended outputs the stop changes): **1 of 1,248** ended outputs (0.08%), pooled over the four models and both
tasks; the point share is at most 1%, so S2 **passes as written**. Upper 95% bound: 0.38% (exact one-sided
binomial), 0.24% (cluster bootstrap). Holm-adjusted p 0.0005.

- By model: Typhoon 1 of 346, base 0 of 282, Wayu 0 of 278, Pathumma 0 of 342. The share of ended outputs with no
  repeat run is therefore 100% for every model but Typhoon (99.7%).
- The one changed output (Typhoon, a Full-page item, 1,162 tokens) is a real loop that **ended on its own**
  before the limit: one table cell repeated at least 8 times, absent from the reference. The stop cut it at the
  first copy; it did not cut correct text. So it is a loop the "reached `max_new_tokens`" test misses, not a
  false cut. Read for this report only; S2 does not ask for it (S2 passed).

## 3. H-read: R1 (Full-page, stopped outputs; (line missing + span missing) ÷ (misread with base right))

| model | ratio [95%] | R1 |
|---|---|---|
| Typhoon | 8.2 [5.5, 14.3] | passes |
| base | 7.8 [5.0, 11.7] | passes |
| Wayu | 10.8 [7.1, 16.0] | passes |
| Pathumma (card) | 15.8 [7.5, 32.0] | passes |

All four lower bounds are above 3, and the Holm-adjusted p is 0.0009 for each. **Reading:** for these four models,
on locked Full-page pages, marks are lost mainly because the text is **absent from the output** (whole lines and
spans), not misread where the base consonant is right. Absence is observed; a failure to read is not (a line absent
after a loop does not separate the loop from not reading it, W1 §3). The claim is for these four models; it needs
B and C for the rest.

Attribution counts of reference marks on stopped Full-page outputs (correct / line missing / span missing /
misread, base right / misread, other): Typhoon 27,224 / 1,086 / 714 / 220 / 447; base 19,492 / 6,889 / 1,138 /
1,027 / 1,178; Wayu 20,268 / 4,826 / 2,151 / 648 / 1,680; Pathumma (card) 25,786 / 2,332 / 480 / 178 / 678
(approximate reorder rows not shown).

## 4. H-rank (reported, not tested): Typhoon minus the model, mark F1 in points, paired 95% bootstrap

| comparison | Full-page | Text recognition |
|---|---|---|
| Typhoon − base (BQ) | +38.3 [+30.4, +45.4] | +53.8 [+43.6, +63.2] |
| Typhoon − Wayu (`OCR:`) | +19.0 [+11.7, +26.1] | +37.9 [+23.7, +50.5] |
| Typhoon − Pathumma (BQ) | +4.5 [−2.0, +10.7] | +8.0 [−5.5, +20.9] |
| Typhoon − Pathumma (card) | +1.5 [−3.1, +6.5] | +9.0 [−3.6, +21.3] |

- Against base and Wayu, Typhoon's mark F1 is higher on both tasks (intervals above 0).
- Against Pathumma on either prompt and either task, **no difference is shown at n = 128 (Full-page, half-width
  about ±6) and n = 224 (Text rec., about ±13)**; the intervals include 0. This is not "equivalent".
- "Best" is **not used**: Typhoon's lower bound is not above 0 against every model on both tasks.
- Contamination, beside every Typhoon and Pathumma number: Typhoon is from ThaiOCRBench's group, and Pathumma's
  377K training samples are unnamed.

## 5. Markup audit and the registered upper bound

Pathumma emits markup on Full-page (27–28 of 128 outputs contain a tag; 21 and 9 are JSON-wrapped for the
`BENCHMARK_QUESTION` and card prompts; 5 and 4 have an unclosed `<figure>`, of which 4 and 3 ended on their own).
Typhoon has markup in 4 outputs, base in none, Wayu in 1. Extraction v2 stays primary, unchanged (§5).

Upper bound (§5; ended outputs with an unclosed `<figure>` credited with a perfect read): Pathumma's Full-page F1
would be 90.1 (BQ, 4 outputs, 1,309 marks) and 92.4 (card, 3 outputs, 857 marks); Typhoon minus Pathumma would
then be +2.5 [−3.6, +8.4] and +0.2 [−4.3, +4.9]. It does not change the H-rank reading.

## 6. What this shows, and does not

- **Shows (four models, locked split, one read each):** the stop is a large gain where a model loops often, does
  not alter outputs that ended, and the loss of marks on Full-page pages is dominated by absence in all four
  models. The gain for Pathumma Full-page is not shown (interval reaches 0).
- **Does not show:** any statement about the four models not analysed; that Typhoon is "best" (Pathumma is not
  separated from it); that stopping at decode time works live (the stop is offline; the decode-time criterion was
  replayed on calibration text and has not generated live); anything about other benchmarks or prompts.
- **Not a gate.** W4 opens or passes no gate.

## 7. Disclosures

- The first run of the analysis (`runs/` only) omitted §5's unclosed-figure upper bound. It was added in a second
  commit and the script re-run; the two outputs are identical in every other section (compared).
- An earlier commit (PR #125) put a raw archive with benchmark reference text on `main`; it was replaced by the
  reference-free `W4A_OUTPUTS_*.json.gz` as M1–M6 do. The old file remains in git history.
- The locked split was read once, by phase A's run. No locked run was repeated.
