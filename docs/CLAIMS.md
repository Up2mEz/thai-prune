# Claims Registry

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

None yet. No main experiment has been completed.

---

## SUPPORTED_WITH_LIMITS

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

### Proposed specialization hypothesis — model-agnostic; fallback pending

OCR specialization may change the degradation curve under decreasing realized
visual-information budgets for a sufficiently matched base/descendant pair.
The primary proposed test is a non-directional `MODEL x BUDGET` interaction.
A `MODEL x BUDGET x COMPONENT` interaction is secondary/descriptive unless S0
establishes adequate component-level measurement capacity.

**Status:** `APPROVED_FOR_ENGINEERING_SMOKE_ONLY`; untested and not an active
registered hypothesis. Stage S0 remains unauthorized.

The Typhoon candidate was subsequently set to
`NOT_PURSUED_DUE_TO_USAGE_TERMS`; this is an operational decision, not a
scientific rejection. The model-agnostic hypothesis remains proposed. The
PaddleOCR-VL-1.6 / Wayu-Paxa fallback is approved only for the exact
non-scientific 40-call engineering smoke and has no scientific outcome
evidence.

### H1 — Differential component degradation
Under decreasing visual-token budgets, distinctions involving small Thai orthographic components may degrade differently from other character distinctions.

**Status:** untested.

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
- "Fine-tuning is the only difference between the proposed checkpoints."
- "OCR specialization causes an attention or representation change."
- "Representation quality explains transcription performance."
- "Thai orthographic components degrade differently under the proposed pivot."
- "The previous Qwen3.5 transcription failure is evidence for a Typhoon specialization effect."
- "PaddleOCR-VL-1.6 and Wayu-Paxa differ only by Thai training data."
- "The audited Paddle/Wayu pair is T4-feasible."
- "Wayu-Paxa is more robust than PaddleOCR-VL-1.6 under visual-information reduction."
- "The Paddle/Wayu source-only audit is Gate 0 or compression evidence."

The following inference is also forbidden:

- "No signal under Resolution Reduction rejects a post-encoder Token Pruning hypothesis."

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
