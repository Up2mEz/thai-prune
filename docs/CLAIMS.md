# Claims Registry

> **Phase note (2026-09-27):** the claim-status vocabulary and the
> prohibitions below still bind every report, including the current
> objective. Entries naming specific experiments refer to the completed
> robustness phase unless stated otherwise. Start from `ONBOARDING.md`.

> Purpose: prevent code, reports, slides, and future paper drafts from making claims stronger than the evidence.

Codex must read this file before writing any research summary, result interpretation, abstract, presentation text, or paper-style prose.

---

## Claim levels

### `SUPPORTED`
Directly supported by valid project evidence and approved for use within the stated scope.

### `SUPPORTED_WITH_LIMITS`
Supported only under explicitly stated models, datasets, conditions, or intervention types.

### `HYPOTHESIS`
Scientifically plausible and being tested, but not established by this project.

### `BACKGROUND`
Supported by external literature, not discovered by this project. External citation required.

### `NOT_SUPPORTED`
Must not be presented as a project finding.

---

# Current registry

## SUPPORTED

No unqualified cross-dataset, cross-model, or cross-intervention claim is
supported. The completed main-panel claim is registered below with explicit
scope and limitations.

---

## SUPPORTED_WITH_LIMITS

### Completed Paddle/Wayu MODEL x BUDGET panel

Within the exact pinned PaddleOCR-VL-1.6 / Wayu-Paxa model pair, controlled
synthetic Thai minimal-pair dataset, OCR prompt/parser, four registered budgets,
and BICUBIC Input Resolution Reduction intervention, FULL validity passed and
the registered primary analysis returned
`NO_CONFIRMATORY_MODEL_BUDGET_INTERACTION_EVIDENCE`.

The primary GLMM was unavailable because the registered full `glmer` fit raised
a numerical exception before diagnostics. The already specified pair-clustered
fallback supplied the result after a transparently documented post-data-access
eligibility amendment. Its global p-value was `0.170947`; all three exact DIDs
were Holm-nonsignificant and had observed magnitudes below the 10 pp SESOI.

This supports only the scoped statement that the experiment did not find
confirmatory evidence of different degradation curves under this design. It
does not support equivalence, equal robustness, a causal Wayu-training effect,
component-specific confirmatory effects, general compression robustness,
post-encoder Token Pruning, Token Merging, mechanism, or real-world/cross-model
generalization. See
`stage0/PADDLE_WAYU_LOCKED_MODEL_BUDGET_REPORT.md`.

### Proposed specialization-pair architecture audit

At the pinned public repository revisions recorded on 2026-09-12,
`Qwen/Qwen3-VL-2B-Instruct` and `typhoon-ai/typhoon-ocr1.5-2b` declare the same
`Qwen3VLForConditionalGeneration` architecture/config dimensions, BF16
parameter count, patch size, spatial merge size, DeepStack indexes, and
state-dict key/shape/dtype structure. Typhoon public metadata declares the
Qwen model ID as its fine-tuning base.

This supports only the wording “closely related base and OCR-specialized
descendant.” It does not establish the immutable parent revision, equality of
all non-training conditions, which weights changed, or fine-tuning as the only
causal difference. No model inference was performed. The audit is in
`docs/architecture/QWEN3VL2B_TYPHOON_OCR15_CONFIG_DIFF.json`.

### Step 3 engineering feasibility

The pinned `Qwen/Qwen2.5-VL-3B-Instruct` revision completed the local Step 3
pipeline controls with observable and internally consistent LLM-boundary token
accounting. The two Latin A/B smoke images were human-approved on 2026-09-06.

This supports only an engineering-feasibility statement for the exact model,
revision, environment, config, and smoke controls. It is not Stage 0 evidence,
Thai rendering evidence, compression evidence, or support for H1–H4.

The Kaggle Tesla T4 backend has status
`KAGGLE_BACKEND_FEASIBLE_PROPOSED`; it is not a human-approved scientific gate
or a benchmark claim. Exact evidence and limitations are in
`docs/architecture/KAGGLE_BACKEND.md`.

Kaggle T4 is human-approved for the future Stage 0 calibration workload under
status `KAGGLE_T4_APPROVED_FOR_STAGE0_CALIBRATION`. No Stage 0 model outcome
exists yet, so this remains an execution authorization rather than scientific
evidence.

On 2026-09-06 the exact design advanced to `FROZEN_CALIBRATION`. This permits
only the registered calibration workload. No calibration result, locked
validation result, or Gate 0 conclusion exists until corresponding artifacts
are collected and reviewed.

The frozen calibration workload subsequently completed two exact 1,000-call
runs, but every response failed the registered exact A/B parser. This supports
only the tested claim that the current prompt/parser contract is invalid for
this model configuration. It does not support a visual-accuracy claim, Gate 0,
H1, or any compression claim. Post hoc leading-label summaries are diagnostic
and not Gate 0 evidence. The historical failure class is
`REGISTERED_OUTPUT_PARSER_CONTRACT_FAILURE`; Repair v2 must not rewrite the
old runs or promote their diagnostic accuracy to registered evidence.

Stage 0 Repair v2 subsequently constrained the sole generated token to the
verified canonical A/B token IDs while keeping the exact parser. Its
engineering smoke passed, and two repaired calibration runs reproduced
exactly with zero execution, contract, or parser failures. This supports only
the exact repaired output-contract and calibration evidence reported in
`docs/stage0/CHECKPOINT_C_REPAIRED_INSTRUMENT.md`. It is not locked evidence,
does not approve Gate 0, and provides no compression or H1 evidence.

Checkpoint D analyzed only the first repaired calibration run and used the
second run only to confirm reproducibility. Within this exact synthetic Qwen
calibration, accuracy was strongly associated with canonical member identity,
and some components varied descriptively by font and size. Blank controls
showed strong answer-position preference, but matched blank choices aligned
with 51.74% of full-information errors overall. These findings justify further
measurement diagnostics only. They do not identify a cause, validate all
components, approve Gate 0, or provide compression/H1 evidence. Exact scope
and limitations are in
`docs/stage0/CHECKPOINT_D_CALIBRATION_ONLY_DIAGNOSTICS.md`.

Checkpoint E used one new calibration-only pass over the same already exposed
100 pairs. Under the pinned synthetic Qwen setup, the rendered image shifted
the A/B decision margin toward the displayed correct member on average in all
five components, but the shift was small and strongly member-dependent for
`LOWER_VOWEL_VARIANT` and `STACKED_TONE_MARK`. Matched blank controls retained
a strong displayed-position-A preference, and paired size associations usually
moved in the same direction as binary accuracy. These are secondary,
non-causal measurement diagnostics reported in
`docs/stage0/CHECKPOINT_E_IMAGE_GAIN_DIAGNOSTIC.md`; they do not replace the
registered metric, validate every component, approve Gate 0, establish model
capacity, or support any compression/H1/real-world claim.

The pinned `Qwen/Qwen3.5-4B` revision was evaluated only on the already exposed
100-pair Stage 0 calibration split after a pre-registered selection rationale.
Its T4 FP16 engineering contract passed and two 1,000-observation runs
reproduced exactly, but full-information accuracy was 49.875% with a 100%
blank A-position preference and aggregate image-gain interval crossing zero.
This supports the bounded claim that Qwen3.5-4B is not an adequate measurement
instrument under this exact prompt, parser, rendering, dataset, revision, and
runtime contract. It does not support a general Qwen3.5-versus-Qwen2.5 ranking,
a Thai-language capability claim, a visual-token-count mechanism, Gate 0, or
any claim about Resolution Reduction, Token Pruning, Token Merging, H1–H4, or
real-world text.

The pre-registered Qwen3.5 D1-D4 diagnostic subsequently found very low A/B
content consistency, candidate scores near chance after blank correction,
strong separation in a post-spatial-merger representation probe, and a
positive visual-rescue gain when glyphs were clearly magnified. Under the
frozen classifier these jointly support only an `inconclusive` root-cause
classification and a recommendation to screen an architecturally distinct
backbone. D3 is a diagnostic probe rather than a primary metric, and D4 is a
scale rescue rather than compression evidence. The result does not establish
a purely interface or purely visual cause, does not rank Qwen3.5 against
Qwen2.5 under D1-D4, and does not support Gate 0, H1-H4, real-world Thai OCR,
or any compression claim. Exact estimates, pair-clustered intervals, and
scope are in `docs/stage0/QWEN35_MEASUREMENT_DIAGNOSTIC_REPORT.md`.

The subsequent frozen 25-pair measurement-contract pilot found exact target
accuracy of 0% in both isolated direct transcription and center-target
transcription with artificial surrounding layout. This supports only the
bounded statement that direct transcription did not rescue this exact
Qwen3.5 revision, prompt, rendering, decoding, and open-calibration subset; it
does not establish that the A/B interface is harmless or that visual
representation is absent. Because Condition C crossed the preregistered 20%
output-contract-failure flag, the frozen decision is
`MIXED_TARGETED_INSTRUMENT_REVIEW`. It does not authorize backbone screening,
Gate 0, compression, or a Qwen3.5-versus-Qwen2.5 comparison. Exact evidence is
in `docs/stage0/QWEN35_MEASUREMENT_CONTRACT_PILOT_REPORT.md`.

---

## HYPOTHESES

### Thai-specific OCR adaptation hypothesis — frozen overall design

Thai-specific OCR adaptation may change the degradation curve under decreasing
realized visual-information budgets for the base OCR VLM and its declared
Thai-specialized OCR descendant.
The frozen primary test is a non-directional `MODEL x BUDGET` interaction.
A `MODEL x BUDGET x COMPONENT` interaction is descriptive/diagnostic under the
current dataset and cannot be promoted without a separately powered approval.

**Status:** `NOT_SUPPORTED` as a confirmatory interaction under this exact
design. The one-shot 6,400-call panel completed, FULL validity passed, and the
registered fallback global test was not significant (`p=0.170947`). This does
not disprove the hypothesis and is not evidence of equivalence.

The Typhoon candidate was subsequently set to
`NOT_PURSUED_DUE_TO_USAGE_TERMS`; this is an operational decision, not a
scientific rejection. PaddleOCR-VL-1.6 / Wayu-Paxa completed the accepted
engineering smoke and S0 full-information open-calibration baseline. Those
results remain baseline association evidence, not `MODEL x BUDGET` or
compression evidence.

The observed FULL-validity PASS means only that the overall primary
`MODEL x BUDGET` analysis is measurement-interpretable under the registered
planning criterion. It does not establish measurement capacity for every
component.

The absolute SESOI is 10 percentage points. A non-significant omnibus test is
classified only as `NO_CONFIRMATORY_MODEL_BUDGET_INTERACTION_EVIDENCE`; it is
not equivalence or proof that the models have equal robustness. The three
pair-clustered bootstrap 95% CIs are reported separately and are not described
as Holm-adjusted CIs; Holm multiplicity control applies to p-values.

### Historical H1 — Differential component degradation
Under decreasing visual-token budgets, distinctions involving small Thai orthographic components may degrade differently from other character distinctions.

**Status:** untested and descriptive/diagnostic under the current dataset; not
the active confirmatory primary hypothesis.

**Directionality:** frozen as non-directional on 2026-09-04. The stronger claim
that micro-features degrade more than base-character distinctions is not
registered and must not be treated as confirmatory H1.

### H2 — Size is not necessarily the whole explanation
Any observed component difference may persist after controlling for the size and visual properties of the critical distinguishing evidence.

**Status:** untested.

### H3 — Compression location may matter
Input-resolution reduction and post-encoder token reduction may produce different degradation patterns.

**Status:** untested.

A Resolution Reduction experiment alone does not test H3. Both intervention
families require direct evidence under a fair comparison.

### H4 — Existing OCR/text-aware methods may not fully preserve micro-features
Current OCR-aware or text-aware compression methods may still lose distinction-critical evidence under constrained budgets.

**Status:** untested and particularly time-sensitive; current literature must be checked before Stage 4.

---

## BACKGROUND

The following types of statements may be used only with appropriate external sources:

- VLMs transform images into learned visual representations before language generation.
- Higher processed image resolution can increase the amount of visual computation/representation in dynamic-resolution architectures.
- Visual-token compression is an active efficiency research area.
- OCR/text-rich tasks can be sensitive to loss of fine visual detail.
- Thai writing includes marks and vowel components positioned above and below base characters.

Do not convert background literature into a claim that this project has demonstrated the same effect.

---

## NOT_SUPPORTED

The following claims are currently forbidden:

- "Thai tone marks degrade faster than base consonants under visual-token compression."
- "Thai is inherently more vulnerable to visual-token compression than other writing systems."
- "Token pruning causes Thai OCR errors."
- "The observed problem is caused by loss of a particular individual token."
- "Resolution reduction and visual-token pruning are equivalent interventions."
- "Existing OCR-aware pruning methods fail on Thai micro-features."
- "A new compression method is necessary."
- "The proposed method is better than existing methods."
- "A phenomenon observed in one Qwen model generalizes to all VLMs."
- "Synthetic controlled results demonstrate real-world OCR failure."
- "A statistically significant effect is automatically practically important."
- "Typhoon OCR is more robust than Qwen3-VL under visual-information reduction."
- "OCR specialization improves compression robustness."
- "The BASE and SPECIALIZED models have equivalent or equal robustness."
- "Every true DID is smaller than the 10 pp SESOI."
- "Fine-tuning is the only difference between the proposed checkpoints."
- "OCR specialization causes an attention or representation change."
- "Representation quality explains transcription performance."
- "Thai orthographic components degrade differently under the proposed pivot."
- "The previous Qwen3.5 transcription failure is evidence for a Typhoon specialization effect."
- "PaddleOCR-VL-1.6 and Wayu-Paxa differ only by Thai training data."
- "The audited Paddle/Wayu pair is T4-feasible."
- "Wayu-Paxa is more robust than PaddleOCR-VL-1.6 under visual-information reduction."
- "The Paddle/Wayu source-only audit is Gate 0 or compression evidence."
- "PaddleOCR-VL-1.6 is a general-purpose VLM control against an OCR model."
- "S0 tests the MODEL x BUDGET interaction."
- "The 45,723-page synthetic training set is the only checkpoint difference."
- "The frozen 256/196/121/64 budget grid is Token Pruning."
- "The design freeze authorizes locked validation or Resolution Reduction inference."
- "The experiment has 84-97% power" without stating the registered simulation assumptions.

The following inference is also forbidden:

- "No signal under Resolution Reduction rejects a post-encoder Token Pruning hypothesis."

---

# Thai-marks phase (objective of 2026-09-27)

> **Proposed 2026-10-11 by Up2mEz's session, for the short paper. The
> researcher's approval is the merge of the PR that adds this section.**
> Every entry is `Preliminary/Pilot`: ThaiOCRBench calibration split only
> (Full-page OCR 69 items, Text recognition 109 items, seed 20260927), pinned
> revisions, greedy decoding, Kaggle T4. The locked split is unopened. Several
> remedies were designed after seeing the same split.

## SUPPORTED_WITH_LIMITS (descriptive, calibration split)

Scope for every entry: the exact pinned checkpoints, prompts (`BENCHMARK_QUESTION`
= BQ, `TYPHOON_CARD` = TC), T1 scoring v2 and the order-free v2 mark metric.

1. **Order-free mark metric.** Typhoon OCR 1.5 2B Full-page mark F1 is 94.9 (BQ) /
   95.3 (TC) order-free, against 93.1 / 93.7 with reading order charged. Base
   Qwen3-VL-2B: 41.0 (BQ). `stage0/ORDER_FREE_MARK_METRIC_DRAFT.md` §7.
2. **Mark-specific tone error.** When the base consonant is read correctly,
   Typhoon's tone mark is wrong 0.65% of the time (Full-page, BQ); the base's
   is 9.4%. T1 scoring v2 (`stage0/THAI_MARKS_T1_SCORING_V2.md`) on T1 run
   `a44199c29759`, reproduced in `stage0/MODEL_SURVEY_M1_RESULTS.md` §1–2.
3. **Where Typhoon's Full-page marks go**, as % of all reference marks (BQ / TC):
   read in another order 1.6 / 1.0, whole line absent 2.3 / 2.9, span missing
   0.7 / 0.8, misread 1.5 / 2.4. Automatic attribution, not hand-checked.
   `stage0/TYPHOON_FAILURE_PROFILE.md` §2d.
4. **Tone mark given correct context (T2).** In an in-context forced choice
   with the correct preceding text, Full-page tone accuracy is 99.7% with the
   image and 98.8% without (Typhoon); 98.1% / 98.9% (base). This is not free
   generation. `stage0/THAI_MARKS_T1_T2_RESULTS.md`.
5. **Loops.** On Typhoon, 2–5 looping pages hold 68–76% of all surplus marks.
   `stage0/T5_LOOP_DECODING_DRAFT.md`.
6. **Six checkpoints (M1, M5).** Full-page / Text recognition mark F1: Typhoon
   94.9 / 81.7, Pathumma-llm-vision 3.0 (card prompt) 89.8 / 77.6,
   wayu-paxa-ocr-zero 65.2 / 46.0, PaddleOCR-VL-1.6 53.3 / 47.9, Qwen3-VL-4B
   45.9 / 23.5, Qwen3-VL-2B 41.0 / 24.3.
   - Pathumma minus Typhoon is -5.1 [-14.3, +1.6] and -4.1 [-15.1, +8.0]:
     comparable, neither shown better. Pathumma minus the base is +48.9 and
     +53.3.
   - Models are compared as shipped (unequal visual-token budgets); Paddle
     and Wayu are region recognizers, off-design on Full-page; Pathumma's
     377K training samples are unnamed, so overlap with the benchmark is not
     excluded.
   - `stage0/MODEL_SURVEY_M1_RESULTS.md` §2, `stage0/MODEL_SURVEY_M5_RESULTS.md` §1.
7. **Stop at a detected loop (T5b-B rule, offline cut), six models.**
   - Mark F1 rises in every model on both tasks; no interval lies below 0
     and seven of twelve cells exclude 0. Full-page: Typhoon +0.8
     [0.0, +2.7], Pathumma +3.0, Wayu +10.8 [+5.3, +16.1], Paddle +5.2,
     Qwen3-VL-4B +22.9, base +24.4.
   - Across the twelve cells the cut changed 3 of 898 outputs that had ended
     on their own. Two are Paddle outputs that left a degenerate loop by
     themselves; the cut dropped real page text after it.
   - Recall falls by up to 10.6 points on Full-page, partly credit earned by
     loop copies (see the repeat-aware score) and partly text after the loop.
   - The rule was set after T5, on the same calibration split.
   - `stage0/T5B_STOP_AT_LOOP_DRAFT.md`, `stage0/MODEL_SURVEY_M2_RESULTS.md`,
     `stage0/MODEL_SURVEY_W1_CROSS_MODEL.md` §2, `stage0/MODEL_SURVEY_M5_RESULTS.md` §3.
8. **Repetition penalty 1.1** (the vendor package's setting) changes almost
   every Typhoon output and lowers non-looping Full-page F1 by 1.1–1.3; Text
   recognition (BQ) tone error rises 17.1% → 22.6%.
   `stage0/T5_LOOP_DECODING_DRAFT.md`.
9. **Speculative decoding (S1).** Typhoon 1.14–1.15× faster (prompt lookup),
   output identical except at fp16 near-ties. TC prompt, T4, batch 1 only.
   `stage0/SPEC_DECODE_S1_RESULTS.md`.
10. **Confidence (E1).** Typhoon's own token log-probability separates its
    mark misreads from correct marks: AUROC 0.918 (BQ) / 0.935 (TC).
    `stage0/E1_CONFIDENCE_DRAFT.md`.
11. **Where marks are lost, six models (Full-page, outputs cut at the first
    loop).** Whole lines absent plus spans missing cost 3.2% (Typhoon), 9.3%
    (Pathumma) and 29-44% (the other four) of the reference marks. A wrong
    mark after a correctly read consonant costs 0.4%, 0.8% and 2.7-4.3%. Not
    reading costs 7 to 12 times more than misreading in every model. For
    looping models a line after a loop counts as absent, and the loop is not
    separated from a failure to read. The attribution is automatic.
    `stage0/MODEL_SURVEY_W1_CROSS_MODEL.md` §3, `stage0/MODEL_SURVEY_M5_RESULTS.md` §3.

## HYPOTHESIS (needs more models and/or the locked split)

- The prior is already right for the tone mark given correct context in
  models other than Typhoon and Qwen3-VL-2B (T2 on Pathumma and Qwen3-VL-4B
  not yet run).
- The stop at a loop helps on unseen items (locked split, not opened).
- Decoding that subtracts the language prior costs Thai tone marks in
  general (seen with T2's contrastive rescoring and the project's
  "M3ID-form" contrast, `stage0/REMEDIES_R1_RESULTS.md`).

## Forbidden in this phase

- "Typhoon OCR 1.5 2B is the best open Thai OCR model." Pathumma-llm-vision
  3.0 is comparable on our metric (intervals include 0) and may overlap with
  the benchmark. Allowed: "the strongest measured here, comparable to
  Pathumma".
- "Stopping at a loop is better than repetition penalties / existing
  methods." Not until a registered locked-split result.
- "M3ID", "VCD" or "PAI" results, unqualified. These are the project's
  reimplementations: write "M3ID-form" / "PAI-style".
- "Wayu knows when it is inventing text." M4's AUROC has an unresolved
  confound with forced tokens.
- "OCR specialization makes a model rely more on the image." One base and
  descendant pair (RQ-C) only.
- "Typhoon rarely misreads tone marks", without the scope: ThaiOCRBench
  calibration split, given a correct base consonant.

---

# Scope-safe wording examples

## Before experiments
Use:
> "We investigate whether..."

Do not use:
> "We show that..."

## If an effect is observed only on Qwen + synthetic data
Use:
> "Under the evaluated Qwen model and controlled synthetic conditions, we observe..."

Do not use:
> "VLMs generally..."

## If Stage 2 shows size explains the effect
Use:
> "The apparent component difference is largely explained by properties of the critical visual evidence."

Do not use:
> "Thai orthographic structure causes the failure."

## If existing methods solve the problem
Use:
> "The evaluation indicates that the tested text/OCR-aware method substantially mitigates the observed failure under the evaluated budgets."

Do not invent a new-method motivation that contradicts this result.

---

# Update procedure

After every human-approved gate decision:

1. Add newly supported claims with exact scope.
2. Move disproven hypotheses to `NOT_SUPPORTED` or mark them rejected.
3. Attach run IDs or analysis references.
4. Narrow claims if external-validity tests fail.
5. Never delete an inconvenient historical claim; preserve the change history through Git.

## Evidence-status vocabulary for advisor reporting

- `Tested`: direct valid locked evidence exists within the stated scope.
- `Preliminary/Pilot`: exploratory evidence exists but is not final or gate evidence.
- `Not Tested`: no direct valid experiment exists.
- `Blocked`: a prerequisite or feasibility constraint prevents testing.

Stage 1A Resolution Sensitivity must be `Preliminary/Pilot`. Post-encoder Token
Pruning, H3, real-world Thai OCR, and cross-architecture validity remain
`Not Tested` or `Blocked` until directly evaluated.
