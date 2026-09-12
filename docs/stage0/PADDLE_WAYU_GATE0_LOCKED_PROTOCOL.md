# Paddle/Wayu One-Shot Locked Confirmatory Panel Protocol

> Status: `FINAL_LOCKED_PANEL_AUTHORIZATION_READY`
>
> Execution: `NOT_RUN`
>
> The historical filename is retained for stable references. Gate-0 is no
> longer a staged execution. It is the FULL-validity condition evaluated only
> after the complete one-shot panel is immutable.

No locked image bundle was built, inspected, or sent to a processor/model while
preparing this amendment.

## One-shot execution contract

The only registered locked workload is:

`100 pair_id x 2 members x 2 fonts x 2 sizes x 2 models x 4 budgets = 6,400 calls`.

The four categorical budgets are the actual LLM image-position counts
`256/196/121/64`, mapped to processor inputs `448/392/308/224`. Every registered
cell must be materialized and executed in the same run. There is no 1,600-call
FULL-only run and no conditional 4,800-call continuation.

The runner may stop only for a fail-closed engineering corruption. During the
one-shot run it must not display or inspect scientific predictions, accuracy,
CER, DID values, per-model summaries, component outcomes, or FULL-validity
results. Runtime output is restricted to completed call count, execution
failure codes without prediction content, GPU/runtime status, and token-
accounting validation. Raw scientific records are append-only sealed evidence,
not an intermediate display or analysis.

Scientific output may be unsealed only after all three conditions hold:

1. all 6,400 registered calls completed;
2. artifacts and checksums are immutable;
3. local artifact verification passes.

After sealing:

1. evaluate the registered FULL-validity criteria using only `B256_FULL`;
2. if FULL validity fails, label the primary `MODEL x BUDGET` analysis
   `NOT_INTERPRETABLE_FULL_VALIDITY_FAILED` and do not promote reduced-budget
   results to scientific claims;
3. if FULL validity passes, run the frozen primary analysis without changing
   pairs, budgets, metrics, exclusions, model structure, or multiplicity.

## Immutable stimulus and INPUT RESOLUTION REDUCTION pipeline

The registered 448x448 RGB PNG is the immutable source for all four budgets.
`B256_FULL` uses byte-identical source PNG bytes. Reduced PNGs are produced once
from that exact source; text is never re-rendered at a lower size.

- library: `Pillow==12.3.0`;
- function: `PIL.Image.Image.resize`;
- exact call: `source.resize((width, height), Image.Resampling.BICUBIC, reducing_gap=None)`;
- interpolation/antialias: `BICUBIC`; Pillow has no separate antialias boolean
  for this call, so the registered antialias behavior is the one-step BICUBIC
  kernel with `reducing_gap=None`;
- dimensions: exact integer square sizes; no aspect-ratio calculation or
  coordinate rounding;
- mode: input must already be `RGB`; output remains 8-bit `RGB`;
- PNG encoding: Pillow PNG writer, `optimize=False`, `compress_level=9`, no
  metadata written for reduced images;
- forbidden: sharpening, thresholding, OCR-specific preprocessing, EXIF
  rotation, adaptive sizing, or any per-image parameter change.

Before model loading, a stimulus manifest must record SHA-256 hashes of every
source file, source RGB pixel buffer, output file, and output RGB pixel buffer.
The runtime must verify exact dimensions and the expected processor accounting:

| Input | `image_grid_thw` | Pre-merge | Actual LLM positions |
|---:|---:|---:|---:|
| 448x448 | `[1,32,32]` | 1,024 | 256 |
| 392x392 | `[1,28,28]` | 784 | 196 |
| 308x308 | `[1,22,22]` | 484 | 121 |
| 224x224 | `[1,16,16]` | 256 | 64 |

Processor calls must pass `min_pixels=max_pixels=width*height`. The intervention
is named **INPUT RESOLUTION REDUCTION**. The study does not identify visual-token
count alone as the cause because image sampling changes before the Vision Encoder.

## FULL-validity condition

PASS means only:

> overall primary `MODEL x BUDGET` analysis is measurement-interpretable under
> the registered planning criterion.

It requires all of the following on `B256_FULL`:

1. each model's lower pair-clustered percentile 95% CI for overall exact
   accuracy is at least 20%;
2. output-contract failure is at most 1% separately for each model;
3. exact visual-token accounting on every call;
4. no model/processor/input/generation-boundary mismatch, Unicode/parser
   corruption, NaN/Inf, or unexplained runtime corruption;
5. `unauthorized_or_out_of_workload_locked_pair_count=0`.

The authorized panel intentionally contains
`registered_locked_pair_count=100`. The legacy phrase `locked_pair_count=0`
means zero unauthorized or out-of-workload locked pairs and must be emitted
with the qualified field name above.

There is no upper-baseline gate. Thai-output rate and paired font/size effects
are diagnostic. PASS is not evidence that all five orthographic components
have valid measurement capacity. Component curves remain descriptive and no
pair may be removed based on S0 or locked difficulty.

## Analysis and estimator failure

The exact primary and fallback procedures are frozen in
`docs/stage0/PADDLE_WAYU_PRIMARY_ANALYSIS_SPEC.md`. The selected target-aware
random structure is `(1 | pair_id) + (1 | pair_id:member)`. `pair_id` remains
the top-level bootstrap/resampling unit.

No post-outcome exclusion, replacement, parser repair, per-example retry, or
silent estimator switch is allowed. A partial or corrupt run is preserved with
a failure manifest and is not a valid panel.

Terminal state: `FINAL_LOCKED_PANEL_AUTHORIZATION_READY`.
