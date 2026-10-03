# REMEDIES_R1 — results (Track B pilot)

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

## 4. Interpretation (inference, not established)

- **Contrastive decoding's large CER gains come from ending loops, not from
  reading marks better.** Both VCD and M3ID turn most looping base outputs
  into readable ones; consonant error also falls slightly. That is a real
  effect on output quality, but it is not a mark fix.
- **On readable output they cost tone marks, by deletion.** A plausible
  mechanism: the contrast subtracts what the language model predicts without
  (or with degraded) visual evidence. A tone mark after a known syllable is
  exactly such a prior-predictable token, so its score is pushed down and the
  unmarked continuation wins. If so, Thai tone marks on these models are
  carried partly by the language prior — the opposite of the "prior overrides
  the image" story, at least at these settings. T2's image-gain numbers are
  the direct test of this; this pilot only suggests it.
- **PAI at α = 0.5 from layer 2 breaks generation** on both models (no item
  kept on the base). This says the paper-default strength is wrong for page
  OCR on this architecture, not that attention amplification cannot work.
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
3. **PAI at much lower strength or in fewer, later layers**, chosen on a
   calibration sub-split, if attention amplification is still of interest.
4. Read §3 against T2's image gain at tone sites once T2 is posted.
