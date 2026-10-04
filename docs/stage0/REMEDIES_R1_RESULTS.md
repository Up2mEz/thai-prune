# REMEDIES_R1 — results (Track B pilot)

**Arm names.** `VCD`, `M3ID` and `PAI` below are this project's implementations
(`M3ID-form`, `PAI-style`), not checked line by line against the papers
(registration §2); every claim about them is about these implementations.

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** 24 calibration items
(12 per task), paper-default settings, no tuning. Registration:
`docs/stage0/REMEDIES_R1_REGISTRATION.md`. Authorization: `docs/DECISION_LOG.md`
2026-09-28b.

| | |
|---|---|
| run | `kaggle-remedies-r1-014755d599c8`, commit `014755d`, 2×T4, fp16 both models |
| smoke | `kaggle-remedies-r1-92796af7ef92-smoke1`: zero-strength controls reproduced FULL token for token on T4 fp16 |
| failures | 0 of 192 item × arm × model generations |
| checksums | verified; analysis `scripts/remedies_analyze.py` (registered §4), commit of this document |

## 1. What FULL itself does on these 24 items

| model | misread | reading_order | loop | overgeneration | omission |
|---|---|---|---|---|---|
| base | 11 | 2 | **7** | **4** | 0 |
| typhoon | 19 | 1 | 1 | 2 | 1 |

With `BENCHMARK_QUESTION`, 11 of 24 base outputs loop or over-generate; these
dominate its CER (micro CER 1.12 under T1's normalization). Typhoon mostly
reads (micro CER 0.28).

## 2. Results per arm (arm − FULL, paired by item, 95% bootstrap interval)

### Base (Qwen3-VL-2B)

| arm | cause transitions (FULL → arm) | micro CER (T1) | TONE mark-specific, kept | UPPER | LOWER | consonant, kept | latency |
|---|---|---|---|---|---|---|---|
| VCD | loop→misread 4, loop→overgen 2, misread→loop 1, misread→omission 1 | 1.124 → 0.565, −0.56 [−1.45, +0.29] | 0.041 → 0.067, **+0.026 [+0.009, +0.059]** | +0.020 [−0.005, +0.058] | +0.055 [−0.011, +0.123] | −0.015 [−0.028, −0.001] | ×1.24 |
| M3ID | **loop→misread 6**, loop→overgen 1 | 1.124 → 0.213, **−0.91 [−1.63, −0.34]** | 0.037 → 0.076, **+0.039 [+0.030, +0.051]** | +0.010 [−0.006, +0.033] | +0.053 [−0.003, +0.108] | −0.008 [−0.016, −0.001] | ×1.04 |
| PAI | misread→loop 7, misread→overgen 4, … ; **0 items kept** | 1.124 → 3.327, +2.20 [+1.08, +3.82] | — | — | — | — | ×5.24 |

Kept items (FULL and arm both `misread`/`reading_order`): VCD 10, M3ID 12, PAI 0.

### Typhoon OCR 1.5

| arm | cause transitions | micro CER (T1) | TONE mark-specific, kept | UPPER | LOWER | consonant, kept | latency |
|---|---|---|---|---|---|---|---|
| VCD | loop→misread 1, omission→misread 1, overgen→reading_order 1 | 0.276 → 0.045, −0.23 [−0.70, −0.01] | 0.004 → 0.010, +0.006 [+0.001, +0.015] | +0.002 [−0.000, +0.005] | 0.000 | −0.011 [−0.023, −0.000] | ×1.86 |
| M3ID | loop→misread 1, omission→misread 1, overgen→reading_order 1, misread→reading_order 1 | 0.276 → 0.057, −0.22 [−0.69, +0.01] | 0.004 → 0.010, +0.006 [+0.001, +0.015] | +0.002 [−0.000, +0.004] | 0.000 | −0.006 [−0.019, +0.002] | ×1.64 |
| PAI | misread→overgen 9, misread→omission 5, misread→loop 4; 1 item kept | 0.276 → 3.233, +2.96 [+2.18, +4.06] | (1 item) | — | — | — | ×7.69 |

Kept items: VCD 20, M3ID 20, PAI 1. Typhoon's tone counts are small (single
digits of errors), so its tone intervals rest on very few events.

## 3. Exploratory, not registered: what the extra tone errors are

Fates of every reference tone mark on kept items (structural, de-looped):

| model, arm | correct | deleted | tone→other tone | tone→other char |
|---|---|---|---|---|
| base FULL / VCD (10 items) | 625 / 613 | **18 / 37** | 8 / 7 | 28 / 22 |
| base FULL / M3ID (12 items) | 851 / 807 | **21 / 55** | 16 / 15 | 33 / 44 |
| typhoon FULL / VCD (20 items) | 1568 / 1578 | 20 / 18 | 7 / 7 | 15 / 7 |
| typhoon FULL / M3ID (20 items) | 1568 / 1579 | 20 / 20 | 7 / 4 | 15 / 7 |

On the base, the contrastive arms roughly **double tone-mark deletions**;
confusions between tone marks barely move. On Typhoon the unconditional tone
counts improve slightly while the base-conditioned rate worsens slightly —
both on a handful of marks.

## 3b. Per-item differences and item-mean (added 2026-10-04 at Up2mEz's request)

The pooled ratio in §2 weights items by their number of marks and keeps only
items both arms left readable. Per item, on the same kept items, tone
mark-specific error (base-correct marks), arm vs FULL:

| model, arm | items | worse / better / same | item-mean diff | item-median diff | pooled diff | net extra tone errors | share from the top 3 items |
|---|---|---|---|---|---|---|---|
| typhoon VCD | 19 | 4 / 0 / 15 | +0.004 | **0.000** | +0.006 | +10 | 0.90 (one page, `0159AF30`, +7) |
| typhoon M3ID | 19 | 4 / 0 / 15 | +0.004 | **0.000** | +0.006 | +10 | 0.90 (`0159AF30`, +7) |
| base VCD | 10 | 6 / 1 / 3 | +0.043 | +0.012 | +0.026 | +17 | 0.71 |
| base M3ID | 12 | **9 / 0 / 3** | +0.041 | +0.036 | +0.039 | +33 | 0.48 |

Reading: on the **base** the tone cost of contrast is broad — most items lose
tone marks, none gain. On **Typhoon** it is concentrated: the median item is
unchanged and one long page (the one that repeats paragraphs under
`TYPHOON_CARD`) carries 7 of the 10 extra tone errors. For Typhoon the open
question is therefore whether contrast can end loops without costing marks on
such pages, rather than a general deletion effect. Exact per-item counts:
`runs/exports/r1_per_item_tone.json` (local, not committed).

## 4. Interpretation (inference, not established)

- **Contrastive decoding's large CER gains come from ending loops, not from
  reading marks better.** Both VCD and M3ID turn most looping base outputs
  into readable ones; consonant error also falls slightly. That is a real
  effect on output quality, but it is not a mark fix.
- **On readable output they cost tone marks, by deletion.** Contrast lowers the
  score of any token the no-image or noised stream also predicts — including a
  tone mark that is well supported by the image *and* predictable from its
  syllable. Deletion under contrast therefore shows that tone marks here are
  **prior-predictable**; it does not show that they rely on the prior instead
  of the image. T2's image gain at tone sites (after its rerun) is the direct
  test; mark-aware contrast (§6, direction 2) tests the deletion mechanism.
  *(Revised 2026-10-04 after Up2mEz's review,
  `collab/messages/20261003T1810Z_Up2mEz_to_PELY334_review-r1-pilot-and-s1-addendum3.md`;
  the first version over-read this as "the opposite of the prior-overrides-image
  story".)*
- **The PAI-style arm (α = 0.5 from layer 2) breaks generation** on both models
  (no item kept on the base) while its α = 0 control is exact. With the
  implementation not yet checked line by line against the paper (registration
  §2), this points to a setting or implementation mismatch at least as much as
  to a property of PAI.
- Latency: VCD/M3ID cost ×1.6–1.9 on Typhoon; on the base they look cheap
  (×1.0–1.2) only because FULL's loops run to `max_new_tokens`.

## 5. What this result does not show

- Not that any remedy helps or hurts Thai marks in general: 24 items, one
  setting per method, intervals wide, two checkpoints of one architecture
  family.
- Not a comparison with T2's oracle upper bound.
- Not that the implementations match the papers line by line (registration §2).
- Not anything about the locked split, other prompts, or `TYPHOON_CARD`.
- Typhoon's absolute scores remain exposed to possible benchmark
  contamination (Decision Log 2026-09-27).

## 6. Directions this points to (proposals, need their own registration)

1. **Loop-triggered contrast.** Decode greedily; switch to contrastive scoring
   only once `loop_period` detects a loop in the generated tail. Targets the
   gain seen here (loops) without touching readable outputs, where marks are
   lost.
2. **Mark-aware contrast.** Apply the contrast weight only when the top
   candidates differ in more than Thai combining marks; leave decisions between
   a syllable with and without a mark to the plain greedy score. Tests the
   deletion mechanism of §3 directly.
3. **PAI-style at much lower strength or in fewer, later layers**, chosen on a
   calibration sub-split, after the line-by-line check against the paper.

Priority, as Up2mEz suggested: direction 2 first, on Typhoon (only 1 of 24
Typhoon outputs looped, so direction 1 mostly serves the base). Before building
it, add per-item differences and an item-mean sensitivity to the pooled tone
result, which weights items by mark count and keeps only items the arm itself
left readable.
4. Read §3 against T2's image gain at tone sites once T2 is posted.
