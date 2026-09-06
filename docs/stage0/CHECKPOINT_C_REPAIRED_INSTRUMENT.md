# Checkpoint C — Repaired Instrument & Baseline Ceiling Assessment

**Status:** `REPAIRED_CALIBRATION_COMPLETE_PENDING_HUMAN_REVIEW`
**Gate 0:** `NOT_RUN`
**Locked validation:** `BLOCKED`
**Stage 1A and compression:** `BLOCKED`

## 1. Evidence identity

| Item | Value |
|---|---|
| Run ID | `kaggle-stage0-repair-v2-39cd2e1841bc-4e76ab41` |
| Evidence-producing Git SHA | `39cd2e1841bc0433792278bf9019acd5ebce1aeb` |
| Repair config SHA-256 | `4e76ab412f5f2ebeaa84214cf66663f51b5ec678412b8867d3251c06b1cd1394` |
| Frozen allocation SHA-256 | `385c283091852820016bd6b1247a01af90ee04e966d298761f14cd392b8f47e8` |
| Frozen bundle SHA-256 | `d865d689f296f4e929c3adce4b2aa75dab56958d9e203ef940a9edbcf54f1992` |
| Artifact checksum-list SHA-256 | `c798c087324c73f09ed27549aa13080febb8a8179c918cfbc58718eb466cfb24` |
| Checkpoint C evidence SHA-256 | `eb672b8d26942d704b810086ea25145a2929bd59e4dd4aa8d354db46b906097e` |

The Kaggle title resolved to the actual notebook slug
`thanakritsamoena/labbs2026-stage-0-calibration-repair-v2`, while the submitted
metadata requested `thanakritsamoena/labbs2026-stage0-repair-v2`. The local
status record preserves both values. This is a provenance warning, not a
stimulus, model, or output-contract change.

## 2. Historical evidence remains unchanged

The previous two 1,000-call runs remain
`REGISTERED_OUTPUT_PARSER_CONTRACT_FAILURE`. They were not reparsed into
registered evidence and their files were not overwritten. Repair v2 uses new
run IDs and a new generation contract.

## 3. Tokenizer and output contract

At the actual chat boundary after `<|im_start|>assistant\n`, canonical `A` and
`B` are distinct single-token continuations: `A -> 32` and `B -> 33`.
Leading-space forms use different IDs and newline forms require two tokens.

Repair v2 generated exactly one token with `do_sample=false`, allowing only
IDs 32 or 33. Runtime verification repeated the mapping for every prompt. The
registered exact parser remained `^[AB]$`; no leading-label regex was used.

**Finding:** the repaired output/parser contract is valid for this calibration:
2,000/2,000 registered calls conformed, with zero parser failures.

## 4. Engineering smoke — not scientific evidence

The frozen smoke used five already exposed calibration pairs, one per
component, one frozen rendering condition, both displayed members, both blank
orientations, and an exact rerun.

| Acceptance requirement | Result |
|---|---:|
| Calls completed | 40/40 |
| Execution failures | 0 |
| Output-contract conformance | 100% |
| Parser failures | 0 |
| Parsed-choice rerun agreement | 100% |
| Raw-output rerun agreement | 100% |
| Visual-token rerun agreement | 100% |
| Candidate-order audit | PASS |

Visual accuracy was not computed for the smoke. The smoke passed before the
full repaired calibration began.

## 5. Registered repaired calibration

Both exact runs produced identical outputs and metrics.

| Metric | Exact run 1 | Exact run 2 |
|---|---:|---:|
| Calls completed | 1,000/1,000 | 1,000/1,000 |
| FULL_INFORMATION observations | 800 | 800 |
| Blank controls | 200 | 200 |
| Execution failures | 0 | 0 |
| Output-contract failures | 0 | 0 |
| Parser failures | 0 | 0 |
| Raw/parsed/token rerun agreement | 100% | 100% |

### Full-information accuracy and pair-clustered uncertainty

| Component | Accuracy | Pair-clustered 95% interval | Above chance | Hypothetical accuracy after a 10 pp drop |
|---|---:|---:|---:|---:|
| `BASE_CHARACTER` | 96.25% | 91.88–99.38% | 46.25 pp | 86.25% |
| `TONE_MARK` | 81.88% | 75.63–88.13% | 31.88 pp | 71.88% |
| `UPPER_VOWEL_VARIANT` | 63.75% | 58.75–68.75% | 13.75 pp | 53.75% |
| `LOWER_VOWEL_VARIANT` | 58.13% | 53.13–62.50% | 8.13 pp | 48.13% |
| `STACKED_TONE_MARK` | 56.25% | 51.88–61.88% | 6.25 pp | 46.25% |
| Overall | 71.25% | 67.50–75.00% | 21.25 pp | 61.25% |

Interpretation relative to the planning SESOI, not a Gate 0 threshold:

- `BASE_CHARACTER` and `TONE_MARK` retain at least 10 pp downward headroom
  above chance at both their point estimates and interval lower bounds.
- `UPPER_VOWEL_VARIANT` has 13.75 pp point-estimate headroom, but its interval
  lower bound has only 8.75 pp. Adequacy for a 10 pp decline is uncertain.
- `LOWER_VOWEL_VARIANT` and `STACKED_TONE_MARK` have less than 10 pp
  point-estimate headroom before chance. A 10 pp degradation cannot be
  cleanly represented as an above-chance decline under the current baseline.

These statements assess measurement headroom only. They are not thresholds,
compression results, or evidence that a 10 pp effect exists.

### Rendering conditions

Overall condition accuracy was 70.5% (Noto Sans Thai 72), 69.0% (Noto Sans
Thai 96), 70.5% (Noto Serif Thai 72), and 75.0% (Noto Serif Thai 96).

Component-by-condition ranges were:

- `BASE_CHARACTER`: 95.0–100%;
- `TONE_MARK`: 77.5–90.0%;
- `UPPER_VOWEL_VARIANT`: 60.0–67.5%;
- `LOWER_VOWEL_VARIANT`: 47.5–75.0%; and
- `STACKED_TONE_MARK`: 52.5–62.5%.

The 27.5 pp range for `LOWER_VOWEL_VARIANT`, including 75% under Noto Serif
Thai 96, is evidence that rendering/model interaction may matter. It does not
identify the cause.

### Pair heterogeneity and within-pair variation

Pair accuracy ranged from 25–100%, with median 62.5%, IQR 50–87.5%, and SD
19.42 pp across all 100 pairs. Within components, pair-level SD ranged from
9.16–14.32 pp.

However, the current evidence does not show that uncertainty is dominated by
`pair_id` heterogeneity. Displayed-member gaps were 5.0 pp
(`BASE_CHARACTER`), 16.25 pp (`TONE_MARK`), 22.5 pp
(`UPPER_VOWEL_VARIANT`), 38.75 pp (`LOWER_VOWEL_VARIANT`), and 40.0 pp
(`STACKED_TONE_MARK`). Rendering-condition variation is also substantial for
some components. Pair clustering remains required, but the source of
within-pair variation is unresolved.

## 6. Candidate/order and blank controls

- FULL_INFORMATION choice-A rate: 51.75%.
- Accuracy when the correct label was A: 73.0%.
- Accuracy when the correct label was B: 69.5%.
- Absolute correct-label gap: 3.5 pp.
- Blank-control choice-A rate: 85.0%.
- Blank canonical `text_a` preference: 58.0%.
- Blank choice-A rate by component: 100% (`BASE_CHARACTER`), 70%
  (`TONE_MARK`), 92.5% (`UPPER_VOWEL_VARIANT`), 80%
  (`LOWER_VOWEL_VARIANT`), and 82.5% (`STACKED_TONE_MARK`).

The blank results have no visual ground truth. They establish a strong
position preference and a smaller canonical-member preference under no visual
evidence. Balanced ordering limits but does not prove removal of this
confound, especially when component baselines are near chance.

## 7. Token accounting, runtime, and provenance

All 2,040 smoke and calibration calls used 448 x 448 inputs,
`image_grid_thw=[1,32,32]`, 1,024 pre-merge patches, and 256 LLM-boundary
visual positions. No compression was applied.

The repaired exact runs took 300.62 and 300.72 seconds. Median generation was
0.2624 and 0.2623 seconds/call. Peak CUDA allocated was 7.053 GiB, peak CUDA
reserved was 7.090 GiB, and peak process RSS was 6.851–6.868 GiB.

Recorded provenance includes Tesla T4, compute capability 7.5, NVIDIA driver
580.159.04, CUDA 13.0, `torch==2.14.0+cu130`,
`transformers==4.57.6`, `float16`, `sdpa`, model/processor/tokenizer revision,
Git SHA, seed, frozen bundle/allocation hashes, and resolved generation config.

## 8. What the evidence distinguishes

1. **Output/parser limitation:** resolved. Canonical output, exact parsing, and
   rerun reproducibility all passed.
2. **Stimulus/task limitation:** still plausible. Strong displayed-member and
   blank-choice asymmetries may contaminate near-chance categories.
3. **Primary-backbone limitation:** still plausible because only the pinned
   Qwen2.5-VL-3B backbone was evaluated.
4. **Model-by-visual-condition interaction:** supported as a diagnostic
   possibility by the large `LOWER_VOWEL_VARIANT` condition range, but the
   current design does not identify a mechanism.

Low baseline accuracy alone does not establish that the dataset is invalid.
It also does not establish a model limitation or any compression effect.

## 9. Recommendation and mandatory human decision

**Recommendation:** `INVESTIGATE_BASELINE_LIMITATION_USING_CALIBRATION_ONLY_DIAGNOSTICS`.

Do not freeze Gate 0 criteria or open locked validation yet. First determine
whether the low `LOWER_VOWEL_VARIANT` and `STACKED_TONE_MARK` baselines are
mainly associated with member identity, rendering condition, candidate prior,
or the primary backbone. This analysis must use only already exposed
calibration data unless the human separately authorizes a model/backbone
diagnostic.

Gate 0 criteria remain explicitly unapproved. Gate 0 remains `NOT_RUN`, and
Stage 1A, Resolution Reduction, Token Pruning, Token Merging, and every other
compression intervention remain blocked.
