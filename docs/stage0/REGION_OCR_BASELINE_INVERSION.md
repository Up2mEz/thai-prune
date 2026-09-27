# Region OCR — the FULL condition is not the best condition

> Status: `ENGINEERING_DIAGNOSTIC_FROM_A_PARTIALLY_FAILED_RUN`
>
> Source: `kaggle-region-ocr-a2619bbc8767`, whose FULL and Resolution Reduction
> arms completed (1,600 observations, accounting verified on every one) while all
> 3,600 pruning observations failed on a device-placement bug.
>
> This is not a registered result. It is a measurement-validity observation that
> changes how the pending run must be read.

## What was observed

Absolute CER by condition, over 400 regions:

| Condition | LLM positions (median) | macro CER | micro CER |
|---|---:|---:|---:|
| `FULL` | 160 | 0.2721 | 0.1934 |
| `RR_75` | 120 | 0.2573 | 0.1801 |
| `RR_50` | 80 | **0.2230** | **0.1536** |
| `RR_25` | 40 | **0.1964** | 0.1590 |

Recognition **improves** as the visual-token budget falls.

## This is not an aggregation artifact

Checked two ways before interpreting it:

1. **The reduction is real.** Every one of the 1,600 observations delivered
   exactly the registered number of visual positions to the language model:
   160 → 120 → 80 → 40, with per-observation agreement between the achieved and
   expected counts.
2. **It holds region by region.** Comparing exact-match against `FULL` within
   each region rather than across aggregates:

| Condition | regions improved | regions worsened | unchanged |
|---|---:|---:|---:|
| `RR_75` | 20 | 13 | 367 |
| `RR_50` | 31 | 22 | 347 |
| `RR_25` | 41 | 29 | 330 |

More regions improve than degrade at every budget.

## Why this is the expected consequence of the corpus

TEMS crops are small: median 262 × 49 px, about 11 visual tokens at native
resolution. The processor's `min_pixels` floor upsamples them roughly fourfold
in each dimension to reach its ~160-token operating point. That upsampling adds
no information; it adds interpolation. Forcing a lower pixel budget moves the
image back toward its native resolution and removes some of that damage.

The dataset audit already recorded that most visual tokens here are interpolated
redundancy and warned that this biases the design toward finding compression
harmless. The measured effect is stronger than the warning: the redundancy is
not merely uninformative, it is actively harmful, so removing it helps.

## What this changes

- **`FULL` is a degraded baseline, not a ceiling.** The design's framing of
  "degradation curves from full information" does not describe this corpus.
- **`ΔCER` against `FULL` will be negative for Resolution Reduction.** The
  registered DiD stays well defined — it contrasts pruning against resolution
  reduction on the same regions at matched token counts — but its two arms are
  no longer "how much each degrades". One of them improves.
- **A pruning-versus-RR difference could arise from RR helping rather than
  pruning hurting.** Any reading of the pending result must say which.

## What is deliberately not being done

The protocol is not being changed in response to this. Altering the baseline,
the budgets, or the estimand after seeing outcomes is exactly the post-outcome
redesign the branch forbids. This document records the observation so the
pending run is interpreted correctly, and leaves any design decision to the
human researcher.

A defensible follow-up, if one is wanted later, is a pre-registered condition at
or near the native resolution of each crop, which would establish whether an
undegraded baseline exists at all for this corpus. That is a new registration,
not an amendment to this one.
