# MODEL_SURVEY W4 — analysis notes (written before any locked score was computed)

Companion to `MODEL_SURVEY_W4_LOCKED_REGISTRATION_DRAFT.md` (APPROVED, §5–§7). The registration fixes the tests;
this file fixes the **choices it leaves open**, before `scripts/model_survey_w4_analyze.py` is run on locked
outputs. Written by Up2mEz's Claude Code session on 2026-10-13, when only phase A's outputs were held by that
account (phases B and C are on PELY334's account and are not in this repository).

Code: `src/labbs2026/model_survey/w4.py`, `scripts/model_survey_w4_analyze.py`,
`scripts/model_survey_w4_archive.py`, tests `tests/test_model_survey_w4_analysis.py`. The script was tested on the
phase-A calibration smoke (2 items, `--allow-calibration`, output marked `PLUMBING_ONLY`) and on synthetic counts.

## 1. What is read, per model

Primary prompt of each model (§2); Pathumma's `BENCHMARK_QUESTION` as a secondary, descriptive. Every locked item
once. Extraction v2 (`order_free.mark_counts`, `max_cer` 0.4, residual true), and the repeat-aware variant beside it
in every cell, for greedy and for greedy + stop (`loop_cut.variant_b`, k = 8 / 6, applied offline).

## 2. Choices made here

| question the registration leaves open | choice |
|---|---|
| Which models enter S1 | each (model, task) whose **calibration** looping share is at least 5%, looping meaning `reached_max_new_tokens`, at the model's primary prompt, from the calibration output archives (`T1_`, `M1_`, `M5_`, `M6A_`, `M6B_OUTPUTS_*`) |
| S1's p-value | one-sided cluster bootstrap, `p = (1 + #{draws ≤ 0}) / (1 + 10,000)`, on the Δ micro v2 F1 (stopped − greedy) |
| The Holm family | **one family**: the eligible S1 tests, S2, and one R1 per model; α = 0.05. S2's p is the exact one-sided binomial p of at most k changed among n ended outputs if the true share were 1% (the bootstrap cannot express uncertainty at k = 0); R1's p is the one-sided bootstrap p of the ratio against 3 |
| Verdict of S1 | passes when its Holm-adjusted p < 0.05 |
| Verdict of S2 and R1 | **as the registration words them**: S2 passes when the pooled point share is at most 1% (upper 95% bound reported, exact binomial and cluster bootstrap); R1 passes when the lower bound of the 95% percentile interval of the ratio is above 3. Their Holm-adjusted p is reported beside, as a conservative second reading |
| R1's terms | numerator `line_missing` + `span_missing`; denominator `misread_with_base` (misread, base read right); `attribute_marks(approximate_reorder=True)` on the **stopped** Full-page output; a zero denominator gives an infinite ratio |
| S2's population | primary-prompt outputs of every model read, both tasks, "ended" = did not reach `max_new_tokens`; "changed" = `variant_b` changes the text; the share of ended outputs with no repeat run is reported beside (equal to one minus the changed share for this rule) |
| Page clustering | items resampled with their `image_sha256`; all 352 items have distinct hashes, so it equals an item bootstrap |
| H-rank | for every model and prompt, per task: Typhoon (primary prompt) minus the model, micro F1, recall and precision, v2 and repeat-aware, paired 95% bootstrap; Pathumma's `BENCHMARK_QUESTION` is also compared with Typhoon's, the same prompt. "Best" only if Typhoon's lower bound is above 0 against every model on both tasks |
| Markup | structure counts of tags, `<figure>`, unclosed `<figure>`, JSON-wrapped outputs per cell, before scores are read; the unclosed-figure upper bound is applied to ended outputs only, as in M5 |

## 3. Phases

The analysis covers the phases whose outputs are supplied. Phase A (Typhoon, base, Wayu, Pathumma) is on this
account. **Phases B and C were run on PELY334's account and are not available here**, so a first analysis of A alone
is **provisional**: the Holm family grows when B and C are added (adjusted p-values can only rise) and S2 is pooled
over the models read. A claim is made only for models whose phase finished (§8), and the eight-model readings of
H-stop, H-read and H-rank need B and C.

## 4. What this analysis cannot show

- It does not show anything about models outside the registered eight, other benchmarks, or other prompts.
- S2's exact binomial treats every ended output as independent, though one page is read by every model; the
  cluster-bootstrap bound is reported beside it.
- The stop is applied **offline**. The decode-time stop reproduced the offline cut character for character on 185 of
  185 calibration loops, from re-encoded text (`W4_STOP_CHECK_ed02ad0.json`); no live generation with the criterion
  attached has been run, so "stops at decode time" is a statement about that replay.
- Contamination is stated beside every Typhoon and Pathumma number (§7).
