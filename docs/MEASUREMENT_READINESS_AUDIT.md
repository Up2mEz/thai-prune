# Measurement Readiness / Identifiability Audit

> Status: `HUMAN_REVIEW_AFTER_MEASUREMENT_READINESS_AUDIT`
>
> Recommendation: `FREEZE_OVERALL_MODEL_BUDGET_DESIGN`
>
> Source: existing S0 open-calibration artifacts from
> `kaggle-paddle-wayu-s0-a7f3eec06bce-832fe44f` only. No new model inference,
> locked-validation access, compression, budget selection, or fine-tuning was
> performed.

Derived planning artifact:
`runs/kaggle/kaggle-paddle-wayu-s0-a7f3eec06bce-832fe44f/analysis/measurement_readiness_audit.json`,
SHA-256
`6f60105e5b7a3efac6a8acbbf87f37fa00c3778b886d06846177d2abcf9356b4`.

## 1. Question, evidence, and limits

This audit asks whether a future `MODEL x BUDGET` effect is identifiable given
the observed full-information baselines. S0 supplies no reduced-budget outcome,
so the power results below are design simulations under stated assumptions—not
empirical compression evidence.

The intended meaningful effect is the registered planning SESOI of 10
percentage points (pp). For a downward effect, a cell with baseline probability
`p` can decline by at most `p` pp. The raw headroom relative to the SESOI is
therefore `p - 0.10`.

## 2. Pre-specified headroom classification rule

The thresholds are derived from the 10 pp SESOI, not from which cells happened
to pass:

- `ADEQUATE_HEADROOM`: pair-clustered lower CI >= 20%. Even at the conservative
  baseline bound, a 10 pp decline leaves at least one additional SESOI above
  the exact floor.
- `MARGINAL_HEADROOM`: lower CI >= 10% but < 20%. A 10 pp decline is
  structurally possible at the conservative bound, but leaves less than one
  SESOI of reserve and is vulnerable to floor compression.
- `FLOOR_LIMITED`: lower CI < 10%. A scientifically meaningful 10 pp downward
  change is not supported across the plausible baseline range.

This rule uses the CI lower bound because identifiability depends on baseline
precision as well as the point estimate. It does not assert that 20% accuracy
is generally “good OCR.”

## 3. MODEL x COMPONENT floor/headroom audit

`Max drop` is the maximum possible absolute downward degradation from the point
estimate. `SESOI surplus` is `Max drop - 10 pp`. Floor/ceiling are fractions of
the 19 `pair_id` cluster means equal to exactly 0 or 1 across their eight
registered render/member observations.

| Model | Component | Full-information exact [95% CI] | Max drop | SESOI surplus | Pair floor | Pair ceiling | Classification |
|---|---|---:|---:|---:|---:|---:|---|
| BASE | `BASE_CHARACTER` | 58.55% [44.08, 72.37] | 58.55 pp | +48.55 pp | 5.26% | 21.05% | `ADEQUATE_HEADROOM` |
| BASE | `LOWER_VOWEL_VARIANT` | 5.92% [1.32, 11.18] | 5.92 pp | -4.08 pp | 73.68% | 0.00% | `FLOOR_LIMITED` |
| BASE | `STACKED_TONE_MARK` | 13.16% [5.92, 21.07] | 13.16 pp | +3.16 pp | 52.63% | 0.00% | `FLOOR_LIMITED` |
| BASE | `TONE_MARK` | 52.63% [34.87, 69.74] | 52.63 pp | +42.63 pp | 26.32% | 26.32% | `ADEQUATE_HEADROOM` |
| BASE | `UPPER_VOWEL_VARIANT` | 18.42% [9.87, 26.97] | 18.42 pp | +8.42 pp | 42.11% | 0.00% | `FLOOR_LIMITED` |
| SPECIALIZED | `BASE_CHARACTER` | 59.87% [49.34, 70.39] | 59.87 pp | +49.87 pp | 0.00% | 15.79% | `ADEQUATE_HEADROOM` |
| SPECIALIZED | `LOWER_VOWEL_VARIANT` | 28.29% [13.82, 44.08] | 28.29 pp | +18.29 pp | 47.37% | 5.26% | `MARGINAL_HEADROOM` |
| SPECIALIZED | `STACKED_TONE_MARK` | 40.79% [23.03, 58.55] | 40.79 pp | +30.79 pp | 42.11% | 10.53% | `ADEQUATE_HEADROOM` |
| SPECIALIZED | `TONE_MARK` | 56.58% [41.45, 71.05] | 56.58 pp | +46.58 pp | 15.79% | 21.05% | `ADEQUATE_HEADROOM` |
| SPECIALIZED | `UPPER_VOWEL_VARIANT` | 42.11% [27.63, 55.92] | 42.11 pp | +32.11 pp | 26.32% | 0.00% | `ADEQUATE_HEADROOM` |

The BASE lower-vowel point estimate is below the SESOI, so a 10 pp downward
effect is mathematically impossible in that cell. BASE stacked-tone and
upper-vowel have positive point headroom but their lower confidence bounds do
not support a full 10 pp change. High pair-floor fractions also show that this
is not merely an aggregate-CI issue.

## 4. Simulation / resampling design

The reproducible derived artifact used 5,000 simulated studies per scenario and
seed `20260912`. Its assumptions are:

1. One generic future reduced-budget condition is contrasted with full
   information. No token count or budget value is selected.
2. Pair-specific baseline probabilities come from the observed eight-condition
   `pair_id` means. A Jeffreys-smoothed version is a sensitivity analysis.
3. A common log-odds shift is calibrated separately within each model to attain
   requested marginal degradations of 0, 5, 10, 15, or 20 pp while respecting
   probability bounds.
4. Each simulated study resamples the 95 paired `pair_id` clusters. The eight
   member/font/size outcomes remain inside their cluster; power is never
   calculated as if 760 renders were independent.
5. Conditional binomial variation within a cluster is an assumed planning
   model. It is not learned reduced-budget correlation and may be optimistic or
   pessimistic.
6. Detection means a 95% cluster-level interval for the paired marginal
   difference-in-differences excludes zero. This is an approximation to the
   proposed future primary model, not a frozen analysis implementation.

## 5. Overall interaction planning

The table reports empirical plug-in simulations. `Null FPR` is the probability
of falsely detecting interaction when both models have the same requested
degradation. Power columns impose a 10 pp differential in either direction.

| Common degradation | Null FPR | Power: BASE drops 10 pp more | Power: SPECIALIZED drops 10 pp more |
|---:|---:|---:|---:|
| 0 pp | 5.30% | 97.30% | 97.44% |
| 5 pp | 5.20% | 94.14% | 96.48% |
| 10 pp | 5.24% | 86.14% | 93.06% |
| 15 pp | 4.92% | 83.78% | 87.24% |
| 20 pp | 5.70% | structurally infeasible | 77.56% |

At a common 20 pp decline, asking BASE to decline another 10 pp exceeds its
29.74% empirical overall baseline. This is a direct structural floor warning,
not a failed numerical optimizer.

Jeffreys smoothing produced null false-positive rates 4.78–5.42%. Its 10 pp
differential power ranged from 82.50–95.22% for BASE-degrades-more and
91.72–95.04% for SPECIALIZED-degrades-more across common drops 0–20 pp. The
disagreement over feasibility at the deepest scenario shows that conclusions
near the floor depend on the smoothing assumption.

These results support identifiability of an overall 10 pp interaction under a
single generic reduced condition for moderate common degradation. They do not
validate a particular visual-token budget, a degradation curve, or model
robustness.

## 6. Component interaction planning

With only 19 clusters per component, empirical plug-in detection probability
for a 10 pp differential at zero common degradation was:

| Component | BASE drops more | SPECIALIZED drops more |
|---|---:|---:|
| `BASE_CHARACTER` | 33.62% | 34.18% |
| `LOWER_VOWEL_VARIANT` | structurally infeasible | 56.18% |
| `STACKED_TONE_MARK` | 49.72% | 47.50% |
| `TONE_MARK` | 38.76% | 42.02% |
| `UPPER_VOWEL_VARIANT` | 39.24% | 39.90% |

Thus even cells with baseline headroom generally lack convincing cluster-level
power for a cross-model three-way interaction. Headroom is necessary but not
sufficient; 19 clusters and heterogeneous pair behavior remain limiting.

## 7. Recommended primary and sensitivity analyses

### Primary: clustered logistic model with marginal interaction estimand

Use a pre-registered mixed-effects logistic regression for binary exact
transcription with fixed `MODEL`, categorical `BUDGET`, and `MODEL x BUDGET`,
plus registered font, size, and member terms. Include a `pair_id` random
intercept and, if convergence diagnostics support it under simulation before
locked analysis, a pair-level budget slope. The model separates the baseline
`MODEL` effect from the interaction on the log-odds scale.

Report the interaction both as the fitted log-odds term and as a marginal
probability difference-in-differences obtained by g-computation over the frozen
pair/render distribution. Use a `pair_id` cluster bootstrap for the marginal
95% CI. The probability-scale estimand keeps the 10 pp SESOI interpretable;
the logistic model respects 0/1 bounds instead of allowing impossible drops.

Do not exclude floor/ceiling pairs. Report model-specific change from each
model's own full-information baseline and include predicted probabilities so
log-odds interactions are not mistaken for equal percentage-point changes.
Pre-register convergence/fallback rules before locked inference.

### Sensitivity: direct pair-level marginal bootstrap

Aggregate the registered renders within every `MODEL x BUDGET x pair_id` cell,
calculate each model's change from its own full-information baseline, then form
the paired difference-in-differences. Bootstrap whole `pair_id` clusters. This
is transparent and robust to logistic-model specification, but can exhibit
floor compression; therefore report attainable headroom and floor fractions
beside it.

Raw absolute drops without own-baseline changes or without the interaction
contrast are not sufficient because the two models begin at different levels.

## 8. Metric readiness

### A. Exact transcription accuracy

Keep as the registered primary metric for an overall analysis. It has a clear
binary interpretation, preserves the frozen parser, and the 95-cluster planning
shows useful overall interaction sensitivity. Its limitations are severe
component floors, loss of error magnitude, and discontinuity between nearly
correct and unrelated outputs. It is not ready as a confirmatory primary metric
for every component cell.

### B. Codepoint CER

Keep as a pre-registered secondary/sensitivity metric. It uses more information
than exact match and may reduce floor saturation, but short Thai strings make a
single codepoint error a large CER jump. Insertions and combining marks can also
produce ambiguous alignments. CER must not retroactively replace exact accuracy
or be selected because it yields a preferred S0 conclusion.

### C. Critical-orthographic-component score

Potentially defensible only as a future pre-registered measurement redesign.
A valid score would need to test whether the exact differentiating Thai
grapheme/codepoint sequence was recovered at a uniquely aligned position while
the shared surrounding context provides a valid anchor. Required safeguards:

- freeze Unicode representation and grapheme segmentation before inference;
- require a unique alignment; mark ambiguous cases unscorable rather than
  choosing the candidate that benefits the model;
- prevent accidental candidate matching by never scoring “closer to member A
  or B” alone;
- require sufficient shared-context recovery so an unsupported isolated mark
  does not receive credit;
- reject unrelated extra text and visually unsupported guesses under a frozen
  output contract;
- validate the metric on synthetic unit cases and human-reviewed open examples
  without using locked outcomes.

Risks include accidental candidate matching, rewarding unrelated outputs,
Unicode alignment ambiguity, and partial credit for visually unsupported
guesses. No post-hoc critical-component primary result is calculated from S0.

## 9. Research-branch comparison

| Design | Interpretability | Novelty | Floor risk | Power | Original-RQ fit | Publication value | Extra work |
|---|---|---|---|---|---|---|---|
| Option A: overall `MODEL x BUDGET`; components descriptive | Strongest: directly separates baseline and overall interaction | Bounded evaluation contribution; not a new method | Moderate overall, explicit and auditable | Best-supported: ~84–97% in moderate planning scenarios | Direct | Coherent if limitations and marginal estimand are explicit | Lowest; analysis preregistration plus approved budget design |
| Option B: overall primary; SPECIALIZED component secondary; conditional three-way | More complex and asymmetric across models | Potentially richer | High in BASE cells | Component power only ~34–56%; three-way weak even where headroom exists | Partial | Risk of fragmented or selectively interpretable claims | Moderate-high; hierarchy and multiplicity plan needed |
| Option C: redesign component instrument first | Strong for a future component question if redesign succeeds | Measurement contribution possible, not guaranteed | Could reduce floors but introduces new contract | Unknown until new open recalibration | Delays the overall RQ | Potentially high but speculative | Highest; design, validation, human review, and recalibration |

Option A is the most defensible current branch. It answers the original overall
question with the unit that has plausible identifiability, while retaining
component results as descriptive diagnostics. Option B overreaches the current
19-cluster component information. Option C is justified only if confirmatory
component inference is made essential by a later human decision; it is not
required to answer the overall question.

## 10. Review of proposed Gate criteria

| Existing criterion | Decision | Revision/rationale |
|---|---|---|
| Overall lower CI >= 20% | `KEEP` | Interpret explicitly as `2 x SESOI`: after a 10 pp downward effect, the conservative baseline retains one SESOI of reserve. Apply separately to both models and only to overall readiness. |
| Component lower CI >= 10% | `REVISE` | Use the three-tier headroom rule: <10% floor-limited; 10–<20% marginal; >=20% adequate. Ten percent establishes only structural possibility, not adequate reserve or power. Confirmatory component interaction additionally requires simulation-based power and multiplicity review. |
| Render-cell range <= 10 pp | `REVISE` | Raw max-minus-min point range ignores pairing and uncertainty. Replace with pre-registered pair-clustered contrasts among render cells; require the upper 95% bound of the largest absolute nuisance contrast to remain below the 10 pp SESOI, or model font/size explicitly and demonstrate interaction stability. |
| Contract failure <=1%; Thai output >=80% | `REVISE` | Separate them. Contract failure is an engineering/interpretability guardrail and should use an upper pair-clustered CI, not only a point rate. Thai-output rate is descriptive, not a readiness gate: unrelated Thai text can satisfy it while exact measurement fails. |

These remain proposed criteria. This audit does not freeze them.

## 11. Epistemic classification

### FACT

- S0 observed different full-information baselines and heterogeneous component
  capacity on 95 open-calibration clusters.
- Three BASE component cells are `FLOOR_LIMITED` under the SESOI-derived rule.
- Under the stated simulation, overall 10 pp interaction detection is much
  stronger than component-level detection.

### INFERENCE

- An overall `MODEL x BUDGET` design is plausibly identifiable if a future
  approved budget produces moderate degradation and the registered clustered
  analysis behaves approximately as simulated.
- Component-confirmatory inference is not adequately supported by current
  headroom plus 19-cluster planning.

### UNKNOWN

- Actual degradation, dependence across budgets, logistic-model fit,
  random-slope convergence, and power under real token reduction are unknown.
- No specific budget, compression operation, or mechanism has been evaluated.
- Whether a critical-component metric would improve valid measurement remains
  unknown until a separately approved open-data redesign.

### PROHIBITED INTERPRETATIONS

This audit does not establish compression robustness, specialization-induced
robustness, a `MODEL x BUDGET` interaction, component-specific degradation,
causal effects of Thai training, or a need for a new method.

## 12. Recommendation and stop

`FREEZE_OVERALL_MODEL_BUDGET_DESIGN`

This recommendation concerns only the future analysis structure: overall
`MODEL x BUDGET` primary, exact transcription primary metric, clustered logistic
model with marginal g-computed interaction, and pair-level bootstrap
sensitivity. Component results remain descriptive. It does not select a token
budget, freeze the proposed Gate criteria, authorize locked validation, or
authorize compression.

Terminal state: `HUMAN_REVIEW_AFTER_MEASUREMENT_READINESS_AUDIT`.
