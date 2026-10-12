# MODEL_SURVEY W4 — confirmatory registration on the locked split (DRAFT)

**Status: `DRAFT`. Not authorized. Do not run.** Drafted by PELY334's Claude
Code session on 2026-10-12, as Up2mEz's work split asks (collab
`20261011T1315Z_Up2mEz_to_PELY334_paper-prep-work-split.md`, W4): "draft the
registration; do not run it". The locked split needs **both researchers'**
approval (COLLABORATION.md §3b, Decision Log 2026-10-11c, Consequences). This
draft opens nothing.

No locked item, image, reference or output was opened, counted or inspected
in writing this draft. Item counts below are derived from the split's
definition, not from the data.

**Open slots.** M6 and W3 have finished (`MODEL_SURVEY_M6_RESULTS.md`,
`MODEL_SURVEY_W3_RESULTS.md`). The slots below now hold **proposed** values,
marked *proposed*; the approval revision confirms or changes them before
anyone signs. The remaining ⟨…⟩ are filled from the locked run itself or at
approval.

## 0. Why confirm, and what

Every Thai-mark result so far is calibration-only and exploratory. Three
hypotheses in `docs/CLAIMS.md` ("HYPOTHESIS (needs more models and/or the
locked split)") are what the paper would assert. W4 tests the first two on
unseen items and reports the third.

| id | hypothesis (CLAIMS.md wording) | calibration evidence |
|---|---|---|
| **H-read** | Thai OCR VLMs lose marks mainly by not reading (loops, text not found, skipped lines) rather than by misreading marks | W1 (five models), M5 (Pathumma), M6 (SEA-LION, InternVL, DeepSeek-OCR-2): nine models, four families; T2 and W3 teacher-forced (Typhoon, base, Pathumma, Qwen3-VL-4B) |
| **H-stop** | Stopping at a detected loop raises mark F1 across models without changing non-looping outputs | W1: every model, 2 of 726 ended outputs changed; M5: 1 of 172; M6: InternVL 4 of 95 (loops that ended with EOS before the limit), others 0 |
| **H-rank** (reported, not tested) | Typhoon's standing among open Thai OCR models | M1, M5, M6: no difference shown against Pathumma; every other model below Typhoon |

## 1. Items

- **Locked split.** ThaiOCRBench `typhoon-ai/ThaiOCRBench@ca610d1ab330`, test
  split, tasks Full-page OCR and Text recognition. The complement of T1's
  calibration split: `thai_marks.split.calibration_ids`, seed 20260927,
  fraction 0.30, stratified by task and category. Calibration has 178 items,
  so the locked split has about 415 (about 70%). The exact count is recorded
  by the run, not looked up beforehand.
- **Every locked item, once.** No item is dropped after outputs exist.
  - An item that fails engineering-wise (a crash, or non-finite logits in
    both dtypes) is listed with its error and counted as missing for every
    arm of that model.
  - Missing items are reported per model. They are not imputed.
- **Images** are decoded in memory and never written to disk, outputs or the
  repository, as in every run so far.

## 2. Models

Every model cleared and readable at approval time, each at the revision of
its calibration run:

| model | revision | prompt (primary) | calibration source |
|---|---|---|---|
| Typhoon OCR 1.5 2B | `9c8a8fa1…` | `BENCHMARK_QUESTION` | T1 |
| Qwen3-VL-2B-Instruct (base) | `89644892…` | `BENCHMARK_QUESTION` | T1 |
| Qwen3-VL-4B-Instruct | `ebb281ec…` | `BENCHMARK_QUESTION` | M1 |
| PaddleOCR-VL-1.6 | `c5630aba…` | `OCR:` | M1 |
| Wayu | `af0204b4…` | `OCR:` | M1 |
| Pathumma Vision 3.0.0-Re | `08bb11dc…` | card prompt `อ่านข้อความในภาพนี้` | M5 |
| Qwen-SEA-LION-v4-4B-VL | `d0734aa1…` | `BENCHMARK_QUESTION` | M6a: readable (*proposed: include*) |
| InternVL3.5-2B (HF) | `3f301ffc…` | `BENCHMARK_QUESTION` | M6a: smoke degenerate in fp16 and fp32 alike; F1 15.8 / 6.7 (*proposed: exclude*, see below) |
| DeepSeek-OCR-2 | `aaa02f38…` | card `Free OCR.` (own runner, M6 Addendum 1) | M6b: fp16 only, fp32 unchecked on T4 (*proposed: include, with that caveat*) |

**"Readable"** means the model's calibration run produced Thai text on both
tasks, with the fp16 smoke clean. A model that fails this is listed and not
run. The decision is made at approval, from calibration only.

*Proposed* reading of the rule:

- **InternVL fails it.** Its smoke outputs loop from the start in both
  dtypes, and 53 of 69 Full-page outputs reach the limit. It would add about
  3 GPU-hours to measure a model far below every other.
- **DeepSeek-OCR-2 passes it.** It gives Thai text on both tasks, and fp16
  output is correct until a loop. But no fp32 comparison exists, and its
  runner differs from §3's (own venv, eager attention).

Both are for the two researchers to decide.

**Secondary prompt.** For Pathumma, `BENCHMARK_QUESTION` (as in M5), so that
it has a same-prompt comparison with Typhoon. No other model gets a second
prompt.

## 3. Protocol: T1's, frozen

The same values as T1, M1 and M5:

- T1's image policy (long side to 1800 px if either side exceeds 300 px),
  then the model's own processor;
- greedy decoding: `do_sample` false, `num_beams` 1, `repetition_penalty`
  1.0, `no_repeat_ngram_size` 0;
- `max_new_tokens` 3072 and `use_cache` true;
- fp16 with fp32 fallback only if the first item's logits are non-finite;
- `sdpa` attention;
- Kaggle 2×T4.

The code is the M1 runner (`model_survey.remote`) at the approval commit,
with the config's hash recorded.

## 4. Arms

Both arms come from the **same generation**. The stop is applied offline, as
in T5b, M2, W1 and M5.

- **greedy:** the output as generated.
- **greedy + stop:** `thai_marks.loop_cut.variant_b`, frozen as on `main` at
  approval:
  - an exact repeat run of 8 copies, or 6 for units of 50+ characters;
  - the first copy is kept and the rest of the output dropped.

  Its source hash goes in the registration. No parameter is tuned after
  approval.

Speculative decoding is not an arm (PELY334's separate speed claim, S1).

## 5. Metrics

- **Primary:** order-free v2 mark F1 (`order_free.mark_counts`,
  `max_cer` 0.4, residual true), with recall and precision.
- **Registered secondaries:**
  - the repeat-aware variant (`repeat_aware=True`, PR #85);
  - attribution on Full-page (`attribute_marks(..., approximate_reorder=True)`),
    read on the stopped outputs (W1's rule, because the anchored alignment
    is not valid on raw looping outputs);
  - T1 scoring v2 per cell.
- **Markup.**
  - Structure-aware extraction v2, as registered.
  - Raw outputs are audited for markup before any score is read.
  - Extraction has a known defect: a malformed, never-closed tag swallows
    the text after it (M5 §4; Up2mEz's review). If it is still unfixed at
    approval, the upper bound for affected outputs is reported beside the
    registered score. If it is fixed before approval, the fixed extraction is
    the registered one, and it is rerun on calibration first to show what
    changed.

## 6. Statistics

- **Paired bootstrap over pages.** One locked item is one image. To guard
  against two items sharing an image, the run records a hash of each decoded
  image (in memory; the image is not stored). Items with the same hash are
  resampled together as one cluster.
  - 10,000 resamples, seed 20261012.
  - Percentile 95% intervals.
- **Units.** Micro mark F1 over the resampled items (as in M1–M5),
  differences in points.
- **Multiplicity.** The confirmatory family is §7's tests. Holm's correction
  is applied across that family at α = 0.05 (one-sided where stated).
  Everything else is descriptive.

## 7. Confirmatory tests and readings, fixed in advance

**H-stop** (per model, both tasks):

| test | passes when | reading if it passes | reading if it fails |
|---|---|---|---|
| S1: Δ F1 (stop − greedy), all items | for every model that looped on ≥ 5% of calibration items in that task, the lower bound of the Holm-adjusted one-sided interval > 0 | the stop raises mark F1 on unseen items for models that loop | the gain does not replicate for that model, which is named |
| S2: ended outputs changed | the share of non-looping outputs the stop changes is ≤ 1% pooled over models, with the upper 95% bound reported | the stop leaves ended outputs alone | the stop has false cuts; the cases are read, and the claim is withdrawn as worded |

*Proposed for S2* (from M6): "ended" means "did not reach `max_new_tokens`",
as in W1. InternVL had 4 outputs that looped and then emitted
end-of-sequence before the limit, and the stop changed them. Under S2 as
written these count as changes. The approval revision either keeps that
definition, or counts as changes only outputs with no repeat run (the stop's
own rule). It must be fixed before the run.

**H-read** (per model, Full-page, stopped outputs):

| test | passes when | reading if it passes | reading if it fails |
|---|---|---|---|
| R1: not reading vs misreading | (whole line absent + span missing) ÷ (misread, base right) > 3, the lower bound of the 95% item-bootstrap interval of the ratio above 3 | marks are lost mainly by not reading, for that model | that model's loss is not mainly not-reading, and it is a named counter-example |

The claim is stated for the models that pass R1, not for "Thai OCR VLMs" in
general unless all pass. "Line absent" after a loop does not separate the
loop from failure to read (W1 §3). The paper says "not read", not "skipped".

**H-rank** (reported, not tested):

- Every model's F1, and its paired difference to Typhoon with a 95% interval.
- An interval that includes 0 reads "no difference shown at n = ⟨n⟩, width
  ±⟨w⟩", never "equivalent" (Up2mEz's M5 review).
- "Best" is used only if Typhoon's lower bound is above 0 against every
  model on both tasks.
- Contamination is stated next to every Typhoon and Pathumma number:
  Typhoon is from ThaiOCRBench's group, and Pathumma's 377K training samples
  are unnamed.

## 8. Budget and stopping

- **Estimate.** Calibration costs were 1.0–2.6 GPU-hours per model and
  prompt, on 178 items. The locked split is about 2.3 times larger, so
  roughly 2.5–6 GPU-hours per model and prompt. With 8 models (*proposed*: §2
  without InternVL) and one extra Pathumma prompt, about 30–45 GPU-hours.
- **This is more than one account's weekly Kaggle quota.** The draft splits
  the models between the two researchers' accounts, each run with the same
  code and config hash. ⟨assignment at approval⟩
- **Per-unit deadlines** as in M1: no item starts past the deadline, and
  items not run are listed. Deadlines are set from the calibration seconds per
  item × 2.3 × 1.5.
- **Smoke.** Each run has a `--smoke 2` on the first two **calibration**
  items, never locked ones. It must pass before the locked run is submitted.
- **One shot.**
  - No locked run is repeated to change a result.
  - A run that dies for engineering reasons is resumed for its missing items
    only. The resume and its reason are recorded, and nothing already scored
    is regenerated.

## 9. Who approves what

- **Both researchers:** this registration as a whole, the model list (§2),
  the extraction choice (§5), the account split (§8), and the Decision Log
  entry.
- **The paper's claims** follow §7's readings. New `CLAIMS.md` entries need
  Up2mEz's human approval as usual.

## 10. Not in scope

- Any remedy other than the stop (contrast, mark protection, re-reading).
- Sampling.
- Other benchmarks.
- Gate claims: W4 opens or passes no gate unless a separate Decision Log
  entry says so.
