# MODEL_SURVEY_M5 — registration (Track E: Pathumma Vision 3.0.0-Re)

**Status: `APPROVED` by PELY334 in session on 2026-10-11** ("รัน smoke แล้วรันเต็มเลย":
smoke, then the full run). Written before any M5 output existed. Up2mEz's work split (collab
`20261011T1315Z_Up2mEz_to_PELY334_paper-prep-work-split.md`, W2) asks for this
model first and alone. Calibration only, PELY334's quota, own namespace; under
the standing delegation (PR #79, COLLABORATION.md §3b) Up2mEz reviews
afterwards. Parameters: `configs/model_survey/m5.yaml`. Clearance:
`MODEL_SURVEY_M5_CLEARANCE.md`. Claim level of every result:
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

**Question.** Under T1's protocol, how does Pathumma Vision 3.0.0-Re read Thai
marks, next to Typhoon OCR 1.5 and the base, on the same items?

- **(a) Against Typhoon.** NECTEC's card reports ThaiOCRBench scores above
  Typhoon's on Text recognition (0.674 vs 0.592) and below on Full-page
  (0.736 vs 0.772), with the metric unstated. If our protocol confirms a lead,
  the paper cannot call Typhoon the best open Thai OCR model.
- **(b) Against the base.** Pathumma is a second Thai fine-tune of
  Qwen3-VL-2B-Instruct (§2 of the clearance: same architecture, only weights
  differ). This gives a second specialized-vs-base pair for RQ-C.

## 1. Fixed inputs: M1's, unchanged

Model `nectec/Pathumma-llm-vision-3.0.0-re@08bb11dcabf509ac3fa3ac0014ecd44eadb9729b`.

Everything else is M1's and is tested equal to `configs/model_survey/m1.yaml`
(`tests/test_model_survey_m5.py`):

- data: T1's 178 calibration items, T1's image policy then the model's own
  processor;
- decoding: greedy, `max_new_tokens=3072`, `use_cache=true`;
- runtime: fp16 with fp32 fallback, `sdpa`;
- scoring: M1's;
- comparison outputs: T1's archived Typhoon and base outputs
  (`BENCHMARK_QUESTION`).

Prompts:

- **`CARD_PROMPT`** `อ่านข้อความในภาพนี้` (primary): the card's Quickstart
  prompt. This is M1's rule, "card prompt primary".
- `BENCHMARK_QUESTION` (secondary).

Code: M1's (`model_survey.remote`, `scripts/model_survey_kaggle.py --config
configs/model_survey/m5.yaml`, `scripts/model_survey_analyze.py --config …`).
Two changes:

- the scripts take `--config`;
- `plan.PROMPT_KINDS` gains `CARD_PROMPT`.

M1's defaults are unchanged.

## 2. Outcomes

- **Primary.** For each task, order-free v2 mark F1 (with recall and
  precision) of the primary prompt. The paired difference to Typhoon
  (`BENCHMARK_QUESTION`) on the same items, with a 95% item bootstrap (2,000
  resamples, seed 20261010).
- **Secondary.**
  - the same difference to the base;
  - the repeat-aware variant (`mark_counts(..., repeat_aware=True)`, PR #85),
    reported beside v2;
  - T1 scoring v2 per cell;
  - the secondary prompt;
  - W1's stop and attribution, applied to Pathumma's outputs as to the other
    models (`scripts/model_survey_w1.py`).

## 3. What each pattern would mean, stated in advance

| pattern | reading |
|---|---|
| Text recognition F1 above Typhoon, interval excluding 0 | the card's lead holds under our protocol; the paper does not call Typhoon the best open Thai OCR model |
| interval including 0 on a task | no difference shown on that task; "comparable", not "better" |
| below Typhoon with the interval below 0, on both tasks | Typhoon stays the best measured here; the card's lead does not hold under this metric |
| well above the base on both tasks | a second Thai fine-tune of the same base gains marks; RQ-C has two pairs |
| Pathumma's loss is mostly whole lines absent or loops (W1 attribution) | claim (2) "not reading, not misreading" extends to a third Thai model |

"Above", "below" and "well above" are read on the paired intervals and
reported with them; nothing here is a gate.

## 4. Budget, smoke, stopping

- **Estimate.** The base took 2.1 GPU-hours for `BENCHMARK_QUESTION` in T1.
  Pathumma is the same size, with two prompts, giving about 4 GPU-hours,
  about 2 hours per shard on two T4s, less if it loops less than the base.
- **Deadlines.** Each unit stops starting items after **3.0 h**.
- **Cap: 6 T4-hours** of session time.
- **Smoke first: `--smoke 2`.** It checks dtype, finiteness, garbage or
  overflow in fp16 output, `use_cache`, seconds per token, and that no image
  is written.
  - If fp16 output is degenerate where fp32 is not, M5 stops and an addendum
    is written before any full run.

## 5. Not in scope

Other models (M6), the locked split, any remedy, sampling, the card's
`3.0.0-preview`, and any claim beyond this checkpoint.

## Addendum 1, 2026-10-11 — after the smoke, before the full run

No full-run output exists. The smoke (`kaggle-model-survey-m5-4c0a721af760-smoke2`,
first two calibration items, both Full-page, both prompts) generated all four
outputs and then failed while writing the manifest.

- **Engineering fault.** `remote.py` looked up the config hash under M1's
  path. It now uses the run's config path (`spec["config_path"]`, tested).
  M1's runs are unaffected, because the default is M1's path.
- **Precision.** fp16 output is readable Thai on all four outputs. There is
  no garbage or overflow and no fp32 fallback. The QAT/bf16 concern does not
  show on these two pages.
- **Markup.** There is no HTML in any output. One output, `CARD_PROMPT` on
  `0159AF30`, comes wrapped in Typhoon OCR's JSON format, `{"natural_text":
  "..."}`, with newlines as `\n` escapes. It reads the page, then falls into
  a degenerate loop (`/nbs/";"` repeated) to the token limit.
- **Added before the full run.** The registered primary stays M1's scoring
  of the output as written. A **secondary** score applies
  `model_survey.m5.unwrap_natural_text` first (tested). It returns the
  `natural_text` value of a wrapped output, the decoded prefix if the JSON
  never closed, and any other output unchanged. Run it with
  `scripts/model_survey_analyze.py --unwrap-natural-text`. The results report
  how many outputs were wrapped, per cell, and both scores.
- Everything else in §1–§5 stands. The full run follows without a second
  smoke, because the fault was in the manifest step after generation.

## Addendum 2, 2026-10-12 — contamination caveat (added after the results, at Up2mEz's request)

Written after the full-run results existed (`MODEL_SURVEY_M5_RESULTS.md`), in
answer to Up2mEz's review (collab
`20261011T1903Z_Up2mEz_to_PELY334_review-w1-m5-pr79-merged.md`). It adds a
caveat to question (a); it changes no outcome, pattern or reading.

- **Contamination, next to question (a).** M1 and T1 carry this caveat, and
  M5 should have. Overlap with ThaiOCRBench cannot be ruled out for either
  model in the comparison:
  - Typhoon comes from the group that made ThaiOCRBench.
  - Pathumma's card says it was fine-tuned on "377K OCR training samples"
    without naming them, and the card reports ThaiOCRBench scores itself.
- **Consequence.** A lead on Text recognition, or on either task, would be
  exposed to benchmark overlap, just as Typhoon's level is. The paper's
  wording about the best open Thai OCR model depends on that.

