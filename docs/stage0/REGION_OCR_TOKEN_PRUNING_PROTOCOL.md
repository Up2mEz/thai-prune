# Region OCR — Post-encoder Token Pruning vs Input Resolution Reduction Protocol

> Status: `DRAFT_PENDING_HUMAN_AUTHORIZATION`
>
> Authorization: **NONE**. No Decision Log entry authorizes this branch yet.
>
> Inference performed while preparing this document: **NONE**. No model was
> loaded, no dataset was downloaded, no processor was called, no stimulus was
> materialized.
>
> Gate 0: `NOT_RUN`. This branch does not evaluate, approve, or reject Gate 0.

This protocol must be frozen and committed **before** any inference. It is a
proposal authored by the agent; only the human researcher may authorize it.

---

## 1. Question

Within one experiment, on the same stimuli, the same models, the same prompt,
and matched actual visual-token counts:

> Does **post-encoder Token Pruning** produce a different Thai text-region
> recognition degradation pattern than **Input Resolution Reduction**?

This is a direct test of the intervention-family contrast in H3. It is **not**
a comparison against the completed Resolution-Reduction panel
(`kaggle-paddle-wayu-locked-panel-attempt5`, Wald 5.011636, df 3,
p 0.170947). Comparing a "significant" result in one experiment against a
"non-significant" result in another is not evidence that the two differ; the
contrast must be estimated inside a single design, which is why Resolution
Reduction is re-run here rather than imported.

## 2. Evidence status of whatever this produces

`Preliminary/Pilot`.

The dataset is new, no sealed confirmatory split exists, and the model set is
narrow. This branch therefore **cannot**:

- approve, reject, or inform Gate 0 or Gate 1;
- confirm or reject H1, H2, H3, or H4;
- support any claim that a new compression method is needed or better;
- support any claim about Thai vulnerability relative to other scripts;
- generalize beyond the exact models, revisions, stimuli, and budgets tested.

Claim scope is **text-region recognition on Thai document images**, not
end-to-end document OCR.

## 3. Models

| Role | Model | Revision |
|---|---|---|
| BASE | `PaddlePaddle/PaddleOCR-VL-1.6` | `c5630abae1d940eafe0697512a0325494b02ab42` |
| SPECIALIZED | `wayu-ai/wayu-paxa-ocr-zero` | `af0204b4f334a6d5068b6bac2b3738932d6e289b` |

Both are Apache-2.0-rooted and classified `TERMS_CLEAR` in
`docs/FALLBACK_PAIR_CLEARANCE.md`, which records that the Wayu Acceptable Use
terms "contain no clause requiring prior consent for comparative or competitive
benchmarking" and that Token Pruning experiments are not prohibited. The same
document requires a **re-snapshot and hash of the model cards, licenses, and
Wayu Terms before any authorized run**, because the Wayu terms may change. That
re-snapshot is a precondition of execution and is recorded in
`docs/stage0/PAGE_OCR_MODEL_CLEARANCE.md`.

When publishing, the only Wayu clause that constrains wording is the
false-affiliation/endorsement prohibition: results must not imply that Wayu
Research endorses this work.

SPECIALIZED is a Thai-specialized full finetune of BASE, so the two share
identical processor geometry. This is a property of the pair, not an assumption:
`docs/stage0/PADDLE_WAYU_PROCESSOR_GEOMETRY.json` records
`patch_size 14`, `merge_size 2`, `image_token_id 100295`, and
`all_processors_identical_geometry: true`.

Both are **region recognizers, not full-page readers**. They are used here as
designed. No layout-detection stage is introduced.

## 4. Unit of analysis

- **observation** = one text region under one condition.
- **independent unit / resampling cluster** = `source_page_id`.

Multiple regions cropped from the same source page are repeated observations of
that page, not independent samples. This mirrors the existing `pair_id`
discipline and must be preserved by every uncertainty estimate.

Rationale for measuring at the region rather than the page: the intervention
acts inside a single VLM forward pass, and in this model family one region is
one such pass. A layout-detector stage would be unaffected by pruning, so a
page-level score would equal `f(layout error, VLM error)` while the intervention
moves only the second term — diluting the estimand and adding variance without
adding information.

## 5. Conditions and the budget-matching rule

Input Resolution Reduction cannot hit an arbitrary token count because the grid
is quantized by `patch 14 -> merge 2`. Budgets are therefore matched
**per region**, not globally:

```
for each region:
  FULL     -> record actual LLM image-placeholder count N from the processor
  RR       -> resize so the placeholder count lands as close as possible to
              0.75N / 0.50N / 0.25N; record the ACTUAL achieved counts K1,K2,K3
  PRUNING  -> remove post-encoder tokens so exactly K1, K2, K3 remain
```

Pruning is matched to the actual counts RR achieved, so both families deliver
an identical number of visual positions to the language model for that region.

| Condition | Budget | Notes |
|---|---|---|
| `FULL` | N | baseline |
| `RR_75` / `RR_50` / `RR_25` | K1 / K2 / K3 | Pillow BICUBIC, deterministic, hashed |
| `PRUNE_RANDOM` x 2 seeds | K1 / K2 / K3 | both seeds reported; selecting the better seed is forbidden |
| `PRUNE_GRID` | K1 / K2 / K3 | uniform stride preserving spatial coverage |

`Random` is a first-class baseline, not a straw man. Recent work reports that
sophisticated pruning does not reliably beat simple baselines, so a method that
fails to beat `Random` must be visible.

### 5.1 Interpretation boundary of the matching

Matching the **final** token count does not match the information that reached
the Vision Encoder. Resolution Reduction discards evidence *before* encoding;
Token Pruning discards representations *after* the encoder has seen the full
image. That asymmetry is the object of study, not a defect — but it must be
stated wherever the contrast is reported.

Consequently, **post-encoder pruning does not reduce Vision Encoder cost**. Any
efficiency statement must come from measured end-to-end latency and peak VRAM,
never inferred from token counts.

## 6. Output contract

- prompt: single frozen prompt, identical across every condition and model.
- decoding: `do_sample=false`, `num_beams=1`, deterministic, seed recorded.
- `max_new_tokens`: frozen before the scientific run, chosen from the
  engineering smoke by region-length headroom and machine capability, **never
  from observed accuracy**.
- parser: strip leading/trailing whitespace only. Internal whitespace is
  **legal** text content and must not be classified as a contract failure. The
  existing `classify_output` short-string contract is not reused.
- Unicode normalization: **none** in the primary metric. An NFC variant is
  reported as sensitivity only. U+FFFD is never repaired; its presence is
  recorded as a per-call contract flag, following the existing U+FFFD amendment.

## 7. Metrics

| Role | Metric |
|---|---|
| Primary | `mean per-region ΔCER` against `FULL`, paired within region |
| Sensitivity | corpus CER = Σ(edit distance) / Σ(reference length) |
| Secondary | oracle-layout page CER: concatenate region predictions in ground-truth order, score per page |
| First-class, reported separately | truncation rate, empty rate, repetition rate |
| Efficiency | end-to-end latency per region, peak VRAM, actual token counts per stage |

Macro (mean of per-region ratios) and micro (ratio of sums) answer different
questions and diverge when region lengths differ; both are declared, with the
macro paired difference as primary.

Truncated, empty, and degenerate generations are **included** in the primary
metric. A non-truncated subset analysis is reported as sensitivity only and
never substituted for the primary result, because pruning-induced truncation is
a real failure mode, not a nuisance to be filtered away.

## 8. Statistical plan

### 8.1 The primary contrast is `PRUNE_GRID`, not `PRUNE_RANDOM`

Resolution Reduction is a *uniform spatial* reduction of the whole image. Its
post-encoder analogue is uniform stride selection, so `PRUNE_GRID` holds the
spatial-selection policy as close to RR as the two mechanisms allow and leaves
the location of the reduction as the thing that differs. That is the H3 question.

`PRUNE_RANDOM` answers a different question — whether any spatial structure
matters at all — and is a structure-free reference baseline, not the primary
arm. Designating it primary would confound "where the reduction happens" with
"selection is stochastic".

### 8.2 Registered primary estimand

For each budget `b` in `{75, 50, 25}`:

```
ΔCER(C, b) = macro_CER(condition C at budget b) − macro_CER(FULL)
DiD_b      = ΔCER(PRUNE_GRID, b) − ΔCER(RR, b)
```

`macro_CER` is the mean of per-region CER, unclamped, over all analysed regions.
A **positive** `DiD_b` means post-encoder pruning degraded recognition more than
resolution reduction at the same actual token count.

### 8.3 Uncertainty and multiplicity

- Cluster bootstrap resampling the source-image cluster with replacement; a
  cluster drawn more than once contributes each time.
- 10,000 resamples with a seed frozen in the run config.
- **One resample index matrix is shared across every condition and budget**, so
  that `ΔCER` terms entering a `DiD` are computed on the same resampled
  clusters and the contrast keeps its covariance. Drawing independently per
  condition would inflate the `DiD` interval.
- Each `DiD_b` carries its **own** interval; it is never presented as two
  columns for the reader to subtract.
- Multiplicity family = the three `DiD_b` values. Holm adjustment is applied
  within that family only.
- `PRUNE_RANDOM` contrasts, component diagnostics, `micro_CER`, oracle-layout
  page CER, and every sensitivity analysis sit **outside** the primary family
  and are reported without being folded into its correction.

### 8.4 `PRUNE_RANDOM` seed rule

Both seeds are reported as separate estimates together with their range. They
are never pooled into a single number, never used for the primary estimand, and
the better-looking seed is never selected. Their purpose is to show whether the
structure-free baseline is stable.

### 8.5 Failed and missing calls

An execution failure is an engineering event, not a recognition error, and is
**never scored as CER 1.0** — doing so would silently convert infrastructure
faults into apparent degradation. Failed calls are excluded from the metric and
reported as a per-condition count. If the failure rate differs materially across
conditions, the primary estimate is flagged as compromised rather than reported
as if the conditions were comparable.

Truncated, empty, and degenerate generations are the opposite case: they are
genuine model behaviour and stay in the primary metric (§7).

### 8.6 No data-dependent switching

The primary contrast, estimand, cluster unit, resample count, and multiplicity
family above are frozen. They are not revised after any outcome is observed, and
a secondary result is never promoted to primary because it looks better.

No "worth it" threshold is defined in advance. The *measurement* procedure is
frozen here; the value judgement belongs to the human researcher after the table
exists.

## 9. Component diagnostic

Edit operations are classified by the Unicode class of the **reference**
character:

```
tone marks    U+0E48-U+0E4B
upper vowels  U+0E31, U+0E34-U+0E37, U+0E47
lower vowels  U+0E38-U+0E3A
base consonants U+0E01-U+0E2E
```

Region-level measurement removes the reading-order ambiguity that makes this
attribution unreliable on full pages, but the attribution is still
alignment-dependent. Frozen before any outcome:

- the alignment algorithm and its cost model;
- the tie-break rule when several alignments have equal cost;
- the handling of reference characters outside the four classes;
- mandatory reporting of the fraction of text that could not be aligned.

This output is `DESCRIPTIVE_DIAGNOSTIC_ONLY`. It does not identify a mechanism,
does not establish that a component is inherently fragile, and is not a
registered outcome.

## 10. Dataset

Candidate survey, verification, and the selection rule are in
`docs/stage0/REGION_OCR_DATASET_CANDIDATE_AUDIT.md`.

Leading candidate is **TEMS** (Mendeley DOI 10.17632/ntdmgksh9w.5, CC BY 4.0),
verified to provide region crops with transcriptions and a recoverable
`source_photo_id` giving **1,237** photo-level clusters with leakage-safe
splits already supplied by the authors. The two candidates named in the earlier
plan are rejected: `mekpro/ocr_th` has no region annotations and is synthetic,
and `typhoon-ai/ThaiOCRBench` carries ShareAlike plus unenumerated commercial
upstream terms and an unconfirmed bbox structure.

Binding rules for whichever corpus is used:

1. Ground truth is read from the structured metadata, never from filenames —
   1.6% of TEMS filenames disagree with the label field.
2. The clustering unit is the source photograph. Every region from one source
   photo stays on one side of any split.
3. The evaluation split is not opened during development and never used to
   choose a model, prompt, budget, scale policy, or metric.
4. **`FULL` is the processor's default operating point, not a policy we
   invent** (audit §3.2, measured in
   `docs/stage0/REGION_OCR_PROCESSOR_GEOMETRY.json`). The processor declares
   `min_pixels: 112896` with `patch_size 14` / `merge_size 2` and upsamples
   anything below that floor. Running it over all 5,000 released crop
   dimensions gives placeholders of p1 145 / median **160** / p99 180, min 144,
   max 405, and **no region with a degenerate four-level grid**. The count is
   not monotonic in crop area, because `smart_resize` chooses the grid shape,
   so `N` genuinely varies and the per-region matching rule in §5 is required
   rather than decorative.

   Two consequences are stated wherever results are reported: `FULL` means the
   model's standard operating resolution for that crop rather than all available
   detail; and because a median crop carries roughly 11 tokens of native detail
   presented as 144, most tokens are interpolated redundancy. That biases the
   design towards finding pruning harmless, so a positive result is strong while
   a null is weak and carries this caveat.
5. Report realized counts including shortfalls. Quotas are never filled with
   material that failed quality control.

**Fallback if no corpus clears:** render synthetic Thai regions with the Noto
fonts vendored in `assets/fonts/noto/` (SIL OFL 1.1, pinned commit and SHA-256
in `SOURCE.md`). Ground truth is then exact and licence-free, at the cost of
external validity, and that trade-off must be stated wherever results are
reported. The text corpus would itself require separate licence clearance.

## 11. Execution and fail-closed rules

- Engineering smoke precedes the scientific run and is excluded from every
  scientific summary.
- The scientific run executes all registered cells; an exact rerun is used only
  to audit reproducibility and never pooled to narrow an interval.
- Token accounting must prove that the number of positions entering the language
  model was actually reduced — replacing tokens with zeros, masking them, or
  leaving placeholder counts unchanged is a fail-closed corruption.
- Required invariants per pruned call: `pre_prune == N`, `post_prune == K`, and
  `llm_positions == K`.
- Stop and escalate to the human on: token-accounting mismatch, model identity
  mismatch, checksum failure, or evaluation-split exposure.
- If the models cannot read the stimuli well enough at `FULL` for a change to be
  observable, stop and report that, and let the human decide about the backbone
  **before** any pruning outcome is examined.

## 12. Prohibited in this branch

Post-outcome changes to prompt, parser, budgets, dataset, split, or model
presented as the same registered run; opening the evaluation split early;
quantization; fine-tuning; method development; claiming a new method is
justified; reusing this branch's result as Gate 0 or Gate 1 evidence; and
importing the completed Resolution-Reduction panel as a control arm for this
experiment.

## 13. Repository consistency

`src/labbs2026/consistency.py` checks the text of the research documents; it
does not inspect what has been executed. Running this branch therefore does not
make `scripts/check_research_consistency.py` fail, and **no amendment to any
existing research document is required in order to execute.**

Its assertion at lines 99-101 is a conjunction of three separate statements. Two
of them — that Resolution Reduction is not post-encoder Token Pruning, and that
this does not make Stage 1A a post-encoder pruning experiment — are conceptual,
remain true regardless of this branch, and **must not be modified**. This branch
does not re-open, re-interpret, or rewrite Stage 1A.

The third is a `docs/DECISION_LOG.md` status line. Whether it needs revisiting
arises only when results are recorded, and under the `docs/CLAIMS.md` vocabulary
`Tested` requires direct valid **locked** evidence, which a `Preliminary/Pilot`
result is not. Any adjustment there is a deliberate human decision at that
point, never an edit made to turn a failing check green.
