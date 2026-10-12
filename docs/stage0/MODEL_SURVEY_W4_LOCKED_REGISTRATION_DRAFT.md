# MODEL_SURVEY W4 — confirmatory registration on the locked split

**Status: `APPROVED`** by both researchers: Up2mEz in DECISION_LOG
2026-10-12f (PR #117), PELY334 in 2026-10-13a (PR #119).

- This is the approval revision, written by PELY334's Claude Code session on
  2026-10-13 **before any locked output exists**.
- Every slot the draft left open is now fixed, with the values of Up2mEz's
  message
  `collab/messages/20261012T0730Z_Up2mEz_to_PELY334_w4-up2mez-side-decisions.md`.
- The conditions of 2026-10-12f are met in §11.
- The file keeps its `_DRAFT` name so that existing references stay valid.

The draft was written on 2026-10-12, as Up2mEz's work split asks (collab
`20261011T1315Z_Up2mEz_to_PELY334_paper-prep-work-split.md`, W4).

No locked item, image, reference or output was opened, counted or inspected
in writing the draft or this revision. Item counts below are derived from the
split's definition, not from the data. The only ⟨…⟩ left are filled by the
locked run itself.

## 0. Why confirm, and what

Every Thai-mark result so far is calibration-only and exploratory. Three
hypotheses in `docs/CLAIMS.md` ("HYPOTHESIS (needs more models and/or the
locked split)") are what the paper would assert. W4 tests the first two on
unseen items and reports the third.

| id | hypothesis (CLAIMS.md wording) | calibration evidence |
|---|---|---|
| **H-read** | Thai OCR VLMs lose marks mainly because the text is absent from the output (loops, text not found, lines not output) rather than by misreading marks; absence is observed, a failure to read is not | W1 (five models), M5 (Pathumma), M6 (SEA-LION, InternVL, DeepSeek-OCR-2): nine models, four families; T2 and W3 teacher-forced (Typhoon, base, Pathumma, Qwen3-VL-4B) |
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
| Qwen-SEA-LION-v4-4B-VL | `d0734aa1…` | `BENCHMARK_QUESTION` | M6a: readable, **included** |
| DeepSeek-OCR-2 | `aaa02f38…` | card `Free OCR.` (own runner, M6 Addendum 1) | M6b: **included**, fp16 only; the caveat is stated beside every DeepSeek number |
| ~~InternVL3.5-2B (HF)~~ | `3f301ffc…` | — | M6a: **excluded** (fails "readable") |

**"Readable"** means the model's calibration run produced Thai text on both
tasks, with the fp16 smoke clean. A model that fails this is listed and not
run. The decision is made at approval, from calibration only.

Decided (2026-10-12f, 2026-10-13a):

- **InternVL fails it.** Its smoke outputs loop from the start in both
  dtypes, and 53 of 69 Full-page outputs reach the limit. M6a's review also
  asks for a does-it-read-at-all control before it can count toward the
  claim. It is excluded, so eight models remain.
- **DeepSeek-OCR-2 passes it.** It gives Thai text on both tasks, and fp16
  output is correct until a loop. It is included, with this caveat beside
  every number:
  - no fp32 comparison exists, because fp32 does not fit a T4;
  - its runner differs from §3's (own venv, eager attention).

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

**Code.** At the code commit in §11, with each config's hash recorded:

- the M1 runner (`model_survey.remote`) for seven models;
- M6b's runner (`model_survey.remote_m6b`, own venv, eager attention) for
  DeepSeek.

The runners changed for W4 in two ways only, and neither touches generation:

- `run_on`, which selects the locked split;
- an `image_sha256` per record (§6).

The launcher refuses `run_on: locked` unless this file says `APPROVED`. A
`--smoke` always reads calibration items.

## 4. Arms

Both arms come from the **same generation**. The stop is applied offline, as
in T5b, M2, W1 and M5.

- **greedy:** the output as generated.
- **greedy + stop:** `thai_marks.loop_cut.variant_b`, frozen as on `main` at
  approval:
  - an exact repeat run of 8 copies, or 6 for units of 50+ characters;
  - the first copy is kept and the rest of the output dropped.

  Its source hash is in §11. No parameter is tuned after approval.
- **Decode-time stop** (Up2mEz's addition 1). `model_survey.stop` implements
  the same rule as a stopping criterion.
  - It is not an arm, and the locked run does not use it.
  - §11 reports whether it reproduces the offline cut on calibration. That
    decides whether the offline cut may be described as stopping at decode
    time.

Speculative decoding is not an arm (PELY334's separate speed claim, S1).

## 5. Metrics

- **Primary:** order-free v2 mark F1 (`order_free.mark_counts`,
  `max_cer` 0.4, residual true), with recall and precision.
- **Registered secondaries:**
  - the repeat-aware variant (`repeat_aware=True`, PR #85), **beside v2 in
    every cell** (Up2mEz's addition 2);
  - attribution on Full-page (`attribute_marks(..., approximate_reorder=True)`),
    read on the stopped outputs (W1's rule, because the anchored alignment
    is not valid on raw looping outputs);
  - T1 scoring v2 per cell.
- **Markup.**
  - Structure-aware extraction v2, as registered.
  - Raw outputs are audited for markup before any score is read.
  - Extraction has a known defect: a malformed, never-closed tag swallows
    the text after it (M5 §4; Up2mEz's review).
  - **Decided: extraction v2 stays primary, unchanged**, so that W4 stays
    comparable with every calibration number.
  - The upper bound is reported beside it: affected outputs credited as in
    M5's diagnostic.

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

**Decided for S2:** "ended" means "did not reach `max_new_tokens`", as in
W1.

- Reported beside it, not tested: the share of ended outputs that contain no
  repeat run.
- InternVL, the one model with loops that ended by end-of-sequence, is
  excluded.

**H-read** (per model, Full-page, stopped outputs):

| test | passes when | reading if it passes | reading if it fails |
|---|---|---|---|
| R1: absent vs misread | (whole line absent + span missing) ÷ (misread, base right) > 3, the lower bound of the 95% page-bootstrap interval of the ratio above 3 | marks are lost mainly because the text is absent from the output, for that model | that model's loss is not mainly absence, and it is a named counter-example |

The claim is stated for the models that pass R1, not for "Thai OCR VLMs" in
general unless all pass.

"Line absent" after a loop does not separate the loop from failure to read
(W1 §3). The paper says "absent from the output", and states that absence is
observed while a failure to read is not.

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
  roughly 2.5–6 GPU-hours per model and prompt. With 8 models (§2,
  without InternVL) and one extra Pathumma prompt, about 31 GPU-hours (table below).
- **Phases, accounts and caps** (2026-10-12f, 2026-10-13a). Phases are run
  in the order A, B, C, and a claim is made only for models whose phase
  finished. B and C may run while A runs.

  | phase | config | models | account | estimate (GPU-h) | cap (T4-h) |
  |---|---|---|---|---|---|
  | A | `configs/model_survey/w4a.yaml` | Typhoon, base, Wayu, Pathumma (card + `BENCHMARK_QUESTION`) | Up2mEz | 13.8 | 18 |
  | B | `configs/model_survey/w4b.yaml` | Qwen3-VL-4B, PaddleOCR-VL | PELY334 | 8.5 | 10 |
  | C | `configs/model_survey/w4c.yaml`, `w4c_deepseek.yaml` | SEA-LION-4B; DeepSeek-OCR-2 | PELY334 | 5.8; 3.2 | 9; 6 |

  - Total cap: **43 T4-hours** of the 45 that 2026-10-12f allows. A run above
    a cap needs a new approval from Up2mEz.
  - Estimates are each model's calibration generation hours (primary prompts)
    × 2.3.
  - Both accounts launch from commits that change no hashed file (§11).
  - If Up2mEz's account cannot take phase A, PELY334 runs it.
- **Per-unit deadlines** as in M1: no item starts past the deadline, and
  items not run are listed.
  - Each deadline is the calibration hours per shard × 2.3 × 1.5.
  - They are in the configs: for example, 1.6 h for a Typhoon shard and 4.6 h
    for a Qwen3-VL-4B shard.
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

## 11. Approval record (conditions of DECISION_LOG 2026-10-12f)

| condition | status |
|---|---|
| 1. PELY334's approval recorded | PR #117 approved and merged; entry 2026-10-13a (PR #119, merged by Up2mEz) |
| 2. Every slot filled, with code commit, config hashes and `variant_b` source hash | this revision, below |
| 3. Decode-time stop check on calibration reported | below, and `docs/stage0/data/W4_STOP_CHECK_ed02ad0.json` |
| 4. Cap stated | §8: 43 T4-hours (A 18, B 10, C 15) |
| 5. Calibration smoke before each run, no locked item in any smoke | §8; enforced by the launcher (a `--smoke` forces `run_on: calibration`) |

**Code commit:** `ed02ad0872b1aa9606d69afa408f93980798f2ef`.

- Runs launch from it, or from a descendant that changes no hashed file.
- Each run's `submission.json` records the hashes that the worker verifies.

**Config hashes (SHA-256, LF):**

| config | SHA-256 |
|---|---|
| `configs/model_survey/w4a.yaml` | `ecacbebc2f879e79c43615a32f14be60143434aa44b1e7e9e6752d3351aa3baa` |
| `configs/model_survey/w4b.yaml` | `8ff57308c8046dd957b8f3c7c3f71115e6a387fbb5d5a42c82788ffb981520e3` |
| `configs/model_survey/w4c.yaml` | `edb390381f16f79492c1b3965f38d77718abc57e67dac1b182c984f5587b4f04` |
| `configs/model_survey/w4c_deepseek.yaml` | `69d628f42c223f5b48fb1a597abc0901446b8f83378ed2ccd635eb1f0dfc5937` |

**The stop, frozen.** `src/labbs2026/thai_marks/loop_cut.py` SHA-256
`6a11e0b2bc7e0d9c4a9816a4303fd690610e61cac6463f41786d5158316d0b64`. Source
SHA-256 of each function:

- `variant_b`: `a469d2381ee8635d6c3fc16b6b0b8e18d08a9455f9dcca09306618a99d744995`
- `cut_at_loop`: `9c23bddc798fae897e16b5f4039d299b98d9dd2b8a97191abdbf28d478636c09`
- `loop_onset`: `ac50e2560db0a792a7d9efafdd6d6f3e584b519a98870b160f0e5c3c517d3c28`

**Scoring code, frozen.** Its hashes are taken now so that a later change is
visible:

- `thai_marks/order_free.py`: `0cde715b574da5664e285ed1f292ebcdc9fecc507516608d04774cdfdeb65841`
- `thai_marks/extract.py`: `265e754c0460ebe61fdd88a1884d6fb2fdcded43126c62c1f08ea3b8aa9767a7`

**Runners:**

- `model_survey/remote.py`: `4ae4d4da1ca0d3545a60469e6fbd5d8453ddf5036852f5d705d948eee6dcd5d0`
- `remote_m6b.py`: `0c6afadd0dd86e4c5b6f44d3e524f85f271d01505a24a99238bc472b7f964c35`
- `plan.py`: `5356be2a4617acc72e1b790cbc5aa39d34de5a2a030deeb4a68d287117e1df79`

**Decode-time stop check (condition 3).** Done on calibration with
`scripts/model_survey_w4_stop_check.py`, output
`docs/stage0/data/W4_STOP_CHECK_ed02ad0.json` (code commit `ed02ad0`, clean
tree). It ran on CPU; no GPU and no locked item.

How it works:

1. Each W4 model's archived calibration outputs (its W4 prompts) are encoded
   with the model's own tokenizer at its pinned revision.
2. Greedy decoding is replayed under the criterion: stop after the first
   token whose decoded prefix holds a run, then cut it.
3. The result is compared with `variant_b` on the full output.

| model · prompt | outputs | looping | stopped output = offline cut | criterion fired on a non-looping output |
|---|---|---|---|---|
| Typhoon · BQ | 178 | 2 | 2 / 2 | 0 |
| base · BQ | 178 | 46 | 46 / 46 | 0 |
| Wayu · `OCR:` | 178 | 20 | 20 / 20 | 0 |
| Pathumma · card | 178 | 7 | 7 / 7 | 0 |
| Pathumma · BQ | 178 | 3 | 3 / 3 | 0 |
| Qwen3-VL-4B · BQ | 178 | 27 | 27 / 27 | 0 |
| PaddleOCR-VL · `OCR:` | 178 | 22 | 22 / 22 | 0 |
| SEA-LION · BQ | 178 | 27 | 27 / 27 | 0 |
| DeepSeek-OCR-2 · card | 178 | 31 | 31 / 31 | 0 |

**Result.** Every looping output is reproduced character for character
(185 / 185), and the criterion never fires on an output the offline cut leaves
unchanged.

- One DeepSeek output, `B2EF6E79`, could not be replayed. Its grounding
  markup is special tokens that decoding drops, so the re-encoded ids do not
  decode back to the recorded text. The output does not loop and ended on its
  own.
- **Limit.** Outputs are stored as text, so the replay re-encodes them. The
  re-encoded ids are not necessarily the ids the model generated: every
  replayed output decodes back to its recorded text, but a different
  tokenization of the same text could fire the criterion at a different
  token.
- A live check would close this gap: generating with the criterion attached
  on calibration items, which needs a GPU. It is not part of condition 3 as
  asked, and can be added on request.

**Reading.** On calibration, the offline cut is what a decode-time stop with
the same rule produces, for all eight W4 models. W4's arms stay as registered:
the offline cut on the same generation.
