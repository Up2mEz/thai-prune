# Overall MODEL x BUDGET Design Freeze

> Status: `OVERALL_MODEL_BUDGET_DESIGN_FROZEN_PENDING_LOCKED_AUTHORIZATION`
>
> Freeze date: 2026-09-13
>
> Documentation and processor-geometry analysis only. No model inference,
> locked-validation access, Resolution Reduction inference, Token Pruning,
> Token Merging, fine-tuning, or method development occurred.

## 1. Frozen scientific question

> Does Thai-specific OCR adaptation change the degradation curve under
> controlled visual-information reduction?

The confirmatory effect is the non-directional `MODEL x BUDGET` interaction:
whether change from FULL to reduced visual-information budgets differs between
the BASE and SPECIALIZED checkpoints. No direction and no robustness advantage
is assumed.

- BASE: `PaddlePaddle/PaddleOCR-VL-1.6@c5630abae1d940eafe0697512a0325494b02ab42`
- SPECIALIZED: `wayu-ai/wayu-paxa-ocr-zero@af0204b4f334a6d5068b6bac2b3738932d6e289b`
- Primary outcome: exact target transcription correctness under the frozen
  exact-codepoint parser.
- Primary experimental unit: `pair_id`. Pair members, fonts, font sizes,
  budgets, and models are repeated observations within a pair, not independent
  samples.

All five components remain in the dataset. `MODEL x BUDGET x COMPONENT` and
within-component curves are `DESCRIPTIVE / DIAGNOSTIC`, not confirmatory, under
the current 19-cluster-per-component design.

## 2. Frozen primary analysis specification

The observation-level binary outcome is modeled using mixed-effects logistic
regression:

```text
exact_correct ~ MODEL * BUDGET
              + FONT + FONT_SIZE + MEMBER + COMPONENT
              + (1 | pair_id)
```

- `MODEL`: categorical; BASE reference.
- `BUDGET`: categorical by actual LLM image-placeholder count; `B256_FULL`
  reference. It is not a nominal percentage covariate.
- `FONT`, `FONT_SIZE`, `MEMBER`, and `COMPONENT`: nuisance/main-effect
  adjustments. Component is justified by the heterogeneous S0 baselines; no
  confirmatory component interaction is included.
- Primary confirmatory test: two-sided joint 3-df test that all reduced-budget
  `MODEL x BUDGET` coefficients are zero, alpha 0.05.
- Budget-specific reduced-versus-FULL contrasts use Holm correction across the
  three contrasts when making inferential claims.

The log-odds interaction is not the user-facing effect size. For every reduced
budget, marginal predictions/g-computation over the frozen pair/render
distribution report:

```text
[SPECIALIZED(reduced) - SPECIALIZED(FULL)]
  - [BASE(reduced) - BASE(FULL)]
```

Report this Difference-in-Differences in percentage points with a 10,000-
resample `pair_id` cluster-bootstrap percentile 95% CI, seed `20260913`.
Report model-specific changes from each model's own FULL baseline as well.

Primary sensitivity analysis aggregates within each
`MODEL x BUDGET x pair_id` cell and pair-bootstraps the model-specific changes
and their Difference-in-Differences. Codepoint CER is a secondary sensitivity
metric; it does not replace the exact-transcription primary outcome.

All registered observations remain in analysis. Contract failures and empty
outputs score incorrect. There is no post-outcome replacement/exclusion. If the
primary mixed model is non-convergent or singular under the frozen fit checks,
record `PRIMARY_MODEL_NOT_ESTIMABLE` and stop for review; do not promote a
sensitivity result to primary after seeing outcomes.

## 3. Frozen Gate-0 measurement-validity criteria

Gate-0 FULL measurement validity requires:

1. Each model's lower pair-clustered 95% CI for overall exact transcription
   accuracy is at least 20%. This is `2 x` the 10 pp SESOI from the zero floor.
2. Output-contract failure is at most 1% separately in each model.
3. Visual-token accounting is exact on every call.
4. No model/processor identity mismatch, input/hash mismatch, generation
   boundary failure, Unicode/parser corruption, NaN/Inf, or unexplained runtime
   corruption occurs.
5. Unauthorized or out-of-workload locked-pair count is zero.

There is no requirement that baseline accuracy be at most 80%. Thai-output rate
is diagnostic only. Paired font/size contrasts and pair-clustered CIs are
reported and the future model adjusts for both factors; no raw render-cell range
threshold is a hard gate. Component headroom remains diagnostic and does not
block the overall experiment when overall Gate-0 criteria pass.

An authorized locked Gate-0 workload intentionally contains the 100 registered
locked pairs. Its manifest must distinguish
`registered_locked_pair_count=100` from
`unauthorized_or_out_of_workload_locked_pair_count=0`; the legacy unqualified
`locked_pair_count` must not be used for this run.

## 4. Processor-only candidate resolution mapping

Both pinned processors were loaded without model weights using Transformers
`5.12.0`. Their geometry matched: `patch_size=14`, `merge_size=2`, temporal grid
1, and `image_token_id=100295`. A blank, non-dataset 448x448 image was passed
through the PIL processor backend with `min_pixels=max_pixels=target²`.
The measured `image_grid_thw`, flattened patch count, and tokenizer placeholder
count matched the source-derived geometry for both processors.

Reproduction command (processor-only; no model weights):

```powershell
uv run --with transformers==5.12.0 --with pillow --with numpy python scripts/probe_paddle_wayu_processor_geometry.py --output <new-output.json>
```

| Processor target | `image_grid_thw` | Pre-merge patches | Projector / actual LLM placeholders | Fraction of FULL |
|---:|---:|---:|---:|---:|
| 448x448 | `[1,32,32]` | 1,024 | 256 | 100.00% |
| 420x420 | `[1,30,30]` | 900 | 225 | 87.89% |
| 392x392 | `[1,28,28]` | 784 | 196 | 76.56% |
| 364x364 | `[1,26,26]` | 676 | 169 | 66.02% |
| 336x336 | `[1,24,24]` | 576 | 144 | 56.25% |
| 308x308 | `[1,22,22]` | 484 | 121 | 47.27% |
| 280x280 | `[1,20,20]` | 400 | 100 | 39.06% |
| 252x252 | `[1,18,18]` | 324 | 81 | 31.64% |
| 224x224 | `[1,16,16]` | 256 | 64 | 25.00% |

The processor's default minimum area is 112,896 pixels (336²). Therefore a
small source image alone could be upscaled to 336x336. Every frozen condition
must pass equal `min_pixels` and `max_pixels` explicitly so the realized target
cannot drift. The original registered 448x448 PNG remains the source; the
processor performs the frozen BICUBIC resize.

## 5. Frozen future budget grid

| Budget ID | Target | Actual LLM positions | FULL fraction | Role |
|---|---:|---:|---:|---|
| `B256_FULL` | 448x448 | 256 | 100.00% | FULL reference |
| `B196` | 392x392 | 196 | 76.56% | high retained budget |
| `B121` | 308x308 | 121 | 47.27% | middle retained budget |
| `B64` | 224x224 | 64 | 25.00% | low retained budget |

These are the lattice-realizable points closest to the desired small monotonic
FULL/~75%/~50%/~25% span. Scientific records and analysis use actual positions
`256/196/121/64`, not the approximate labels. Selection used only processor
geometry, dynamic-range coverage, and the already established T4 feasibility;
no model accuracy at a reduced resolution exists or was used.

This intervention family is **Input Resolution Reduction**. It changes the
image before the Vision Encoder. It is not Pre-encoder token selection,
post-encoder Token Pruning, Token Merging/Pooling, or dynamic decoding-time
token access. Evidence must remain mechanism-specific.

## 6. Locked-validation protocol and reuse governance

The Gate-0 locked FULL protocol is prepared in
`docs/stage0/PADDLE_WAYU_GATE0_LOCKED_PROTOCOL.md` but remains unauthorized and
unrun. It uses exactly the previously frozen 100 locked `pair_id` values, two
members, two registered fonts, two sizes, two models, and FULL only: 1,600
calls. No locked bundle was materialized or inspected in this task.

The same 100 locked pairs are intended for the later four-budget registered
panel. Consequently, the complete 6,400-call grid, primary analysis, metrics,
and exclusions are frozen now—before the first locked FULL output. If Gate 0 is
later human-approved, the remaining three budgets account for 4,800 calls. The
locked baseline cannot be used to tune the grid or analysis.

If this same-panel reuse guarantee cannot be enforced, stop before locked
inference and adopt a new human-approved data split/protocol.

## 7. Simulation interpretation

Allowed planning statement: under the registered simulation assumptions, the
95-cluster design showed approximately 84–97% probability of detecting a 10 pp
differential degradation in moderate-effect scenarios. This is not an
unconditional power claim and is not empirical compression evidence. Component
simulations of approximately 34–56% support keeping component analyses
descriptive under the present design.

## 8. Claims and authorization boundary

This freeze establishes a question, estimand, analysis, Gate-0 criteria,
processor-realizable budget grid, exclusions, and locked-data governance. It
does not establish compression robustness, specialization-induced robustness,
an observed `MODEL x BUDGET` interaction, component degradation, causal effects
of Thai training, or a need for a new method.

No locked inference or Resolution Reduction inference is authorized. Terminal
state: `OVERALL_MODEL_BUDGET_DESIGN_FROZEN_PENDING_LOCKED_AUTHORIZATION`.
