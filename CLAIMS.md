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

None yet.

---

## HYPOTHESES

### H1 — Differential component degradation
Under decreasing visual-token budgets, distinctions involving small Thai orthographic components may degrade differently from other character distinctions.

**Status:** untested.

### H2 — Size is not necessarily the whole explanation
Any observed component difference may persist after controlling for the size and visual properties of the critical distinguishing evidence.

**Status:** untested.

### H3 — Compression location may matter
Input-resolution reduction and post-encoder token reduction may produce different degradation patterns.

**Status:** untested.

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
