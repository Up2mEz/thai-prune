# MODEL_SURVEY_M1 — registration (Track E: models not yet run on ThaiOCRBench)

**Status: `APPROVED` by PELY334 only.** PELY334 authorized the run in session on
2026-10-10 and chose to run before Up2mEz's review ("รันเลย, Up2mEz ตรวจทีหลัง").
**Up2mEz's review is pending**: the Decision Log entry 2026-10-10 is in this
track's PR and is not merged until Up2mEz approves (`docs/COLLABORATION.md` §3).
Written before any M1 output on ThaiOCRBench exists; the only outputs so far are
local engineering checks on a synthetic image (§8). Plan:
`docs/exec-plans/active/MODEL_SURVEY_PLAN.md`. Parameters:
`configs/model_survey/m1.yaml`. Claim level of every result:
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

**Question.** Measured with T1's protocol unchanged, how do three checkpoints
not yet run in this repository read Thai marks, next to Typhoon OCR 1.5 and the
base on the same items?

- **(a) `Qwen/Qwen3-VL-4B-Instruct`** — the base's family at twice its size.
  Does size alone close the base's gap (T1 full-page order-free mark F1: base
  41.0, Typhoon 94.9)?
- **(b) `PaddlePaddle/PaddleOCR-VL-1.6`** (0.9B) — a multilingual document-OCR
  specialist, not trained for Thai in particular.
- **(c) `wayu-ai/wayu-paxa-ocr-zero`** (0.9B) — a full fine-tune of (b) for Thai
  on 45,723 synthetic pages built from public English document collections,
  with no OCR label from a real Thai document (its model card). Thai
  specialization without real Thai data.

Primary comparison: each new model against Typhoon on the same items.

## 1. Fixed inputs (T1's unless stated)

| | |
|---|---|
| models | `Qwen/Qwen3-VL-4B-Instruct@ebb281ec70b05090aa6165b016eac8ec08e71b17`, `PaddlePaddle/PaddleOCR-VL-1.6@c5630abae1d940eafe0697512a0325494b02ab42`, `wayu-ai/wayu-paxa-ocr-zero@af0204b4f334a6d5068b6bac2b3738932d6e289b`; the last two are the revisions already pinned in `configs/stage0/overall_model_budget_design.yaml` |
| licence | all three Apache-2.0 and ungated (Hugging Face API, 2026-10-10) |
| items | T1's **178** calibration items (69 Full-page OCR, 109 Text recognition; seed 20260927, stratified by Task × category), `Id` order; the locked split is never touched |
| image | T1's `typhoon_card` policy (long side to 1800 px if either side > 300 px), then each model's own processor; images stay in memory, never written |
| prompts | Qwen3-VL-4B: `BENCHMARK_QUESTION` (the item's question) only. Paddle and Wayu: `OCR_NATIVE` = `OCR:` (their documented recognition prompt) **and** `BENCHMARK_QUESTION` |
| primary prompt | Qwen3-VL-4B: `BENCHMARK_QUESTION` (T1's registered primary for both tasks). Paddle, Wayu: `OCR_NATIVE` |
| decoding | T1's, explicit: `do_sample=false`, `num_beams=1`, `repetition_penalty=1.0`, `no_repeat_ngram_size=0`, `max_new_tokens=3072`; plus `use_cache=true` (§8) |
| precision | fp16, `sdpa`; fp32 only if the first item's logits are non-finite; recorded |
| hardware | one Kaggle session, 2×T4: GPU 0 runs Qwen3-VL-4B shard 0 then Paddle; GPU 1 runs Qwen3-VL-4B shard 1 then Wayu (interleaved shards) |

Why only `BENCHMARK_QUESTION` for Qwen3-VL-4B: `TYPHOON_CARD` is Typhoon's own
card prompt, whose format contract the base did not follow in T1, and most of
the base's T1 cost was `TYPHOON_CARD` output that looped to the token limit
(3.3 of 5.3 GPU-hours). Why `BENCHMARK_QUESTION` also for Paddle and Wayu: so
that T1's primary condition exists for every model.

## 2. Design limits, stated in advance

- **Paddle and Wayu are region recognizers.** Their cards run them after a
  layout detector (PP-DocLayoutV3). T1 gives every model the whole page, and
  so does M1: their **Full-page cells measure them off-design**; their **Text
  recognition cells are in-design**. No layout pipeline is added, because it
  would compare a pipeline with single models.
- Wayu's card suggests sampling (`temperature=0.1`, `top_p=0.7`,
  `repetition_penalty=1.05`); T1's greedy decoding is kept for every model.
- **Contamination.** Typhoon comes from the group that made ThaiOCRBench (noted
  since T1). The training data of Qwen3-VL and PaddleOCR-VL are not published
  in enough detail to rule out overlap. Wayu's card states synthetic training
  data only.
- One run; greedy decoding is deterministic up to fp16 kernel ties (S1).
- No result is generalized beyond these checkpoints: two families
  (Qwen3-VL; PaddleOCR-VL with its fine-tune).

## 3. Scoring (offline; existing code only)

- **T1 scoring v2** (`thai_marks.analysis.analyze_t1_v2`, null seed 20260928):
  per cell (task × prompt, never pooled) the chance-calibrated anchored CER and
  located rate, tone error given a correct consonant, truncation and
  repetition rates, median seconds per token.
- **Order-free v2 mark precision/recall/F1** (`thai_marks.order_free.mark_counts`
  with `max_cer=0.4, residual=True`, micro over items) — the reported mark
  metric (Decision Log 2026-10-03).
- **Base and Typhoon** are scored by the same functions on their archived T1
  outputs (`docs/stage0/data/T1_OUTPUTS_a44199c29759.json.gz`,
  `BENCHMARK_QUESTION`), against this run's references for the same item ids.
  **Check:** the order-free F1 of `BENCHMARK_QUESTION` must reproduce
  `ORDER_FREE_MARK_METRIC_DRAFT.md` §7 — Typhoon 94.9 (Full-page) and 81.7
  (Text recognition), base 41.0 and 24.3; if not, no comparison is reported
  until the difference is explained.

Code: `src/labbs2026/model_survey/` (`plan.py`, `remote.py`, `analysis.py`),
`scripts/model_survey_kaggle.py`, `scripts/model_survey_analyze.py`,
`infra/kaggle/model_survey_worker.py`; tests `tests/test_model_survey.py`
(including that every condition in §1 equals T1's config).

## 4. Primary outcome

For each new model's primary prompt and each task: order-free v2 mark F1 (with
recall and precision), and its **paired difference to Typhoon**
(`BENCHMARK_QUESTION`) on the same items, with a 95% item-bootstrap interval
(2,000 resamples, seed 20261010). Descriptive: no decision rule on the interval.

Secondary: the same difference to the base; anchored median CER, located rate,
tone error given a correct consonant, truncation and repetition rates, seconds
per token, visual tokens; each new model's secondary prompt.

## 5. What each pattern would mean, stated in advance

| pattern | reading |
|---|---|
| Qwen3-VL-4B full-page mark F1 near the base's 41 | size alone does not close the gap; Thai OCR training is what carries marks |
| Qwen3-VL-4B clearly above the base, clearly below Typhoon | size explains part of the gap |
| Qwen3-VL-4B near or above Typhoon | a general model twice the base's size reads marks like the Thai specialist; Typhoon's edge is size-equivalent here |
| Wayu clearly above Paddle on Text recognition marks | Thai synthetic fine-tuning helps marks without real Thai labels |
| Wayu near Paddle | the fine-tune adds nothing measurable on marks here |
| Paddle or Wayu near Typhoon on Text recognition, far below on Full-page | they read glyphs but not pages off-design (layout, length, loops) |
| a new model above Typhoon on Text recognition marks, interval excluding 0 | worth a registered follow-up, e.g. as a re-reader of the lines Typhoon's confidence flags (E1/E3) |

"Near", "clearly" and "above" are read on the point estimates and the paired
intervals and reported with them; nothing here is a gate.

## 6. Budget, smoke, stopping

Smoke first: `--smoke 2` (the first two calibration items for every model; one
per Qwen3-VL-4B shard), checked for dtype, failures, output format, the
recorded `use_cache`, seconds per token, peak memory and the absence of images
in the outputs. Estimate: the base took 2.1 GPU-hours for `BENCHMARK_QUESTION`
in T1; Qwen3-VL-4B at about twice the cost per token is ~4 GPU-hours, ~2 hours
on two shards; Paddle and Wayu ran at 0.05–0.06 s/token in the local check
(§8), well under 1.5 hours each for two prompts unless they loop. **Cap: 8
T4-hours of session time, PELY334's own Kaggle quota.** If the smoke implies
more, Qwen3-VL-4B's Text recognition cell is dropped first — decided and
recorded before the full run.

## 7. Not in scope

Reruns of Typhoon or the base; `TYPHOON_CARD` for the new models; layout
pipelines; sampling; other ThaiOCRBench tasks; the locked split; any remedy;
claims beyond these checkpoints.

## 8. Engineering checks before this registration was frozen (synthetic image; not results)

Local RTX 3060 6 GB, `transformers 5.12.0` (as `uv.lock`), torch 2.11+cu128, a
rendered two- and three-line Thai image (Tahoma), never ThaiOCRBench:

- Paddle and Wayu load in fp16 through `thai_marks.runtime`, logits are
  finite, the resolved decoding is greedy, both prompts generate; peak 1.96 GB.
- **PaddleOCR-VL-1.6's `generation_config.json` sets `use_cache: false`**
  (Wayu's sets `true`). Paddle with and without the cache gave the **identical**
  output (88 tokens) at 0.94 vs 0.061 s/token. Caching does not change what
  greedy decoding selects, so `use_cache=true` is passed to every model, the
  condition under which T1's two models decoded; it is recorded per run.
- Qwen3-VL-4B (8.9 GB in fp16) does not fit the local GPU; it is the
  architecture of the base, which T1 already ran in this runtime.
