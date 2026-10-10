# MODEL_SURVEY_M1 — results (Track E)

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** Calibration split only,
one run. **Authorized by PELY334; Up2mEz's review was pending when these
results were produced** (PR #63; Decision Log 2026-10-10 not merged).
Registration: `MODEL_SURVEY_M1_REGISTRATION.md` (with Addendum 1).

| | |
|---|---|
| run | `kaggle-model-survey-m1-3431d9f9dccf` (git `3431d9f`), Kaggle 2×T4, fp16 for every model, torch `2.14.0+cu130`, transformers `5.12.0`, `use_cache` true |
| units | Qwen3-VL-4B 89 + 89 items (1.33 h, 1.35 h), Paddle 178 (2.43 h), Wayu 178 (2.53 h); 0 failures; no deadline bound (`not_run` empty) |
| session time | ≈ 4.1 h (GPU 0: 3.8 h, GPU 1: 3.9 h, plus setup), within the 8 T4-hour cap |
| scores | `docs/stage0/data/M1_SCORES_3431d9f9dccf.json` (`scripts/model_survey_analyze.py`, git `3431d9f`, clean) |
| outputs | `docs/stage0/data/M1_OUTPUTS_3431d9f9dccf.json.gz`: no reference text, no image (T1's archive format) |
| exploratory | `docs/stage0/data/M1_EXPLORATORY_3431d9f9dccf.json` (`scripts/model_survey_exploratory.py`, git `e27f2cb`, clean) |

## 1. Registered check (§3): passed

Scored by the same code against this run's references, T1's archived
`BENCHMARK_QUESTION` outputs reproduce `ORDER_FREE_MARK_METRIC_DRAFT.md` §7
exactly:

- order-free F1: Typhoon 94.9 (Full-page) and 81.7 (Text recognition); base
  41.0 and 24.3;
- T1's headline: Typhoon median CER 2.8%, tone error 0.65%, truncation 2.9%;
  base 27.1%, 43.5%.

The comparison is therefore reported.

## 2. Primary outcome (§4)

Order-free v2 mark F1 (recall, precision) and T1 scoring v2. Each model is
shown with its primary prompt; Paddle and Wayu also with
`BENCHMARK_QUESTION` (secondary). Percentages.

### Full-page OCR (69 items) — off-design for Paddle and Wayu (§2)

| model | prompt | mark F1 | recall | precision | median CER | located | tone error¹ | truncated | repetitive | s/token |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Typhoon OCR 1.5 (T1) | BQ | **94.9** | 96.1 | 93.7 | 2.8 | 100 | 0.65 | 2.9 | 1.4 | 0.042 |
| base Qwen3-VL-2B (T1) | BQ | 41.0 | 65.0 | 29.9 | 27.1 | 91 | 9.41 | 43.5 | 36.2 | 0.041 |
| **Qwen3-VL-4B** | BQ | 45.9 | 69.3 | 34.4 | 18.1 | 97 | 9.89 | 27.5 | 24.6 | 0.058 |
| **PaddleOCR-VL-1.6** | `OCR:` | 53.3 | 46.6 | 62.2 | 28.4 | 74 | 14.57 | 39.1 | 37.7 | 0.021 |
| **wayu-paxa-ocr-zero** | `OCR:` | 65.2 | 69.0 | 61.8 | 13.0 | 86 | 5.27 | 26.1 | 24.6 | 0.021 |
| PaddleOCR-VL-1.6 | BQ | 33.1 | 35.5 | 30.9 | 100.0 | 43 | 18.10 | 53.6 | 49.3 | 0.021 |
| wayu-paxa-ocr-zero | BQ | 50.4 | 61.1 | 42.9 | 27.3 | 78 | 5.07 | 42.0 | 42.0 | 0.020 |

### Text recognition (109 items)

| model | prompt | mark F1 | recall | precision | median CER | located | tone error¹ | truncated | repetitive | s/token |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Typhoon OCR 1.5 (T1) | BQ | **81.7** | 82.9 | 80.6 | 5.0 | 91 | 0.60 | 0.9 | 0.9 | 0.065 |
| base Qwen3-VL-2B (T1) | BQ | 24.3 | 83.6 | 14.2 | 24.1 | 87 | 4.91 | 14.7 | 16.5 | 0.057 |
| **Qwen3-VL-4B** | BQ | 23.5 | 84.3 | 13.6 | 20.0 | 95 | 4.38 | 11.9 | 5.5 | 0.061 |
| **PaddleOCR-VL-1.6** | `OCR:` | 47.9 | 67.3 | 37.1 | 25.0 | 74 | 14.55 | 14.7 | 15.6 | 0.025 |
| **wayu-paxa-ocr-zero** | `OCR:` | 46.0 | 83.8 | 31.7 | 8.5 | 83 | 2.63 | 20.2 | 20.2 | 0.024 |
| PaddleOCR-VL-1.6 | BQ | 24.1 | 70.1 | 14.6 | 67.3 | 53 | 11.52 | 23.9 | 21.1 | 0.024 |
| wayu-paxa-ocr-zero | BQ | 20.9 | 80.0 | 12.0 | 12.5 | 72 | 2.39 | 39.4 | 38.5 | 0.022 |

¹ Tone-mark error given a correctly read base consonant (T1's
mark-specific error). BQ = `BENCHMARK_QUESTION`.

### Paired mark F1 difference to Typhoon and to the base (points, 95% item bootstrap)

| new model (primary prompt) | task | − Typhoon | − base |
|---|---|---|---|
| Qwen3-VL-4B | Full-page | −48.9 [−56.6, −39.8] | **+5.0 [−4.0, +14.1]** |
| Qwen3-VL-4B | Text recognition | −58.2 [−68.4, −45.2] | −0.8 [−11.4, +7.4] |
| PaddleOCR-VL-1.6 | Full-page | −41.6 [−51.2, −32.4] | +12.3 [+2.6, +21.7] |
| PaddleOCR-VL-1.6 | Text recognition | −33.9 [−50.0, −14.2] | +23.6 [+7.3, +41.8] |
| wayu-paxa-ocr-zero | Full-page | −29.6 [−39.9, −19.2] | +24.3 [+12.5, +35.8] |
| wayu-paxa-ocr-zero | Text recognition | −35.7 [−49.7, −18.8] | +21.7 [+7.0, +36.8] |

## 3. Reading against the registered patterns (§5)

- **Qwen3-VL-4B on Full-page: near the base.** The registered row reads "size
  alone does not close the gap; Thai OCR training is what carries marks".
  - Mark F1 rises 41.0 → 45.9, an interval of +5.0 that includes 0, and the
    tone error is unchanged (9.9% vs 9.4%).
  - Twice the size does reduce loops (truncated 43.5% → 27.5%) and lowers the
    median CER (27.1% → 18.1%). It is 1.4× slower per token.
- **Wayu vs Paddle on Text recognition: near, by the registered F1** (46.0 vs
  47.9). The exploratory pairs in §4 show the tie hides two opposite effects:
  - Wayu finds more of the reference marks (recall +16.5 [+1.1, +29.9]), with a
    far lower tone error (2.6% vs 14.6%).
  - Its precision is lower, from loops (20% of outputs hit the limit) and from
    transcribing whole images.
  - On Full-page, Wayu is above Paddle: +11.9 [−0.2, +25.2].
- **"Paddle or Wayu near Typhoon on Text recognition, far below on Full-page"
  does not hold** on the registered F1: both are 34–36 points below Typhoon on
  Text recognition too. It does hold, exploratorily, on the subset where Wayu
  answers the text alone (§4).
- **No new model is above Typhoon** on any cell. Every interval against Typhoon
  excludes 0 by at least 14 points. The registered follow-up condition (a new
  model above Typhoon on Text recognition marks) is not met.

**In one sentence:** under T1's protocol, Typhoon OCR 1.5 remains clearly the
best of five checkpoints on Thai marks, and doubling the base's size does not
close its gap. The Thai synthetic fine-tune (Wayu) is the best of the three
new models but loses most of what it reads to repetition loops.

## 4. Exploratory readings (not registered; `M1_EXPLORATORY_3431d9f9dccf.json`)

**Loops versus reading.** These pairs use only the items on which neither the
model nor Typhoon reached `max_new_tokens`. Typhoon still reads Full-page marks
10–16 points better:

| vs Typhoon, no loop on either side | n | Typhoon F1 | model F1 | Δ F1 |
|---|---:|---:|---:|---|
| Qwen3-VL-4B · Full-page | 49 | 97.9 | 82.8 | −15.0 [−20.0, −11.1] |
| Paddle · Full-page | 41 | 98.7 | 82.3 | −16.4 [−20.2, −12.7] |
| Wayu · Full-page | 51 | 98.2 | 88.1 | −10.0 [−16.0, −4.7] |
| base · Full-page | 38 | 99.1 | 84.6 | −14.5 [−20.4, −10.3] |

**Answering versus transcribing (Text recognition).** Some items show a whole
page or poster, and the question asks for one part. The reference is that part
only.

- `OCR:` carries no question, so Paddle and Wayu transcribe everything.
  - On such an item Wayu printed 926 characters for a 10-character reference.
  - The target's marks are then present (recall up), but the surplus is
    charged (precision down).
- Typhoon answers the question, but sometimes **from the wrong place**. On one
  item it answered with another option of the same exam question. This is the
  finding failure Track C reported (`FIND_VS_READ_F1_RESULTS.md`).

Splitting the non-looping items by how much text the model produced
(≤ 1.5 × the reference length vs more):

| Text recognition, no loop | n | Typhoon F1 (R/P) | model F1 (R/P) | Δ F1 | Δ recall |
|---|---:|---:|---:|---|---|
| **Wayu · reads about the reference** | 59 | 94.5 (94.0/94.9) | **94.9** (95.3/94.4) | **+0.4 [−1.6, +3.0]** | +1.3 [−1.1, +4.5] |
| Wayu · reads much more | 27 | 58.6 (60.8/56.6) | 37.6 (92.8/23.6) | −21.1 [−43.4, +4.0] | +32.0 [+11.8, +52.2] |
| Paddle · reads about the reference | 65 | 89.9 (87.4/92.5) | 86.2 (81.0/92.0) | −3.7 [−10.8, +6.7] | −6.4 [−19.0, +10.2] |
| Paddle · reads much more | 27 | 64.9 (65.2/64.5) | 34.2 (77.4/21.9) | −30.7 [−50.6, −6.2] | +12.2 [−9.4, +33.1] |

On the 59 items where Wayu answers with about the reference alone and does not
loop, a 0.9B model trained on synthetic pages only reads Thai marks **as well
as Typhoon** (F1 94.9 vs 94.5). Two limits on this:

- The split conditions on Wayu's own output, so these are items on which it
  behaved well; it is hypothesis-generating, not a test.
- Wayu's higher recall on the "reads much more" items comes from transcribing
  everything. It is not better reading.

## 5. Output-format audit (before any number above was read)

- **HTML tags.** None in any output of the three models. The only tag-like
  strings are:
  - `<Jonetz>`, printed in one image and present in its reference;
  - `GLYPH<SM59…>` placeholders in 3 of Wayu's items. These look like a
    PDF-extraction artefact, presumably from its synthetic training pages
    (an inference).
- **Markdown.**
  - Qwen3-VL-4B answers Text recognition questions conversationally: a
    preamble ("ข้อความในภาพเขียนว่า: …"), the text in `**bold**` (101 of 109
    outputs), and sometimes translations or a description.
  - `extract_text` removes bold, headings and fences before scoring (checked
    directly). The preamble and translations stay, and are charged as surplus
    by the order-free metric: precision 13.6%, recall 84.3%. The base was
    scored the same way in T1 (precision 14.2%).
- **Repetition flags** computed on raw and on structure-normalized text are
  identical in every cell, so markup does not change the loop rates (cf. the
  S1 markup check).

## 6. Limits

- **Up2mEz review pending** at the time of writing; one run; calibration split
  only; `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.
- **Visual tokens.** Each model's own processor caps them: Qwen3-VL family
  median 2,240 (Full-page) / 2,352 (Text recognition); Paddle and Wayu
  1,240–1,280. The comparison is between models as shipped, not at an equal
  visual-token budget.
- **Decoding.** T1's greedy decoding with `repetition_penalty=1.0` is kept;
  Wayu's card recommends sampling with 1.05. Part of Wayu's loop rate (26%
  Full-page, 20% Text recognition) may be this choice; not tested here.
- **Paddle and Wayu on Full-page are off-design** (no layout detector), as
  registered. `BENCHMARK_QUESTION` is not a prompt either was trained on.
- **Contamination.** Typhoon comes from ThaiOCRBench's group; Qwen3-VL's and
  PaddleOCR-VL's training data are unknown in this respect; Wayu's card claims
  synthetic data only.
- Two model families. No claim beyond these five checkpoints.

## 7. What this suggests (proposals only; none is authorized)

1. **Wayu with its own decoding, or with T5b's loop stop.** This would show how
   much of its deficit is loops. That is cheap: 0.9B, 0.021 s/token, half of
   Typhoon's per-token time on T4.
2. **Wayu as a re-reader of single lines.** E1 found that Typhoon's confidence
   locates its mark errors, and E3 failed on cost. If a registered test
   confirms on held-out items that Wayu reads isolated text as well as
   Typhoon, it is a candidate re-reader for flagged lines. Any such test needs
   a new registration reviewed by Up2mEz before it runs.
3. **Larger checkpoints are not reachable at fp16 on one T4.** Qwen3-VL-8B
   needs about 16.5 GB. Typhoon OCR 7B would need the terms audit its
   1.5-2B revision had.
