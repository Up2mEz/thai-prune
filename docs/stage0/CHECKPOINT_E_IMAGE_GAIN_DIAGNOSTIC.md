# Checkpoint E — Calibration Image-Gain / Decision-Margin Diagnostic

**Status:** `CALIBRATION_DIAGNOSTIC_COMPLETE_PENDING_HUMAN_REVIEW`

**Evidence status:** `CALIBRATION_DIAGNOSTIC_ONLY_NOT_PRIMARY_METRIC`

**Gate 0:** `NOT_RUN_CRITERIA_NOT_FROZEN`

**Locked validation:** `BLOCKED_UNEXPOSED`

**Stage 1A, compression, and secondary backbone:** `NOT_RUN`

## 1. Scope and provenance

The diagnostic used only the 100 previously exposed calibration `pair_id`
values: 800 `FULL_INFORMATION` observations and 200 matched
`LANGUAGE_CANDIDATE_BIAS_BLANK` controls. It did not expose a locked pair.

- remote run: `kaggle-stage0-margin-80088b862c5a-008c5556`;
- inference Git commit: `80088b862c5a399c5923b83f777147bddb6ed101`;
- analysis Git commit: `3c16e80`;
- model and processor:
  `Qwen/Qwen2.5-VL-3B-Instruct@66285546d2b821cf421d4f5eb2576359d3770cd3`;
- runtime: Kaggle Tesla T4, `float16`, `sdpa`, Python 3.12.13,
  `torch==2.14.0+cu130`, `transformers==4.57.6`, CUDA 13.0;
- image preprocessing, 448 × 448 rendering, prompt v1, exact parser,
  deterministic decoding, and seed policy were unchanged;
- every call contained 256 actual LLM-boundary visual positions.

Raw logits and all observation metadata are retained in
`runs/kaggle/kaggle-stage0-margin-80088b862c5a-008c5556/`. Artifact checksum
verification passed. The registered binary predictions agree with repaired
calibration `exact_run_1` for all 1,000 observations.

The first local analysis command reached the host command-return limit after
30 seconds but completed the derived files. A repeated invocation correctly
refused to overwrite them. Both events and the superseding v2 analysis are
preserved in the run directory; they did not change model evidence or add
statistical observations.

## 2. Engineering smoke

The 40-call engineering smoke passed before the 1,000-call diagnostic began.

| Required check | Result |
|---|---|
| Registered assistant-boundary token IDs | exact `A=32`, `B=33` |
| `generate` versus independent direct-forward logits | exact agreement on all 40 calls |
| Generated label versus A/B logit argmax | exact agreement on all 40 calls |
| Historical registered binary prediction | unchanged on all 40 calls |
| Exact-rerun logits, margins, and label | deterministic on all 20 matched observations |
| Visual-token count | 256 on every call |

Smoke results are engineering evidence only and are excluded from all
scientific summaries below.

## 3. Diagnostic definitions and statistical grain

For raw, pre-generation-processor logits `z_A` and `z_B`:

```text
position_margin = z_A - z_B
correct_margin = logit(correct displayed label) - logit(incorrect label)
canonical_member_margin = signed margin toward canonical member a
image_gain = FULL_INFORMATION correct_margin - matched-blank correct_margin
```

The matched blank has the same `pair_id` and candidate orientation. A positive
`image_gain` means that replacing the blank canvas with the registered rendered
stimulus moved the A/B decision evidence toward the displayed correct member.
It is a diagnostic association, not a causal effect and not a calibrated
probability.

All 95% intervals resample `pair_id` clusters. Repeated members, fonts, sizes,
orientations, and renderings are not independent units. There is one diagnostic
run; the earlier exact rerun is used only as a frozen binary reference.

## 4. Observed calibration evidence

### 4.1 Image evidence by component

| Component | Binary accuracy | Mean `image_gain` (pair-clustered 95% CI) | Gain > 0 |
|---|---:|---:|---:|
| `BASE_CHARACTER` | 96.25% | 1.863 (1.627, 2.103) | 89.38% |
| `TONE_MARK` | 81.88% | 0.843 (0.656, 1.029) | 80.63% |
| `UPPER_VOWEL_VARIANT` | 63.75% | 0.210 (0.134, 0.285) | 56.88% |
| `LOWER_VOWEL_VARIANT` | 58.13% | 0.095 (0.054, 0.134) | 56.25% |
| `STACKED_TONE_MARK` | 56.25% | 0.124 (0.057, 0.199) | 56.25% |
| Overall | 71.25% | 0.627 (0.482, 0.782) | 67.88% (64.25%, 71.63%) |

The image systematically moves evidence toward the correct candidate overall
and in the mean for every registered component. However, the gain is much
smaller and only slightly more often positive than negative for the lower-
vowel and stacked-tone categories. Their low binary accuracy therefore does
not mean the image contributes no information, but the contribution is weak
and heterogeneous relative to the stronger categories.

### 4.2 Blank-position prior

Blank images have no correct visual answer. Across the 200 blank controls, the
model chose displayed position A in 85.0% of calls (pair-clustered 95% CI
80.0–89.5%), with mean `z_A-z_B = 0.358` (0.308, 0.411). Component A-choice
rates were 100% (`BASE_CHARACTER`), 80% (`LOWER_VOWEL_VARIANT`), 82.5%
(`STACKED_TONE_MARK`), 70% (`TONE_MARK`), and 92.5%
(`UPPER_VOWEL_VARIANT`).

The overall matched-blank correct margin averages to zero because the frozen
design balances which canonical member occupies position A. This cancellation
must not be interpreted as absence of position or candidate/language prior.

### 4.3 Lower-vowel and stacked-tone diagnosis

| Component/member displayed | Blank correct margin (95% CI) | `image_gain` (95% CI) | Full correct margin (95% CI) |
|---|---:|---:|---:|
| `LOWER_VOWEL_VARIANT` a | 0.091 (0.004, 0.172) | 0.221 (0.074, 0.355) | 0.313 (0.169, 0.441) |
| `LOWER_VOWEL_VARIANT` b | −0.091 (−0.172, −0.004) | −0.032 (−0.161, 0.089) | −0.124 (−0.236, −0.012) |
| `STACKED_TONE_MARK` a | −0.016 (−0.166, 0.120) | −0.305 (−0.528, −0.071) | −0.321 (−0.591, −0.060) |
| `STACKED_TONE_MARK` b | 0.016 (−0.120, 0.166) | 0.554 (0.389, 0.728) | 0.569 (0.363, 0.814) |

For `LOWER_VOWEL_VARIANT`, member b combines an adverse matched-blank prior
with no detectable compensating image gain. The present evidence therefore
supports **both** prior and weak visual-evidence limitations for that member.

For `STACKED_TONE_MARK`, matched-blank member margins are near zero, whereas
the image shift is strongly member-dependent and points in the wrong direction
for member a. Its dominant observed limitation is associated with visual/pair
composition rather than the measured blank prior. This does not identify a
causal model mechanism.

### 4.4 Font and size association

Paired 96 px minus 72 px effects preserve `pair_id` as the unit:

| Component | Accuracy difference | `image_gain` difference (95% CI) | Direction agrees? |
|---|---:|---:|---|
| `BASE_CHARACTER` | +2.50 pp | +0.131 (−0.002, 0.262) | yes |
| `TONE_MARK` | −6.25 pp | −0.154 (−0.344, 0.034) | yes |
| `UPPER_VOWEL_VARIANT` | 0 pp | −0.031 (−0.127, 0.060) | no directional accuracy effect |
| `LOWER_VOWEL_VARIANT` | +6.25 pp | +0.068 (−0.005, 0.142) | yes |
| `STACKED_TONE_MARK` | +5.00 pp | +0.147 (0.062, 0.241) | yes |

Size-related gain and accuracy move in the same direction for every component
with a non-zero accuracy difference. The evidence is clearest for stacked
tone marks. Font effects are less consistent: Serif improves lower-vowel
accuracy by 16.25 pp but its mean gain difference is only +0.024 and includes
zero; for tone marks, accuracy and gain move in opposite directions. Thus
scale has a coherent descriptive association, while font is not a uniform
explanation.

### 4.5 Canonical-member asymmetry

The paired member-a minus member-b `image_gain` contrast remains:

| Component | a − b `image_gain` (pair-clustered 95% CI) |
|---|---:|
| `BASE_CHARACTER` | −0.197 (−0.853, 0.546) |
| `TONE_MARK` | −0.672 (−1.211, −0.204) |
| `UPPER_VOWEL_VARIANT` | −0.072 (−0.578, 0.431) |
| `LOWER_VOWEL_VARIANT` | +0.254 (0.001, 0.505) |
| `STACKED_TONE_MARK` | −0.858 (−1.235, −0.472) |

Canonical-member asymmetry therefore remains in the margin evidence for
`TONE_MARK`, `LOWER_VOWEL_VARIANT`, and `STACKED_TONE_MARK`; it is not merely
an artifact of thresholding continuous evidence into a binary answer.

## 5. Interpretation boundaries

### Likely explanations supported as associations

- The model receives some useful image-conditioned evidence in all five
  categories, but its strength varies substantially by component and member.
- `LOWER_VOWEL_VARIANT` member-b failures are associated with both adverse
  blank prior and weak image gain.
- `STACKED_TONE_MARK` failures are more strongly associated with asymmetric
  image-conditioned evidence/pair composition than with the matched blank
  prior.
- Visual scale is a plausible measurement limitation because paired size
  changes usually move accuracy and gain together.

### Explanations not supported

- a single universal A-token mechanism explaining all errors;
- font or critical-region size as a proven cause;
- insufficient primary-model capacity as the cause;
- invalidity of difficult pairs;
- any compression, Resolution Reduction, Token Pruning, H1, or real-world OCR
  conclusion.

### Unresolved ambiguity

- whether a different full-information visual scale would produce adequate
  headroom without changing the construct being measured;
- why particular canonical members attract oppositely directed image evidence;
- how provisional lexical status and base-character composition contribute;
- whether the pattern is architecture-specific; no secondary backbone was run;
- the later hierarchical model and Gate 0 criteria remain unfrozen.

The dominant current limitation is associated with **visual scale/rendering
and pair/member composition**, with an additional candidate/language-prior
contribution for lower-vowel member b. Model capacity remains unresolved.

## 6. Runtime and execution audit

- remote submission: 374.36 s total;
- diagnostic inference section: 284.98 s;
- mean generation latency: 0.256 s/call; p95: 0.267 s/call;
- peak allocated GPU memory: 7,572,835,840 bytes;
- peak reserved GPU memory: 7,612,661,760 bytes;
- execution failures: 0;
- artifact verification: `VERIFIED`.

## 7. One recommended next action and mandatory stop

**Recommendation:** `MEASUREMENT_SCALE_DIAGNOSTIC`.

This is the lowest-cost next action aligned with the observed evidence: size
effects move accuracy and image gain coherently, especially for stacked tone
marks, while a task-only change would not explain the strong member-dependent
image shifts. Any scale diagnostic requires a new human-approved design and
must use only calibration pairs unless separately authorized. It must not
select scale from locked outcomes or be described as compression evidence.

Stop here for human review. Gate 0 criteria are not frozen; locked validation,
secondary-backbone inference, Stage 1A, Resolution Reduction, Token Pruning,
Token Merging, and all compression interventions remain blocked.
