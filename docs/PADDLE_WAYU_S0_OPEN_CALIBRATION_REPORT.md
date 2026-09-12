# Paddle/Wayu S0 Open-Calibration Baseline Report

> Status: `HUMAN_REVIEW_AFTER_S0_OPEN_CALIBRATION`
>
> Recommendation: `BASELINE_CAPACITY_MIXED_CRITERIA_REVIEW_REQUIRED`
>
> Scope: open-calibration, full-information baseline only. This report is not
> evidence about compression, `MODEL x BUDGET`, causality, mechanism, locked
> validation, or a new method.

## 1. Run and protocol identity

- Run ID: `kaggle-paddle-wayu-s0-a7f3eec06bce-832fe44f`
- Frozen source Git SHA: `a7f3eec06bce27bf178cefbe895a8c3ae44de1c3`
- Frozen config SHA-256:
  `832fe44f43e95ba5ba87fb126a560e814c8d002f584c12bd449fd5225564794c`
- Source bundle SHA-256:
  `d865d689f296f4e929c3adce4b2aa75dab56958d9e203ef940a9edbcf54f1992`
- Prompt: exactly `OCR:`; greedy decoding; `max_new_tokens=32`.
- Primary parser: `raw_output.strip()` only; no Unicode normalization,
  autocorrection, punctuation removal, or fuzzy replacement.
- Primary unit: `pair_id`; eight observations per pair/model were averaged
  before inference. CI: paired/pair-clustered percentile bootstrap, 10,000
  resamples, seed `20260912`.

## 2. Exact model/revision manifest

| Role | Checkpoint and resolved revision | Model / processor | `model.safetensors` SHA-256 |
|---|---|---|---|
| BASE | `PaddlePaddle/PaddleOCR-VL-1.6@c5630abae1d940eafe0697512a0325494b02ab42` | `PaddleOCRVLForConditionalGeneration` / `PaddleOCRVLProcessor` | `85a479d506a11e724e7285d395c551be69f41dbc16b6342d3cacfb189aed71db` |
| SPECIALIZED | `wayu-ai/wayu-paxa-ocr-zero@af0204b4f334a6d5068b6bac2b3738932d6e289b` | `PaddleOCRVLForConditionalGeneration` / `PaddleOCRVLProcessor` | `6129b78107aeecdc3a72582a12236cbb05767a6cc00e98bff81e0f3ca5758235` |

Requested and resolved revisions were identical. Full processor/model configs,
individual config hashes, loading information, and weight sizes are preserved
in `model_revision_manifest.json`.

## 3. Exact environment manifest

- Kaggle status: `COMPLETE`; GPU: Tesla T4, 15,360 MiB, compute capability 7.5.
- Python `3.12.13`; PyTorch `2.14.0+cu130`; Transformers `5.12.0`;
  CUDA runtime `13.0`; cuDNN `92400`.
- `cudnn_benchmark=false`; `torch_deterministic_algorithms=false`.
- Decoding was deterministic greedy. S0 did not add repeat calls; exact-repeat
  reproducibility was established only in the accepted engineering smoke.

## 4. Workload and locked-set audit

- 95 open-calibration pairs after excluding the five smoke pairs.
- 19 pairs in each of `BASE_CHARACTER`, `LOWER_VOWEL_VARIANT`,
  `STACKED_TONE_MARK`, `TONE_MARK`, and `UPPER_VOWEL_VARIANT`.
- 2 members x 2 registered fonts x 2 registered sizes x 2 models = 1,520
  successful calls, 760 per model.
- Identical image SHA-256 and input token IDs were verified across models for
  all 760 matched inputs.
- `locked_pair_count = 0`; no replacement was drawn from locked validation.

## 5. Token-accounting audit

All 1,520 calls used `image_grid_thw=[1,32,32]`, 1,024 pre-merge visual
positions, 256 projector outputs, and 256 LLM image placeholders. Input/output
token boundaries were isolated by exact prefix identity. No Resolution
Reduction, Token Pruning, Token Merging, or representation intervention ran.

## 6. Primary exact-transcription results

| Model | Exact accuracy | Pair-clustered 95% CI | Clusters |
|---|---:|---:|---:|
| BASE | 29.74% | 23.29% to 36.71% | 95 |
| SPECIALIZED | 45.53% | 38.68% to 52.50% | 95 |
| `SPECIALIZED - BASE` | +15.79 pp | +9.08 to +22.63 pp | 95 paired |

This is an association on the full-information open-calibration baseline. It
does not establish why the checkpoints differ and does not test robustness to
visual-information reduction.

## 7. Codepoint CER

| Model | Mean codepoint CER | Pair-clustered 95% CI |
|---|---:|---:|
| BASE | 0.5886 | 0.4961 to 0.6866 |
| SPECIALIZED | 0.4143 | 0.3116 to 0.5498 |

CER is secondary and preserves the primary exact parser; it is not used to
replace an exact-match failure.

## 8. Error taxonomy and output behavior

| Category | BASE n (%) | SPECIALIZED n (%) |
|---|---:|---:|
| exact target | 226 (29.74%) | 346 (45.53%) |
| opposite-member substitution | 38 (5.00%) | 50 (6.58%) |
| other Thai substitution | 387 (50.92%) | 359 (47.24%) |
| non-Thai output | 108 (14.21%) | 5 (0.66%) |
| deletion/empty | 0 (0.00%) | 0 (0.00%) |
| output-contract failure | 1 (0.13%) | 0 (0.00%) |

Thai-output rate was 85.66% for BASE and 99.34% for SPECIALIZED. Mean output
length was 2.242 and 2.496 codepoints respectively. NFC secondary exact
accuracy equaled primary exact accuracy for both models, so NFC did not rescue
any primary error.

## 9. Model-by-component calibration descriptives

| Component (19 clusters each) | BASE exact [95% CI] | SPECIALIZED exact [95% CI] |
|---|---:|---:|
| `BASE_CHARACTER` | 58.55% [44.08, 72.37] | 59.87% [49.34, 70.39] |
| `LOWER_VOWEL_VARIANT` | 5.92% [1.32, 11.18] | 28.29% [13.82, 44.08] |
| `STACKED_TONE_MARK` | 13.16% [5.92, 21.07] | 40.79% [23.03, 58.55] |
| `TONE_MARK` | 52.63% [34.87, 69.74] | 56.58% [41.45, 71.05] |
| `UPPER_VOWEL_VARIANT` | 18.42% [9.87, 26.97] | 42.11% [27.63, 55.92] |

The component pattern is calibration-only and has just 19 independent clusters
per cell. It must not be promoted to a final component claim.

## 10. Pair-level variability

BASE pair-mean exact accuracy had quartiles 0%, 0%, 12.5%, 50%, and 100%; 38
of 95 pairs had zero exact outputs and 9 were exact in all eight conditions.
SPECIALIZED quartiles were 0%, 0%, 50%, 75%, and 100%; 25 pairs had zero exact
outputs and 10 were exact in all eight conditions. This heterogeneity is one
reason the recommendation is mixed rather than a simple pass.

## 11. Font/member/size sensitivity

Across the four registered render cells, exact accuracy ranged from 27.89% to
34.74% for BASE and 41.58% to 46.84% for SPECIALIZED. Collapsed font estimates
were Sans 28.16% versus Serif 31.32% for BASE, and Sans 44.21% versus Serif
46.84% for SPECIALIZED. Collapsed size estimates were 72 px 27.89% versus 96 px
31.58% for BASE, and 72 px 46.84% versus 96 px 44.21% for SPECIALIZED.

Member descriptives were `a=33.16%`, `b=26.32%` for BASE and `a=40.00%`,
`b=51.05%` for SPECIALIZED. These are rendering/member sensitivity
descriptives, not independent observations or causal effects.

## 12. Runtime, VRAM, failures, and preservation

| Model | Load | 760-call inference total | Mean/call | Peak allocated | Peak reserved |
|---|---:|---:|---:|---:|---:|
| BASE | 6.931 s | 118.804 s | 0.1563 s | 1,880,104,960 B | 1,946,157,056 B |
| SPECIALIZED | 5.012 s | 119.234 s | 0.1569 s | 1,880,105,472 B | 1,944,059,904 B |

Total remote runtime was 314.142 s. `failure_log.json` is empty. Raw decoded
outputs, parsed outputs, exact targets, opposite members, input/full/generated
token IDs, PNG hashes, workload manifest, model/processor provenance, and
artifact checksums are preserved under
`runs/kaggle/kaggle-paddle-wayu-s0-a7f3eec06bce-832fe44f/`.

## 13. Evidence classification

### FACT

- The frozen 1,520-call workload completed and local artifact verification was
  `VERIFIED`; checksums matched and `locked_pair_count=0`.
- The exact estimates, CIs, taxonomy, token counts, runtime, and VRAM values
  above were calculated from the preserved open-calibration artifacts.
- Several component cells, especially BASE lower/stacked/upper variants, have
  low full-information exact accuracy and substantial pair-level zeros.

### INFERENCE

- Overall baseline capacity is nonzero and leaves observable room for a later
  overall-budget contrast, but component-level measurement capacity is mixed.
- The positive `delta_model` describes an association between the two pinned
  checkpoints under this baseline contract. It is compatible with Thai-specific
  adaptation mattering, but does not identify the training cause.

### UNKNOWN

- Robustness under any reduced visual-information budget is unknown.
- Locked-validation performance, generalization beyond these fonts/sizes,
  causal mechanism, and whether the 45,723-page synthetic set explains the
  checkpoint difference are unknown.
- Power and interpretability of a later `MODEL x BUDGET x COMPONENT`
  interaction remain unestablished for low-capacity component/model cells.

### PROPOSED NEXT CRITERIA — not yet frozen

Using the planning SESOI of 10 percentage points, propose for human review:

1. Overall measurement readiness requires each model's full-information lower
   95% CI to be at least 20% (twice the SESOI) and its point estimate to be no
   more than 80%, preserving both floor separation and downward headroom.
2. A component may enter confirmatory component interaction analysis only if
   each model's component-level lower 95% CI is at least 10% (one SESOI).
   Otherwise that component remains descriptive or requires a separately
   approved measurement redesign.
3. The maximum registered render-cell accuracy range within each model must not
   exceed 10 pp; larger variation requires explicit font/size handling before
   locked inference.
4. Output-contract failure must remain at or below 1%, Thai-output rate at or
   above 80%, visual-token accounting exact on every call, and locked exposure
   exactly zero.

On current S0 estimates, criterion 1 is met by both overall baselines;
criterion 2 is not met by BASE for `LOWER_VOWEL_VARIANT`,
`STACKED_TONE_MARK`, and `UPPER_VOWEL_VARIANT`; criteria 3 and 4 are met. These
criteria are proposals, not authorization, and must be accepted/frozen by the
human reviewer before any locked outcome or budget intervention.

## 14. Recommendation and mandatory stop

`BASELINE_CAPACITY_MIXED_CRITERIA_REVIEW_REQUIRED`

Reason: the overall baseline has measurable signal and acceptable technical
contract behavior, but substantial pair-level zeros and low component cells
make component-level measurement capacity mixed. Do not proceed automatically.

Terminal state: `HUMAN_REVIEW_AFTER_S0_OPEN_CALIBRATION`.
