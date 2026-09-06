# Stage 0 Checkpoint B — Calibration Review

**Status:** `REGISTERED_OUTPUT_PARSER_CONTRACT_FAILURE`
**Gate 0:** `NOT_RUN`
**Locked validation:** `BLOCKED`
**Stage 1A and compression:** `BLOCKED`

## 1. Evidence identity and scope

The authorized Kaggle workload completed two exact calibration runs at 1,000
model calls per run: 800 `FULL_INFORMATION` and 200
`LANGUAGE_CANDIDATE_BIAS_BLANK`. No locked-validation pair was included in the
model-input bundle or observation plans.

| Item | Frozen/observed value |
|---|---|
| Git commit | `8936e9b28d295e1dbfe85d0c6725ef9ae39198bc` |
| Allocation SHA-256 | `385c283091852820016bd6b1247a01af90ee04e966d298761f14cd392b8f47e8` |
| Input bundle SHA-256 | `d865d689f296f4e929c3adce4b2aa75dab56958d9e203ef940a9edbcf54f1992` |
| Calibration evidence SHA-256 | `7d6e3c26ac28f5018c9715329dc4dfda3a54ab8e62ddd179cdc473fbab6bb58a` |
| Model/processor revision | `66285546d2b821cf421d4f5eb2576359d3770cd3` |
| Runtime | Python 3.12.13; `torch==2.14.0+cu130`; `transformers==4.57.6`; CUDA 13.0; `float16`; `sdpa` |
| Decoding/seed | `do_sample=false`; `max_new_tokens=4`; seed `20260906` |

Raw and derived artifacts are under
`runs/kaggle/kaggle-stage0-calibration-8936e9b28d29-ec26b038/`. The derived
`calibration_evidence.json` retains hashes of both manifests, observation
plans, raw predictions, parsed predictions, metrics, and failure logs.

## 2. Observed registered calibration evidence

The exact parser accepts only `^[AB]$`. Qwen returned no exact A/B-only output
in either run. Typical raw outputs were structured as `A. <text>` or
`B. <text>`. Therefore every registered parse failed.

| Registered metric | Exact run 1 | Exact run 2 |
|---|---:|---:|
| Completed calls | 1,000/1,000 | 1,000/1,000 |
| Model execution failures | 0 | 0 |
| FULL_INFORMATION parser failures | 800/800 (100%) | 800/800 (100%) |
| Blank-control parser failures | 200/200 (100%) | 200/200 (100%) |
| FULL_INFORMATION accuracy with parser failures retained as incorrect | 0% | 0% |
| Accuracy conditional on parsed output | undefined | undefined |
| Exact raw-output agreement across reruns | 100% | 100% |
| Parsed/token metadata agreement across reruns | 100% | 100% |

Registered overall, per-component, and per-condition accuracy are all
nominally 0% because parser failures remain in the scored denominator. This is
not evidence that visual discrimination accuracy is 0%; it is evidence that
the registered prompt/parser combination is not a valid measurement
instrument in its current form.

This historical classification is immutable. Repair v2 creates new run IDs;
it does not reinterpret these outputs as registered evidence.

Consequently the following registered quantities are **not estimable**:

- visual accuracy by component or rendering condition;
- A/B candidate-order behavior;
- blank-image candidate/language bias;
- meaningful pair-level heterogeneity or pair-clustered accuracy intervals;
- achieved visual-measurement precision; and
- ceiling/headroom for a later 10 percentage-point effect.

The stored 0-to-0 bootstrap intervals are mechanical consequences of treating
all parser failures as incorrect and must not be presented as achieved
precision.

## 3. Unregistered diagnostic audit

To localize the failure without changing the registered result, a post hoc
read-only diagnostic extracted a leading A/B label with pattern
`^\s*([AB])(?:\.|\s|$)`. This diagnostic is explicitly
`UNREGISTERED_POSTHOC_DIAGNOSTIC_DO_NOT_USE_FOR_GATE0`.

- 1,000/1,000 raw outputs in each run had a leading A/B label;
- 0/1,000 met the registered exact parser;
- 22/1,000 contained only a label plus punctuation such as `A.`;
- 294/1,000 echoed the complete selected candidate exactly; many other echoes
  omitted part of the Thai string;
- every diagnostic value reproduced exactly across the two runs.

If the leading label were accepted, the exploratory full-information summary
would be:

| Component | Diagnostic accuracy | Pair-clustered 95% interval | Pair-level range |
|---|---:|---:|---:|
| `BASE_CHARACTER` | 96.25% | 91.88–99.38% | 62.5–100% |
| `TONE_MARK` | 81.88% | 75.63–88.13% | 62.5–100% |
| `UPPER_VOWEL_VARIANT` | 63.75% | 58.75–68.75% | 50–87.5% |
| `LOWER_VOWEL_VARIANT` | 58.13% | 53.13–62.50% | 25–75% |
| `STACKED_TONE_MARK` | 56.25% | 51.88–61.88% | 37.5–87.5% |
| Overall | 71.25% | 67.50–75.00% | 25–100% |

Exploratory per-condition accuracy was 70.5% (Noto Sans Thai 72), 69.0%
(Noto Sans Thai 96), 70.5% (Noto Serif Thai 72), and 75.0% (Noto Serif Thai
96). Their pair-clustered interval widths were 9.5–10 percentage points.

Pair-level diagnostic heterogeneity was material: median pair accuracy 62.5%,
IQR 50–87.5%, standard deviation 19.42 percentage points, and 22/100 pairs
were perfect. Per-component interval widths were 7.5–12.5 points, equivalent
to half-widths of 3.75–6.25 points. These diagnostics suggest that even after
a parser repair, `UPPER_VOWEL_VARIANT`, `LOWER_VOWEL_VARIANT`, and
`STACKED_TONE_MARK` may have insufficient full-information ceiling. That is a
measurement-validity warning, not a Gate 0 result.

### Candidate/order and blank controls — diagnostic only

- FULL_INFORMATION leading-label choice A rate: 51.75%.
- Diagnostic accuracy when the correct label was A: 73.0%; when B: 69.5%;
  absolute gap 3.5 points.
- Blank-control leading-label choice A rate: 85.0%.
- Blank-control canonical `text_a` choice: 58.0% overall.
- Blank A-choice rates by component were 100% (`BASE_CHARACTER`), 70%
  (`TONE_MARK`), 92.5% (`UPPER_VOWEL_VARIANT`), 80%
  (`LOWER_VOWEL_VARIANT`), and 82.5% (`STACKED_TONE_MARK`).

The blank results indicate a strong candidate-position preference under the
diagnostic parser. They have no visual ground truth and are not visual
accuracy samples.

## 4. Token accounting and resources

All 2,000 calls recorded:

- original and preprocessed shape `448 x 448`;
- `image_grid_thw = [1, 32, 32]`;
- 1,024 pre-merge patches;
- 256 LLM-boundary visual positions from the grid formula;
- 256 processor image-token positions; and
- 256 runtime Vision Encoder output positions.

There was no compression intervention. Actual visual-token count was 256 for
every full-information and blank-control call.

| Resource metric | Exact run 1 | Exact run 2 |
|---|---:|---:|
| Model load | 44.95 s | 6.71 s |
| Median preprocessing/call | 0.0129 s | 0.0132 s |
| Median generation/call | 0.3954 s | 0.4014 s |
| Total run time | 473.74 s | 427.59 s |
| Peak CUDA allocated | 7.053 GiB | 7.053 GiB |
| Peak CUDA reserved | 7.090 GiB | 7.090 GiB |
| Peak process RSS | 5.937 GiB | 6.213 GiB |

## 5. Execution failures and warnings

1. Kernel version 1 failed before model inference because Windows CRLF and
   Linux LF produced different raw hashes for `uv.lock`. The failed artifact
   is retained; `.gitattributes` now pins `uv.lock` to LF.
2. Kernel version 2 completed both exact model runs, with zero call-level
   execution failures, but its submission-level validator ended in `ERROR`
   after inference. The validator compared in-memory integer token-count keys
   with JSON string keys. Local recomputation confirmed this serialization
   mismatch as the validator failure; prediction metadata itself matched the
   frozen 256-token contract. The verifier was repaired after evidence
   collection without rerunning or altering raw results.
3. Because submission finalization stopped at this validation error, a top-level
   `SUCCESS.json` and persisted `gpu_preflight` record were not produced.
   T4-class verification had to pass before either model run could start, but
   this run does not retain the current GPU name/driver record. The per-run
   software, CUDA, memory, model, processor, and architecture records are
   complete.

## 6. Interpretation

**Observed:** the exact workload and token accounting executed reproducibly,
but the registered parser failed systematically and blank controls show a
large exploratory A-position preference.

**Interpretation:** the current Stage 0 task/prompt/parser combination is not
a valid measurement instrument. A parser or decoding repair is necessary,
and the same calibration pairs should be reused so no locked pair is exposed.
The exploratory low ceiling in three component categories may remain a
separate problem after parser repair.

**Not established:** no valid visual-accuracy estimate, no Gate 0 result, no
evidence about Resolution Reduction, no post-encoder Token Pruning evidence,
and no support or rejection of H1.

## 7. Proposed numeric Gate 0 criteria — not frozen

These criteria are proposed from the 10 percentage-point planning SESOI and
the observed failure modes. They are not universal defaults and require human
approval before any locked validation.

| Criterion | Proposed numeric rule | Justification |
|---|---|---|
| Parser contamination | Pair-clustered 95% upper bound on parser-failure rate <= 5% overall and in every component | Limits format-related contamination to at most half the 10-point SESOI |
| Full-information discrimination | In every component, point accuracy >= 70% and pair-clustered 95% lower bound > 50% | 70% is two SESOIs above binary chance; a 10-point decline would retain one SESOI of separation from chance |
| Baseline precision | Pair-clustered 95% half-width <= 5 percentage points in every component | Measurement uncertainty should be no larger than half the planning SESOI |
| Correct-label order sensitivity | Absolute A-versus-B accuracy gap <= 5 points | Caps order-related distortion at half the planning SESOI |
| Blank A-position preference | Leading/registered A-choice rate between 45% and 55% after both orientations are balanced | A position bias larger than half the SESOI could mimic a meaningful difference |
| Exact-rerun stability | Parsed-choice agreement >= 95%; visual-token-count agreement = 100% | Limits nondeterministic outcome noise to half the SESOI while requiring exact accounting |
| Execution integrity | 100% authorized calls completed, 0 execution failures, 0 locked pairs exposed, and 100% token metadata matches the frozen contract | A gate run with missing observations or provenance mismatch is not interpretable |

The canonical-member preference in blank controls should remain a reported
diagnostic. If its absolute deviation from 50% exceeds 10 points in any
component, the Gate 0 outcome should be `INCONCLUSIVE` unless a preregistered
paired analysis demonstrates that this prior cannot explain the visual result.

## 8. Unresolved human decisions

Before any further model call, the human researcher must decide:

1. whether to repair decoding (for example a one-token generation contract),
   repair parsing with a narrowly defined leading-label grammar, revise the
   prompt, or stop this instrument;
2. whether to approve the proposed Gate 0 criteria or revise their rationale;
3. whether to authorize one repaired calibration using only the already
   exposed 100 calibration pairs and the same four rendering conditions;
4. whether a strong blank-position preference requires a task redesign before
   recalibration; and
5. whether low exploratory ceiling in three categories should trigger a
   measurement-design pivot if it persists after the parser/decoding repair.

No locked-validation run should begin from the current calibration.
