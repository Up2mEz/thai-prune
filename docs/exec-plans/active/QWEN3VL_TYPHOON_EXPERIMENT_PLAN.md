# Experiment plan — Qwen3-VL-2B / Typhoon OCR 1.5 on ThaiOCRBench

**Status: `PLAN_PENDING_HUMAN_REVIEW`.** Authorizes nothing. Each phase ends at a
human decision recorded in `docs/DECISION_LOG.md`; no phase starts before the
previous one's decision is recorded.

## 0. What is being asked

From `docs/RESEARCH_SPEC.md`:

| id | question | status before this plan |
|---|---|---|
| **RQ1** (active primary) | Does change in exact transcription across actual visual-token budgets differ between a BASE OCR VLM and its Thai-specialized descendant? Non-directional, `MODEL x BUDGET`. | Null for Paddle/Wayu on synthetic pairs, Resolution Reduction only (Wald 5.01, df 3, p = 0.17). Never tested on a pair where budgets discard real pixels. |
| H1 (descriptive) | Component types may degrade differently with budget. | Descriptive only. |
| H2 | Component effects may be explained by properties of the visual evidence. | Untested. Round-3 diagnostic found tone marks fail on correctly read consonants at 3–4× the vowel rate, flat across compression. |
| H3 | Resolution Reduction and post-encoder reduction may differ. | Paddle only, confounded by magnification on TEMS. |
| H4 | Existing OCR-aware compression may not preserve distinction-critical evidence. | Untested. |

Why this pair answers RQ1 better than Paddle/Wayu: identical architecture and
processor, so both models receive **byte-identical visual-token budgets** for
every item; the only varying factor is the weights.

## 1. Fixed inputs

- Models: `Qwen/Qwen3-VL-2B-Instruct@89644892e4d8…`,
  `typhoon-ai/typhoon-ocr1.5-2b@9c8a8fa14905…` — pinned SHAs only.
- Benchmark: `typhoon-ai/ThaiOCRBench@ca610d1ab330`, CC-BY-SA-4.0.
- Tasks: Full-page OCR (197) and Text recognition (333) primary;
  Fine-grained text recognition (206) secondary.

## 2. Split — decided before any output exists

Seeded item-level split, stratified by task × category:

- **calibration (≈30%)** — every design decision: prompt, normalization,
  budget grid, validity thresholds, stratum boundaries.
- **locked (≈70%)** — opened once, for the registered confirmatory run.

Reason: round 3 chose `RR_50` on the same regions it scored, which made the
improvement optimistic by selection. ThaiOCRBench has no held-out split of its
own, so one is made before looking.

## 3. Phases

### Phase A — Instrument (no inference)

Why: rounds 1–3 lost time to an instrument that was not ready. Each item here
answers a failure already paid for.

1. Qwen3-VL adapter: processor contract preflight (factor 32, floor 65,536,
   ceiling); placeholder accounting; **DeepStack accounting** (three extra
   streams added at visual positions of LLM layers 0–2); path equivalence
   checked on a sample, not on one item.
2. Output normalization, frozen: Markdown/HTML to plain text, the ` | `
   block separator, whitespace and line breaks. Unit-tested.
3. Metrics, unit-tested: CER macro/micro; the component decomposition with
   the base-conditioned mark-specific error of `THAI_MARK_FAILURE_MODES.md`
   §7; truncation and repetition rates; the benchmark's BMFL as secondary for
   comparability with the published table.
4. Stage-resolved cost (`cost.py`), reused.
5. Exact per-item scale count: native area against the processed grid, to
   define the stratum where reduced budgets genuinely discard pixels.
6. **fp16 stability check.** T4 has no native bf16 and Qwen models can
   overflow in fp16. A fallback to fp32 must be decided on the calibration
   split, not discovered mid-run.

### Phase B — Stage 0 on the new backbone: FULL validity

Why first: one new factor at a time. Nothing compressed is interpretable until
both models read the tasks at FULL.

- 2 models × 2 prompts (Typhoon's card prompt; the benchmark's own) × FULL,
  calibration split. Fine-grained items run twice: whole image with the box,
  and an oracle crop of the box.
- Measured: CER, BMFL, component decomposition, truncation, repetition loops,
  stage costs.
- **Decided afterwards, by the human:** which prompt is pinned; FULL-validity
  thresholds frozen for the locked run; whether fp16 holds.

### Phase C — RQ1: `MODEL x BUDGET`, Input Resolution Reduction

Why: this is the registered primary question, and this pair is the first on
which it can be asked with budgets that discard source pixels.

- Budgets: FULL and forced pixel budgets at 75 / 50 / 25% of FULL's tokens.
  Identical per item for both models by construction.
- Primary population: items where the 25% budget discards source pixels.
- Estimand: per-item ΔCER against FULL, and its difference between models at
  each budget; cluster bootstrap by item, category as stratum, Holm across
  budgets. Component curves (H1) descriptive.
- Run on the calibration split first to validate the pipeline; the locked split
  is opened once the human approves.

### Phase D — H3: post-encoder reduction, DeepStack-aware

Why after C: it needs pruning re-implemented for DeepStack, and it is only
interpretable next to C's Resolution Reduction arm.

- Grid pruning matched per item to the tokens Resolution Reduction achieved.
  Removing a visual position removes it from the main stream and all three
  DeepStack streams at once; accounting asserts it.
- Includes the restored-detail control from round 3 so detail and magnification
  can be separated again.
- Efficiency re-measured: pages carry ~2,240 visual tokens, so prefill may now
  be a real share of cost — the crop-scale conclusion is not assumed.

### Phase E — H2 / mechanism, training-free

Why: the round-3 diagnostic says tone marks fail independently of compression.
These probes ask why, at FULL, without training.

1. **DeepStack ablation** — zero each of the taps from vision layers 5, 11, 17,
   and all three; per-component effect.
2. **Patch-phase shift** — translate pages 0–15 px vertically; does tone-mark
   error oscillate with the 16-px grid while consonant error does not.
3. **Oracle crop** (Fine-grained) — finding versus reading.
4. **Base/Typhoon** — per-module weight delta; component swaps.
5. **Readout** — probability margin between toned and untoned candidates.

E1–E3 are registered secondary families; E4–E5 exploratory.

### Phase F — H4, gated

Existing OCR-aware methods (ET-Prune, FastOCR) only if compatible with this
architecture and only after a human-approved Gate 3.

## 4. Gate mapping

| phase | gate in `RESEARCH_SPEC.md` §7 |
|---|---|
| B | Stage 0 measurement validity, new backbone |
| C | Gate 1 — overall differential degradation |
| E1, E2 | Gate 2 — visual-size and major confounds |
| D | Gate 3 — intervention families |
| F | Gate 4 — existing methods |

## 5. Cost estimate, to be replaced by Phase B measurement

Full-page OCR references are p50 1,345 characters, about 770 output tokens at
0.57 tokens per character. With a 28-layer decoder at batch 1 on a T4, that is
on the order of 20 s per page, so decode dominates. Rough totals:

- Phase B: 2 models × 2 prompts × ~160 calibration items — a few GPU hours.
- Phase C locked: 2 models × 4 budgets × ~370 items — roughly 8–12 GPU hours.

Kaggle's 30 h/week covers A–C in about one week; D and E follow. These are
estimates, not measurements.

## 6. What the plan will not claim

No confirmatory claim from the calibration split. No generalization beyond one
architecture family. No statement that tone marks degrade *faster* — the
round-3 evidence is of a higher baseline, not a steeper curve. Typhoon's
absolute scores carry the contamination caveat recorded 2026-09-27.
