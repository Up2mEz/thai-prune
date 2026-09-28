# REMEDIES_R1 — registration (Track B pilot)

**Status: `APPROVED`** under `docs/DECISION_LOG.md` entry 2026-09-28b (Track B
evaluation without waiting on T2, both researchers) and the pilot scope
pre-approved in
`collab/messages/20260928T0201Z_Up2mEz_to_PELY334_advance-permission-remedies-pilot.md`.
Written before any R1 output exists. Owner `PELY334`
(`docs/exec-plans/active/REMEDIES_PLAN.md`). Parameters:
`configs/remedies/r1.yaml`. Claim level of every result:
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

**Question.** Do VCD, an M3ID-form no-image contrast, or PAI-style attention
amplification change Thai mark errors relative to plain greedy (FULL) for
Qwen3-VL-2B and Typhoon OCR 1.5 — and what do they cost in other errors and in
latency? This is a **pilot**: it shakes out the mechanics and shows the size
and direction of effects at paper-default settings, to choose what a full
evaluation would test. It is not the Track-B-vs-T2 evaluation.

## 1. Fixed inputs

| | |
|---|---|
| models | `Qwen/Qwen3-VL-2B-Instruct@89644892e4d85e24eaac8bacfd4f463576704203`, `typhoon-ai/typhoon-ocr1.5-2b@9c8a8fa14905041d793f1e4e922312147956dcc0` |
| benchmark | `typhoon-ai/ThaiOCRBench@ca610d1ab330` (CC-BY-SA-4.0), Full-page OCR and Text recognition |
| items | T1's calibration split (`labbs2026.thai_marks.split`, seed 20260927, 30%); within it, per task, the **first 12 in hash order** `sha256("20260927:" + Id)` → 24 items (`labbs2026.remedies.design.pilot_ids`). Locked split never touched |
| prompt | `BENCHMARK_QUESTION` (the item's own question) — T1 scoring v2's primary prompt (PR #23); avoids the `TYPHOON_CARD` `<figure>` contract problem (`docs/stage0/OUTPUT_DIAGNOSTICS_NOTES.md` F1) |
| image policy | T1's (`typhoon_card` resize, then `smart_resize`) |
| precision | fp16; fp32 only if the first item's logits are non-finite; recorded per run |
| decoding | greedy, passed explicitly to every `generate()` because both checkpoints default to sampling: `do_sample=false`, `num_beams=1`, `repetition_penalty=1.0`, `no_repeat_ngram_size=0`, `max_new_tokens=3072`; the contrastive loop applies no logits processor, which matches these values |
| hardware | Kaggle 2×T4, one model per GPU |

## 2. Arms (paper-default settings; no tuning on data)

| arm | what | parameters |
|---|---|---|
| `FULL` | plain greedy | — |
| `VCD` | contrast with a noised copy of the same image (arXiv:2311.16922) | α = 1.0, β = 0.1, noise step 500 / 1000, linear β-schedule; per-item noise seed so both models see the same noised image |
| `M3ID` | contrast with the same prompt **without** the image, weight `(1 − e^{−λt}) / e^{−λt}` capped at 10 | λ = 0.02, β = 0.1 |
| `PAI` | `score + α·|score|` on image-token keys, decode-step queries, text layers ≥ 2 (arXiv:2407.21771, attention part only) | α = 0.5 |

Implementation: `labbs2026.remedies.contrastive`, `.pai`, `.remote`. The
formulas are this project's reading of the papers and have **not** been
checked line by line against the paper texts; the pilot measures these
implementations, and a full evaluation would first re-check them.

**Smoke-only controls** (never in the pilot): `PAI_ALPHA0` (PAI machinery at
α = 0, i.e. eager-math attention instead of `sdpa`) and `CD_ALPHA0` (the
contrastive loop at weight 0, β = 0). They measure what the machinery itself
changes relative to `FULL` in fp16 on T4. On CPU fp32 both reproduce `FULL`
exactly (`tests/test_remedies_remote.py`).

## 3. Recorded per item × arm

Raw output and token ids, generated tokens, whether `max_new_tokens` was
reached, seconds, prompt tokens; for contrastive arms the number of steps
where the chosen token differed from the real stream's argmax and the first
such step. Failures are recorded per arm and item; the run continues.

## 4. Metrics (all offline, identical for every arm)

1. **Per-item cause**, `labbs2026.output_diagnostics.taxonomy.diagnose`
   (thresholds fixed 2026-09-28): `format_loss`, `loop`, `omission`,
   `overgeneration`, `reading_order`, `misread`.
2. **CER**: T1's registered `normalize_text` CER (primary, for comparability);
   structural CER and structural-de-looped CER (sensitivity). Micro and macro.
   If T1 scoring v2 (PR #23) is merged before the analysis, its extraction is
   reported as a further sensitivity with its commit SHA; it does not replace
   the primary.
3. **Mark-specific error** per class (TONE, UPPER, LOWER): error of a mark whose
   base consonant was read correctly (`thai_marks.decompose.mark_decomposition`
   on structural-de-looped strings), computed **only on items whose `FULL`
   cause and arm cause are both `misread` or `reading_order`**. Items where
   either output loops, over-generates or omits are excluded from mark rates,
   because there almost every mark counts as deleted and the rate would measure
   the loop rate (`OUTPUT_DIAGNOSTICS_NOTES.md` F6). The number of items kept is
   reported per arm.
4. **Other errors**: consonant error rate on the same items; and the **cause
   transition table** FULL → arm over all items (e.g. how many `misread` items
   an arm turns into `loop`), because a remedy that trades mark errors for loops
   has not helped.
5. **Latency**: seconds per item and per generated token, ratio to FULL.

Each arm is compared with FULL **paired by item**: per-item differences, with an
item-level bootstrap 95% interval (10,000 resamples, seed 20260927, within
task). With 24 items the intervals are wide; no result is described as
significant, confirmed or a pass.

## 5. What a pilot result means, stated in advance

- An arm whose mark-specific error interval lies below FULL's on kept items,
  with no rise in consonant error and no net move of items into `loop` /
  `overgeneration` → worth a full evaluation at this and neighbouring settings.
- An arm that lowers mark error only by changing which items are kept, or that
  moves items into `loop`/`overgeneration` → not a mark fix; reported as such.
- No arm moves mark error → consistent with either evidence missing from the
  representation (T2's question) or settings that are wrong for OCR; the pilot
  cannot tell these apart and says so.
- Latency above ~2× FULL for VCD/M3ID is expected (two streams, a Python
  loop) and is reported, not optimised in the pilot.
- Base-vs-Typhoon differences are read within model only; Typhoon's scores are
  exposed to possible contamination (Decision Log 2026-09-27).

## 6. Budget and stopping

Cap: **6 T4-hours** for the pilot (Up2mEz's "a few T4-hours"). Before the
pilot is submitted, the smoke's seconds per item × arms (slower model) × 24
items gives the estimate; if it exceeds 6 hours, `items_per_task` is reduced
to the largest value that fits, decided from the smoke's timing before any
pilot output, and recorded. Nothing else may change without an addendum.

## 7. Not in scope

The locked split; any tuning of α, β, λ, noise step or layers; OCR-head sink
redistribution (deferred); PAI's logit-refinement half; `TYPHOON_CARD`; Fine-
grained and Handwritten tasks; any claim about VLMs beyond these two
checkpoints of one architecture family; any comparison with T2's oracle as if
final.
