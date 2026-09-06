# Checkpoint D — Calibration-Only Diagnostic Assessment

**Status:** `ANALYSIS_ONLY_COMPLETE_PENDING_HUMAN_REVIEW`

**Gate 0:** `NOT_RUN`

**Locked validation:** `BLOCKED_UNEXPOSED`

**Additional model inference:** `NOT_AUTHORIZED_NOT_RUN`

**Stage 1A and compression:** `BLOCKED_NOT_RUN`

## 1. Scope and evidence grain

This checkpoint uses only the 100 already exposed calibration `pair_id` values
from repaired calibration run
`kaggle-stage0-repair-v2-39cd2e1841bc-4e76ab41`.

- `exact_run_1` is the sole analysis source: 800 `FULL_INFORMATION`
  observations and 200 blank controls.
- `exact_run_2` is used only for reproducibility auditing. It is not pooled,
  does not add independent observations, and does not narrow any interval.
- The effective independent-unit count remains 100 pairs overall and 20 pairs
  per component.
- No locked-validation pair, secondary backbone, new prompt, new rendering, or
  compression intervention was used.

Source hashes and the full machine-readable calculations are stored in the
immutable derived-artifact directory under
`runs/kaggle/kaggle-stage0-repair-v2-39cd2e1841bc-4e76ab41/checkpoint_d_analysis_only/`.

An intermediate derived-analysis draft exposed a bootstrap implementation
defect: replacement draws of the same pair were collapsed when estimating
paired rendering-effect intervals. Its point estimates were unchanged, but
its intervals are invalid. The draft was preserved under
`checkpoint_d_analysis_only_INVALID_BOOTSTRAP_DRAFT/`, explicitly marked
`INVALID_DERIVED_ANALYSIS_DRAFT`, and is not used below.

## 2. Observed member-identity asymmetry

Canonical `member_a` and `member_b` refer to the stable members in the pair
inventory. They do not refer to displayed answer positions A and B, which can
reverse by condition.

| Component | Member a accuracy (pair-clustered 95% interval) | Member b accuracy (pair-clustered 95% interval) | a − b | Member selected by errors |
|---|---:|---:|---:|---|
| `BASE_CHARACTER` | 98.75% (96.25–100%) | 93.75% (85–100%) | +5.00 pp | a: 5/6 |
| `TONE_MARK` | 73.75% (61.25–86.25%) | 90.00% (82.50–96.25%) | −16.25 pp | b: 21/29 |
| `UPPER_VOWEL_VARIANT` | 75.00% (62.50–87.50%) | 52.50% (38.75–66.25%) | +22.50 pp | a: 38/58 |
| `LOWER_VOWEL_VARIANT` | 77.50% (63.75–90%) | 38.75% (25–55%) | +38.75 pp | a: 49/67 |
| `STACKED_TONE_MARK` | 36.25% (22.50–50%) | 76.25% (66.25–86.25%) | −40.00 pp | b: 51/70 |

The large and oppositely directed gaps are direct evidence of member-specific
measurement behavior. They are not a generic “mark deletion” pattern:
`TONE_MARK` and `STACKED_TONE_MARK` errors tend toward member b, while upper-
and lower-vowel errors tend toward member a. The present analysis cannot tell
whether this arises from visual discriminability, lexical/candidate prior,
base-character composition, or their interaction.

## 3. Blank-prior alignment

Two complementary metrics avoid conflating displayed position with canonical
member identity.

1. **Matched-orientation prior-aligned error:** for each incorrect
   `FULL_INFORMATION` observation, the selected canonical member equals the
   blank-control selection for the same `pair_id` and the same candidate
   orientation.
2. **Unique pair-preference aligned error:** the error selects the strict
   canonical-member majority across the pair's two blank orientations. Pairs
   tied 1–1 are absent only from this secondary denominator.

Across 100 pairs, the blank pair-level preference was tied for 74 pairs,
member a for 21, and member b for 5. This high tie count is compatible with
the previously observed position-A preference: choosing displayed A under
both reversed orientations produces a canonical-member tie.

| Component | FULL errors | Matched-orientation aligned | Unique-preference eligible | Unique-preference aligned |
|---|---:|---:|---:|---:|
| `BASE_CHARACTER` | 6 | 83.33% (5/6) | 0 | N/A |
| `TONE_MARK` | 29 | 55.17% (16/29) | 13 | 46.15% (6/13) |
| `UPPER_VOWEL_VARIANT` | 58 | 46.55% (27/58) | 10 | 100% (10/10) |
| `LOWER_VOWEL_VARIANT` | 67 | 44.78% (30/67) | 26 | 46.15% (12/26) |
| `STACKED_TONE_MARK` | 70 | 58.57% (41/70) | 20 | 70% (14/20) |
| Overall | 230 | 51.74% (119/230) | 69 | 60.87% (42/69) |

The blank controls confirm strong candidate-position behavior, but the 51.74%
overall matched-orientation alignment does not support the stronger claim
that blank preference explains most visual errors. The 100% upper-vowel
secondary rate concerns only ten eligible errors from strict-preference pairs
and should not be generalized to all upper-vowel errors.

## 4. Rendering-condition diagnostics

Each cell contains accuracy and a 95% pair-cluster bootstrap interval over 20
pairs. These are descriptive calibration associations, not causal effects.

| Component | Sans 72 | Sans 96 | Serif 72 | Serif 96 |
|---|---:|---:|---:|---:|
| `BASE_CHARACTER` | 95% (87.5–100%) | 95% (87.5–100%) | 95% (87.5–100%) | 100% (100–100%) |
| `TONE_MARK` | 90% (80–97.5%) | 80% (70–90%) | 80% (70–90%) | 77.5% (67.5–87.5%) |
| `UPPER_VOWEL_VARIANT` | 60% (52.5–70%) | 67.5% (57.5–77.5%) | 67.5% (57.5–77.5%) | 60% (52.5–70%) |
| `LOWER_VOWEL_VARIANT` | 52.5% (45–60%) | 47.5% (42.5–50%) | 57.5% (50–65%) | 75% (65–85%) |
| `STACKED_TONE_MARK` | 55% (50–62.5%) | 55% (50–62.5%) | 52.5% (45–62.5%) | 62.5% (55–72.5%) |

Paired 96 px minus 72 px effects, averaged across the two fonts, were:

| Component | 96 − 72 effect (pair-clustered 95% interval) |
|---|---:|
| `BASE_CHARACTER` | +2.50 pp (−2.50 to +7.50) |
| `TONE_MARK` | −6.25 pp (−13.75 to +1.25) |
| `UPPER_VOWEL_VARIANT` | 0 pp (−10 to +10) |
| `LOWER_VOWEL_VARIANT` | +6.25 pp (−1.25 to +13.75) |
| `STACKED_TONE_MARK` | +5.00 pp (+1.25 to +10) |

The aggregate lower-vowel size effect hides a strong descriptive interaction:
96 − 72 is −5 pp (−12.5 to 0) under Sans but +17.5 pp (+2.5 to +30) under
Serif. At 96 px, Serif − Sans is +27.5 pp (+17.5 to +37.5). This supports
investigating a model/rendering interaction; it does not identify font, scale,
or model processing as a cause. Upper-vowel effects reverse direction across
fonts (+7.5 pp Sans and −7.5 pp Serif), producing a zero aggregate effect.

## 5. Pair-level heterogeneity and composition

The complete 100-row `pair_diagnostics.csv` reports for every exposed pair:

- component and canonical text members;
- provisional `lexical_status_a` and `lexical_status_b`;
- overall and member-specific accuracy;
- blank selection under each candidate orientation and pair-level preference;
- matched-orientation prior-aligned errors;
- Serif-minus-Sans and 96-minus-72 paired effects; and
- mean/min/max `critical_pixel_area`, critical bbox width, and bbox height.

The companion 400-row `pair_condition_diagnostics.csv` retains exact
pair × font × size geometry and member-specific correctness. No pair was
excluded, replaced, or relabeled based on model outcomes.

Pair accuracy remains heterogeneous:

- `BASE_CHARACTER`: sixteen of twenty pairs were perfect; the minimum was
  62.5%.
- `TONE_MARK`: 62.5–100%.
- `UPPER_VOWEL_VARIANT`: 50–87.5%.
- `LOWER_VOWEL_VARIANT`: 25–75%.
- `STACKED_TONE_MARK`: 37.5–87.5%, with thirteen of twenty pairs at 50%.

Only 52 observations displayed a provisional `REAL` member, compared with
748 `UNCERTAIN` observations; no displayed member was labeled `CONSTRUCTED`
in this calibration allocation. Accuracy was 75% for `REAL` and 70.99% for
`UNCERTAIN`, but the `REAL` interval was wide (55.77–90.38%) and involved only
ten pairs. `UNCERTAIN` was not reclassified, combined with `CONSTRUCTED`, or
excluded.

## 6. Critical-region association

Spearman associations use pair-cluster bootstrap intervals. They are
calibration diagnostics only; the critical mask is not a perceptual weighting
map, and the associations are not mechanistic or causal evidence.

At the pair level, pooling categories gives:

| Geometry summary | Spearman rho (95% pair-cluster interval) |
|---|---:|
| Mean `critical_pixel_area` | 0.474 (0.285–0.629) |
| Mean critical bbox width | 0.401 (0.187–0.577) |
| Mean critical bbox height | 0.470 (0.284–0.625) |

This pooled association is confounded by component category: base-character
pairs have both larger critical regions and much higher accuracy. Within
components, evidence is non-uniform:

- `TONE_MARK` and `STACKED_TONE_MARK` have no between-pair variation in their
  mean geometry under this design, so pair-level correlations are undefined.
- `LOWER_VOWEL_VARIANT` has only two pair-level geometry values and a weak
  area association (rho 0.111); at the pair-condition level the area
  association is 0.317 (0.126–0.506).
- `UPPER_VOWEL_VARIANT` also has only two pair-level geometry values; its
  pair-level rho is −0.293, while its pair-condition area association is
  −0.019 (−0.207–0.163).
- Base-character intervals are wide and include zero at the pair level.

These results do not support a single critical-region-size explanation.

## 7. Exact-rerun accounting audit

The two runs contain the same 1,000 observation IDs and agree 100% on raw
output, parsed output, parse status, and visual-token count. The audit passed.

All diagnostic accuracy, association, and interval estimates use only
`exact_run_1`. Therefore:

- reruns pooled for estimation: `false`;
- independent units added by rerun: `0`; and
- effective pair count: `100`, not 200.

## 8. Is pair-only clustered uncertainty sufficient?

Pair-cluster bootstrap is appropriate for the current marginal accuracy and
paired-condition summaries because it keeps all member/render observations of
a pair together. It is not sufficient as the only later-stage model for
attribution or interaction analysis:

- member effects are large and reverse direction by component;
- font and size effects interact for some components;
- candidate orientation and provisional lexical status may affect responses;
- systematic base-character reuse may create dependence not represented by a
  simple pair intercept; and
- only 20 independent pairs per component limits complex interaction
  precision.

Proposed later analysis, not adopted here, is an observation-level binomial
hierarchical model with fixed effects for `component_type`, canonical
`displayed_member`, `font_id`, `font_size`, candidate orientation, and
predeclared interactions, plus a random intercept for `pair_id`. A random
font-size or later budget slope by pair may be added only if identifiability
and convergence diagnostics support it. Future Stage 1 analysis would add the
registered `component_type × actual_budget` term. Pair-cluster bootstrap
marginal contrasts should remain a transparent sensitivity analysis.

The exact formula, interaction set, handling of provisional lexical status,
and convergence/fallback rules require human freeze before locked evidence;
they were not silently adopted in this checkpoint.

## 9. Phase 2 decision-margin feasibility and proposed design

### Code finding

The existing adapter does not currently save logits. However, the pinned
`transformers==4.57.6` implementation is technically capable of exposing the
raw next-token logits at the registered assistant boundary:

- `Qwen2_5_VLForConditionalGeneration.forward` applies `lm_head` and returns
  pre-Softmax `logits`;
- generation reads `outputs.logits[:, -1, :]` as the next-token logits before
  applying the prefix constraint; and
- `generate(return_dict_in_generate=True, output_logits=True)` retains those
  raw logits while the current `prefix_allowed_tokens_fn` subsequently masks
  every token except verified IDs 32 (`A`) and 33 (`B`).

Thus the existing generation pass can record the pre-constraint A/B logits
without changing the prompt, parser, visual-token boundary, or registered
forced-choice answer. Existing artifacts did not request `output_logits`, so
the values cannot be recovered retrospectively; new inference is required.

### Proposed diagnostic quantities

For raw logits `z_A` and `z_B`:

```text
p_A_two_choice = exp(z_A) / (exp(z_A) + exp(z_B))
normalized_position_margin = p_A_two_choice - p_B_two_choice
```

The normalized margin is in [−1, 1] and is positive toward displayed answer
position A. Also record:

- raw `logit_a_token` and `logit_b_token`;
- canonical-member margin, with sign reversed under `B_THEN_A` so positive
  always favors canonical member a;
- displayed-correct margin, signed so positive favors the shown member;
- matched blank canonical-member margin for the same `pair_id` and candidate
  orientation; and
- image-induced shift = full canonical-member margin minus its matched blank
  canonical-member margin.

These are secondary calibration diagnostics. They must not replace registered
forced-choice accuracy or be interpreted as calibrated probabilities over the
full vocabulary.

### Proposed workload requiring new human authorization

1. Two identical 20-call engineering margin smokes using the already exposed
   Repair-v2 smoke plan: 40 calls total. Verify finite logits, exact A/B token
   mapping, generated-choice/argmax parity, token accounting, artifact
   completeness, and rerun choice agreement. A numerical logit/margin
   tolerance must be frozen by the human before execution.
2. If the smoke passes, one 1,000-call diagnostic pass over the existing
   calibration observation plan: 800 full-information images and 200 matched
   blank controls.
3. Do not pool the smoke with analysis, expose locked pairs, or alter the
   registered primary calibration results.

Total proposed new inference: 1,040 calls. **This workload has not been run.**

## 10. Interpretation boundaries

### Supported by current calibration diagnostics

- **Pair composition/member identity:** materially associated with accuracy;
  the direction differs by component.
- **Visual scale/rendering:** materially associated for at least some
  component-condition combinations, especially lower vowels under Serif 96.
- **Candidate/language prior:** a strong blank position-A preference exists,
  but matched blank preference does not explain most errors overall.

### Not supported

- one dominant causal mechanism;
- a claim that difficult pairs are invalid;
- a claim that increasing size always improves accuracy;
- a claim that critical-region size alone explains component accuracy;
- a model-capacity conclusion from a single backbone;
- any compression, H1, Thai-specific vulnerability, or real-world OCR claim.

### Unresolved

- whether discrete choices near chance conceal weak but directionally correct
  visual evidence;
- how much member asymmetry is caused by linguistic prior versus visual form;
- whether the primary backbone is the limiting factor; and
- which hierarchical structure is stable with only 20 pairs per component.

## 11. Recommendation and mandatory stop

**Recommendation:** `MULTIPLE_DIAGNOSTICS_REQUIRED`.

The evidence contains simultaneous pair/member, rendering, and prior-related
signals, while model capacity remains untested. The lowest-cost next step is
the proposed decision-margin diagnostic because it directly quantifies image
evidence relative to matched blank input without changing the registered
task. If ambiguity remains, a separately authorized secondary-backbone
diagnostic may be needed; it must not be selected based on a favorable effect.

No Gate 0 criteria are frozen. Locked validation, secondary-backbone
inference, Stage 1A, Resolution Reduction, Token Pruning, Token Merging, and
all other compression interventions remain blocked pending a new human
decision.
