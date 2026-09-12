# Research Decision Log

> Human-owned scientific decision record. Codex may propose decisions and summarize evidence, but final gate approval belongs to the researcher.

## 2026-09-12 — Scientific framing amended; S0 baseline authorized

**Human decision:** Accept the Paddle/Wayu engineering smoke and set
`APPROVED_FOR_S0_OPEN_CALIBRATION_BASELINE_ONLY`.

**Required framing:** The comparison is **base OCR VLM versus Thai-specialized
OCR descendant**, or **Thai-specific OCR adaptation**. It is not general VLM
versus OCR-specialized VLM because PaddleOCR-VL-1.6 is already an
OCR/document-recognition model. The revised question is: “Does Thai-specific
OCR adaptation change robustness to controlled visual-information reduction?”
The future primary interaction remains non-directional `MODEL x BUDGET`.

**Causal boundary:** Do not claim that the 45,723-page synthetic training set
is the only difference between checkpoints.

**Authorized scope:** S0 open-calibration full-information baseline only. Use
the remaining 95 open-calibration `pair_id` values after excluding the five
engineering-smoke pairs; do not replace them from locked validation. The exact
workload is 95 pairs x 2 members x 2 fonts x 2 sizes x 2 models = 1,520 calls,
with identical registered 448x448 PNGs, prompt `OCR:`, deterministic greedy
decoding, and a parser frozen before inference.

**Not authorized:** locked validation, Resolution Reduction, Token Pruning,
Token Merging, any other compression or representation intervention,
fine-tuning, new-method work, or scientific comparison with Qwen3.5 history.
After S0 analysis, stop at `HUMAN_REVIEW_AFTER_S0_OPEN_CALIBRATION`.

## 2026-09-12 — Paddle/Wayu engineering smoke complete; human review required

**Scope:** Non-scientific engineering validation only. The authorized 40-call
workload completed once on Kaggle T4 with no retry or resubmission.

**Observed engineering evidence:** Both exact revisions resolved and loaded as
`PaddleOCRVLForConditionalGeneration` with `PaddleOCRVLProcessor`. All 40 calls
used the identical `OCR:` contract and matched PNG hashes. All 20 exact-repeat
groups were identical. Every call recorded `image_grid_thw=[1,32,32]`, 1,024
pre-merge positions, 256 projector positions, 256 LLM image placeholders, and
finite expected intermediate tensors. Output slicing and Unicode decoding
passed. Kaggle selected Tesla T4; peak reserved VRAM was approximately 1.810
GiB per sequentially loaded model. `locked_pair_count=0`; failure log was empty;
local artifact verification was `VERIFIED`.

**Codex recommendation:**
`ENGINEERING_SMOKE_PASS_S0_READY_PROPOSED`.

**Scientific boundary:** No accuracy, model ranking, specialization benefit,
measurement capacity, component effect, or compression robustness was
calculated or interpreted. This recommendation is not Stage S0 approval.

**Decision state:** `HUMAN_REVIEW_AFTER_ENGINEERING_SMOKE`. Stage S0, locked
validation, Resolution Reduction, Token Pruning, Token Merging, scientific
representation comparison, fine-tuning, and new-method work remain prohibited.
Full evidence is in `PADDLE_WAYU_ENGINEERING_SMOKE_REPORT.md` and the immutable
run `kaggle-paddle-wayu-smoke-dcd835673e1c-28c1cecd`.

## 2026-09-12 — Paddle/Wayu engineering smoke authorized

**Human decision:** Accept the fallback audit and current-scope
`TERMS_CLEAR` classification. The PaddleOCR-VL-1.6 / Wayu-Paxa pair is
`APPROVED_FOR_ENGINEERING_SMOKE_ONLY` for exactly 40 calls: five already
exposed open-calibration `pair_id` values, two members, two models, and two
exact repeats under the shared direct region-recognition prompt `OCR:`.

**Purpose:** Engineering validation only. Accuracy, model ranking,
specialization benefit, component capacity, and compression robustness are not
smoke gates and must not be calculated or interpreted.

**Fail-closed boundary:** Any checkpoint, loading, processor, prompt, output
slicing, Unicode, determinism, visual-token accounting, tensor/module, runtime,
T4, or locked-set failure stops the run. Engineering repair requires another
human review before rerun.

**Still prohibited:** Stage S0, locked validation, Resolution Reduction, Token
Pruning, Token Merging, scientific representation comparison, fine-tuning,
new-method work, and comparison with historical Qwen3.5 outputs.

**Mandatory stop:** `HUMAN_REVIEW_AFTER_ENGINEERING_SMOKE`.

## 2026-09-12 — Paddle/Wayu engineering smoke authorized

**Human decision:** Accept the fallback-pair audit and current-scope
`TERMS_CLEAR` classification. The PaddleOCR-VL-1.6 / Wayu-Paxa candidate pair
is `APPROVED_FOR_ENGINEERING_SMOKE_ONLY`.

**Authorized workload:** exactly 40 non-scientific calls: five already-exposed
open-calibration `pair_id` values, both members, both models, and two exact
repeats. Both models use identical PNGs and the direct region-recognition
prompt `OCR:`. Accuracy is not an engineering gate and no scientific model or
component comparison may be calculated or interpreted.

**Fail-closed boundary:** any identity, loading, processor, prompt, output
slicing, Unicode, determinism, token-accounting, tensor-path/shape, runtime,
T4-feasibility, or locked-set failure stops the run. An engineering repair
requires a new human review before rerun.

**Still prohibited:** Stage S0, locked validation, Resolution Reduction, Token
Pruning, Token Merging, scientific representation comparison, fine-tuning,
new-method work, and comparison with Qwen3.5 diagnostic history. After the
smoke report, stop for human review; do not advance automatically.

## 2026-09-12 — Typhoon branch closed; fallback pair audited

**Human decision:** Typhoon OCR is `NOT_PURSUED_DUE_TO_USAGE_TERMS`. The
current OpenTyphoon competitive-benchmarking consent dependency is not
operationally acceptable for this project. This is not a scientific rejection.
Prior provenance, architecture, literature, and design records are preserved.

**Fallback source-only audit:** The candidate
`PaddlePaddle/PaddleOCR-VL-1.6@c5630abae1d940eafe0697512a0325494b02ab42`
and
`wayu-ai/wayu-paxa-ocr-zero@af0204b4f334a6d5068b6bac2b3738932d6e289b`
is classified `TERMS_CLEAR`. Official sources declare Wayu as a full fine-tune
of the Paddle base on 45,723 synthetic pages and the shared 608-tensor
generative core has matching key names, shapes, and dtypes. The exact immutable
fine-tuning parent revision and equality of common weight values are not
established; PaddleOCR-VL-1.6 is itself an OCR model.

**Codex recommendation:** `APPROVE_PADDLE_WAYU_FOR_ENGINEERING_SMOKE` using
the exact 40-call, open-calibration-only workload proposed in
`FALLBACK_PAIR_CLEARANCE.md`. This recommendation does not authorize execution.

**Current decision:** `FALLBACK_PAIR_PENDING_HUMAN_REVIEW`.

**Not authorized:** any Typhoon use; any fallback-model inference; locked
validation; Resolution Reduction; Token Pruning; Token Merging; fine-tuning;
or Gate 0 change. The research question remains model-agnostic.

## 2026-09-12 — Specialization pivot proposed; human review required

**Stage/Gate:** Proposed amendment only; `Gate 0` remains `NOT_RUN`.

**Proposal:** Evaluate a closely related base and OCR-specialized descendant,
`Qwen/Qwen3-VL-2B-Instruct` and `typhoon-ai/typhoon-ocr1.5-2b`, under a staged
S0-S5 plan. The proposed primary question is a non-directional
`MODEL x BUDGET` interaction. A component-level three-way interaction remains
conditional on measurement capacity.

**Audit evidence:** Both pinned repositories declare the same Qwen3-VL 2B
architecture/config structure, parameter count, patch/merge settings,
DeepStack indexes, and 625 compatible state-dict key names/shapes/dtypes.
Typhoon declares the Qwen model ID as its fine-tuning base, but does not declare
the immutable parent revision. Weight values and full training lineage were
not established. Exact evidence is in `SPECIALIZATION_PIVOT_REVIEW.md` and
`architecture/QWEN3VL2B_TYPHOON_OCR15_CONFIG_DIFF.json`.

**Blocking issue:** The Typhoon model card links OpenTyphoon Terms whose
current text prohibits competitive benchmarking without prior express written
consent. Future model use therefore requires
`LEGAL_TERMS_CLEARANCE_REQUIRED`; this is not a legal conclusion about the
interaction between those terms and the HF `apache-2.0` tag.

**Decision:** `SPECIALIZATION_PIVOT_PENDING_HUMAN_REVIEW`.

**Not authorized:** model inference, engineering smoke, locked validation,
Resolution Reduction, Token Pruning, Token Merging, fine-tuning, prompt tuning,
or new-method implementation. Historical Qwen2.5/Qwen3.5 decisions and
artifacts are not overwritten and cannot be used as matched specialization
evidence.

## 2026-09-12 — Measurement-contract pilot result and human-review stop

**Observed result:** The verified 25-pair open-calibration pilot produced A
accuracy 49.50% (pair-clustered 95% CI 47.50–51.00%), B 0.00% (0–0%), and C
0.00% (0–0%). `delta_interface` was -49.50 pp (-51.00 to -47.50), while
`delta_surrounding` was 0.00 pp (0–0). B/C had no exact or opposite-member
outputs. Condition C's output-contract-failure rate was 22.5% (17.0–29.0%),
exceeding the frozen 20% interpretability flag. `locked_pair_count=0`.

**Frozen decision:** `MIXED_TARGETED_INSTRUMENT_REVIEW`. Direct transcription
did not rescue the current model and therefore does not support A/B interface
as the sole/main explanation. The result also does not establish visual-
representation failure because transcription readout remained invalid and the
prior D3 representation probe was strong.

**Stop boundary:** Human review is required. Do not screen another backbone,
change Gate 0, run compression, tune the prompt/layout, open locked validation,
or start the main experiment. Full evidence is in
`docs/stage0/QWEN35_MEASUREMENT_CONTRACT_PILOT_REPORT.md`.

## 2026-09-12 — Final visual/protocol approval for pilot inference

**Stage/Gate:** Qwen3.5 open-calibration measurement-contract pilot only;
Gate 0 remains `NOT_RUN`.

**Human decision:** The B/C contact sheets across all five components, both
fonts, and both sizes passed visual review. The existing 200/200 byte-level
target-pixel identity validation is accepted. Run only the frozen 25-pair
Qwen3.5 pilot, then stop for human review.

**Frozen interpretation:** Condition C is a controlled artificial surrounding-
layout diagnostic, not natural-language context, positional robustness, or a
realistic document-layout test. `delta_surrounding = C - B` supports only a
statement associated with adding the frozen surrounding layout around the
same centered target.

**Authorization:** Conditions B/C inference and the registered A/B/C analysis
are authorized. Condition A must reuse its verified D1 rows. Locked validation,
backbone screening, Gate 0 changes, compression, post-outcome tuning, and the
main experiment remain prohibited.

## 2026-09-12 — Condition C pre-inference amendment required

**Stage/Gate:** Qwen3.5 open-calibration measurement-contract pilot only;
Gate 0 remains `NOT_RUN`.

**Human decision:** Approve the 25-pair selection, Condition A aggregation,
`pair_id` analysis, 10 pp SESOI, uncertainty, locked-set protection, and
general decision logic. Require Condition C revision and final visual/protocol
approval before inference.

**Amendment:** Conditions B and C now share one exact center-target-only prompt
and return one target string. C is constructed from the exact frozen B PNG by
adding fixed anchors and separators only outside the target cell. Literal pipe
output and full-line alignment are removed. The paired contrast is renamed
`delta_surrounding = C - B` and supports only an association with adding the
frozen controlled surrounding visual layout, not a single causal mechanism or
natural-language contextual effect. Full-line transcription is deferred to a
separate future diagnostic.

**Required pre-inference evidence:** paired B/C contact sheets and a byte-level
report showing identical B/C target-crop RGB hashes for every one of the 200
selected target observations, plus invariant non-target layers within each
font/size condition.

**Generated non-model evidence:**
`docs/stage0/evidence/qwen35_measurement_contract_pilot_preflight/CONTACT_SHEETS.md`
contains 20 paired B/C sheets. The corresponding
`pixel_identity_validation.json` reports 200/200 target observations passing
raw-RGB target-crop identity, zero non-target invariance failures, zero locked
pairs, and `model_inference_performed=false`. Human visual/protocol approval
remains pending.

**Historical provenance:** Commit
`13c64500442bc3790362f82964ad39666fc8b382` preserves the superseded
pre-inference C contract. No pilot model output was observed before this
amendment.

**Current authorization:** Protocol/config amendment, deterministic stimulus
construction, contact sheets, and pixel-identity validation only. Model
inference, locked validation, backbone screening, compression, and the main
experiment remain unauthorized.

## 2026-09-12 — Measurement-contract pilot approved with revisions before inference

**Stage/Gate:** Qwen3.5 open-calibration measurement diagnostic only; Gate 0
remains `NOT_RUN`.

**Human decision:** Approve in principle a three-condition pilot using A
forced-choice, B isolated transcription, and C line-layout transcription, but
require a revised frozen protocol and another quick human check before any
model inference.

**Required revisions recorded:** B/C have no 50% chance-validity threshold;
the primary diagnostics are paired `delta_interface = B - A` and
`delta_line = C - B`, with a 10 percentage-point SESOI and an important effect
requiring point estimate at least +10 pp plus pair-clustered paired 95% CI
lower bound above zero. A's two candidate orders reduce to one target-level
score and are not independent. C uses fixed cells whose non-target pixels are
invariant across target members, and is explicitly a line-layout—not natural-
language context—diagnostic. Selection, prompt, decoding, normalization,
alignment, taxonomy, metrics, and stop rules are fixed before inference.

**Revised protocol:**
`docs/stage0/QWEN35_MEASUREMENT_CONTRACT_PILOT_PROTOCOL.md` and
`configs/stage0/qwen35_measurement_contract_pilot.yaml`.

**Current authorization:** Documentation and non-model validation only.
Inference remains unauthorized pending the quick human protocol check.
Locked validation, backbone screening, split changes, Gate 0, Stage 1A,
compression, and the main experiment remain prohibited.

## 2026-09-08 — Qwen3.5 measurement diagnostic result and stop

**Stage/Gate:** Stage 0 open-calibration measurement diagnostic only; Gate 0
remains `NOT_RUN`.

**Observed result:** The verified D1-D4 run used only the 100 previously exposed
calibration `pair_id`s. D1 content consistency was 10.75% (pair-clustered 95%
CI 6.63-15.38%) and position following was 89.25% (84.63-93.38%). D2
blank-corrected candidate accuracy was 52.88% (50.75-55.13%). D3
post-spatial-merger retrieval accuracy was 97.88% (96.75-98.88%). D4 magnified
visual rescue reached 65.50% corrected accuracy (60.50-70.50%) and improved
16.00 percentage points (10.50-21.50) over its matched original-source
condition.

**Frozen classification:** `inconclusive`. The D1 estimate showed strong
position sensitivity, but its lower CI did not reach the pre-registered 90%
interface threshold. D2 did not reach the registered signal criterion, while
D3 and D4 did. This tension must not be post hoc relabeled as `mixed`.

**Codex recommendation:** **C. screen an architecturally distinct backbone**.
Recommend `google/gemma-3-4b-it` for human consideration because it is a
different multimodal model family and 4B-scale T4 fit is plausible, not yet
verified. Do not run it without a separate human authorization and frozen
screening contract.

**Evidence:** `docs/stage0/QWEN35_MEASUREMENT_DIAGNOSTIC_REPORT.md`; run
`kaggle-qwen35-measurement-953dd5e386ea-79122b58`; inference commit
`953dd5e386eaeee22b549995b9c80f2a3691ebbf`; pre-registration commit
`4243b7f780c561e447d3efa5c624e8fe777559aa`.

**Consequence:** Stop at `HUMAN_REVIEW_CHECKPOINT`. No Qwen2.5 D1-D4 comparison
is valid because Qwen2.5 has not been evaluated under the same diagnostic
contract. Locked validation, Gate 0, Stage 1A, every compression intervention,
the main experiment, and a new-backbone run remain blocked.

## 2026-09-08 — Qwen3.5 measurement diagnostic authorization and pre-registration

**Stage/Gate:** Stage 0 open-calibration measurement diagnostic only; Gate 0
remains `NOT_RUN`.

**Human decision:** After the Qwen3.5-4B calibration failure, authorize D1
position swap, D2 candidate sequence scoring without A/B tokens, D3
post-merger representation separation, and D4 a clearly magnified visual
rescue using only the 100 already exposed calibration pairs. Require metrics,
root-cause decision criteria, and the A/B/C action map to be committed before
diagnostic outcomes are observed.

**Frozen protocol:**
`docs/stage0/QWEN35_MEASUREMENT_DIAGNOSTIC_PROTOCOL.md` and
`configs/stage0/qwen35_measurement_diagnostic.yaml`. `pair_id` remains the
independent unit and uncertainty uses pair-clustered bootstrap. Candidate
scoring is blank-corrected sum sequence log-probability. Representation
retrieval is diagnostic only. Visual rescue changes glyph scale within the
same 448 x 448 canvas and must retain the same processor and 196 native visual
positions.

**Still prohibited:** locked validation, frozen-split changes, Gate 0 approval,
Stage 1A, Resolution Reduction, Token Pruning, Token Merging, the main
experiment, all compression interventions, and any new-backbone inference.

**Mandatory stop:** After D1-D4, record one bounded root-cause classification
and one A/B/C recommendation, update reproducibility artifacts, and stop for
human review.

## 2026-09-07 — Qwen3.5-4B measurement-capacity audit authorization

**Stage/Gate:** Stage 0 calibration-only backbone assessment; Gate 0 remains
`NOT_RUN`.

**Human decision:** Evaluate `Qwen/Qwen3.5-4B` end to end as a candidate primary
measurement backbone using only the 100 already exposed calibration pairs.
Authorize a minimal adapter/factory, tests, Kaggle T4 model-load and engineering
smoke, and—only if the smoke passes—two exact 1,000-observation full-information
calibration passes with matched blank controls. The human request explicitly
forbids locked validation, Gate 0 approval, Stage 1A, Resolution Reduction,
Token Pruning, Token Merging, and every other compression experiment.

**Pre-registered rationale:** The candidate is opened before any Qwen3.5 Thai
calibration outcome because it is a compact current-generation open-weight
multimodal model with official OCR/visual-language capability, an inspectable
Vision Encoder and spatial merger, reproducible Hugging Face inference, a
future-accessible post-encoder representation, and Apache-2.0 licensing. The
exact rationale and pinned pre-inference identity are recorded in
`docs/stage0/QWEN35_BACKBONE_RATIONALE.md` with outcome state
`NO_QWEN35_MODEL_OUTPUT_OBSERVED`.

**Selection integrity:** Qwen3.5 may not be chosen because its outcome supports
a preferred Thai-specific or compression hypothesis. Failure to establish
baseline measurement capacity is a valid result. A T4 fallback to
`Qwen/Qwen3.5-2B` may be considered only after a recorded 4B compute
infeasibility classification, never because of 4B accuracy.

**Mandatory stop:** After the calibration assessment, report a backbone
recommendation and stop for human review. Gate 0 and all later stages remain
human-owned and blocked.

## 2026-09-07 — Qwen3.5-4B calibration result and backbone recommendation

**Stage/Gate:** Stage 0 open calibration only; Gate 0 remains `NOT_RUN`.

**Observed result:** The pinned Qwen3.5-4B FP16 checkpoint fit on Kaggle Tesla
T4. The 40-call engineering smoke passed pinned identity, exact one-token A/B,
direct/generation logit equality, 784-to-196 runtime visual accounting, and
exact rerun. Two full 1,000-observation calibration runs then reproduced
exactly with zero parser/execution failures and zero locked-pair exposure.
Primary-run accuracy was 49.875% (pair-clustered 95% CI 49.00–50.75%). Blank
controls selected A 100%, expected-A/B accuracies were 93.25%/6.50%, and mean
image gain was 0.0106 (95% CI -0.0173 to 0.0399). All five components are
`INADEQUATE` under the pre-registered measurement-planning rules.

**Codex recommendation:** `MEASUREMENT_REDESIGN_REQUIRED`. Do not adopt
Qwen3.5-4B as primary under the present measurement contract. This is not a
Gate 0 decision and does not authorize post-outcome prompt retuning, another
backbone run, dataset changes, locked validation, Stage 1A, or compression.

**Evidence:** `docs/stage0/QWEN35_BACKBONE_CALIBRATION.md`; run
`kaggle-qwen35-stage0-4fef178183d7-b31935da`; inference commit
`4fef178183d77c533fcc854a37748ce308688e38`.

**Interpretation boundary:** The result establishes measurement inadequacy for
this exact Qwen3.5 checkpoint, prompt/label contract, synthetic calibration,
rendering, and runtime. It does not establish general Thai OCR weakness, an
architecture ranking, a visual-token-count cause, or any compression effect.

**Consequence:** Stop for human review. Gate 0 remains `NOT_RUN`; locked
validation and all compression work remain blocked.

## 2026-09-07 — Calibration image-gain diagnostic authorization and result

**Stage/Gate:** Stage 0 calibration diagnostic only; Gate 0 remains `NOT_RUN`.

**Human decision:** Authorize a fail-closed 40-call engineering smoke followed,
only on smoke PASS, by one 1,000-call A/B decision-margin diagnostic using the
100 already exposed calibration pairs. Keep prompt, parser, rendering, model,
runtime, primary binary metric, and all later-stage prohibitions frozen.

**Observed result:** The smoke passed exact token-boundary, independent-forward,
binary-invariance, and deterministic-margin checks. The 1,000-call diagnostic
completed with zero failures and no locked-pair exposure. Mean image gain was
positive overall and within every component, but was weak and highly
member-dependent for lower-vowel and stacked-tone categories. Blank inputs
showed an 85% position-A choice rate. Size-related accuracy and image-gain
directions generally agreed; font effects were not uniform.

**Codex recommendation:** `MEASUREMENT_SCALE_DIAGNOSTIC`. This is a proposal
for human review, not authorization for additional inference and not a Gate 0
decision.

**Evidence:**

- run ID: `kaggle-stage0-margin-80088b862c5a-008c5556`;
- report: `docs/stage0/CHECKPOINT_E_IMAGE_GAIN_DIAGNOSTIC.md`;
- refreshed primary literature: `docs/LITERATURE.md`.

**Known limitations:** Margin evidence is calibration-only, secondary to the
registered binary metric, and non-causal. Blank images still contain visual
tokens. The evidence is Qwen-only and synthetic, tests no compression, and
does not establish model capacity or publication-dataset validity.

**Consequence:** Stop for human review. Gate 0 criteria, locked validation,
secondary backbone, Stage 1A, and every compression intervention remain
blocked.

## 2026-09-06 — Stage 0 Calibration Repair v2 authorization

**Stage/Gate:** Stage 0 calibration repair only; Gate 0 remains `NOT_RUN`.

**Human decision:** Implement the narrowest technically valid canonical A/B
output constraint, verify it with an engineering-only smoke on already
exposed calibration pairs, and run the same registered calibration workload
only if the smoke passes. Locked validation, Gate 0 decisions, Stage 1A, and
all compression interventions remain unauthorized.

**Historical failure classification:**
`REGISTERED_OUTPUT_PARSER_CONTRACT_FAILURE`. The previous two exact runs stay
immutable invalid registered runs. Their post-hoc leading-label analysis
remains diagnostic only.

**Frozen scientific inputs:** The 100 calibration `pair_id`s, strings,
component assignments, candidate order, rendered images, blank allocation,
model/processor revision, prompt, and scientific scoring definitions remain
unchanged. Repair v2 changes only the generated-output contract from
unconstrained four-token generation to a one-token A/B constraint after
verifying the pinned tokenizer at the actual assistant generation boundary.

**Engineering smoke:** five calibration pairs selected before Repair v2
inference by the deterministic rule
`lexicographically_first_calibration_pair_per_component_v1`, one frozen
rendering condition, both displayed members, both blank orientations, and an
exact rerun. This is 20 calls per run and 40 total. No visual-accuracy metric
from the smoke may support Gate 0.

**Mandatory stop:** after the repaired calibration, produce Checkpoint C and
wait for human review. Gate 0 criteria remain unapproved and locked validation
remains sealed.

**Checkpoint C result presented for human review:** the engineering smoke
passed all registered acceptance checks, after which two exact repaired
1,000-call calibration runs completed with zero execution, output-contract,
or parser failures and 100% raw/parsed/token agreement. The repaired baseline
was 71.25% overall, with component accuracies from 56.25% to 96.25%.
`LOWER_VOWEL_VARIANT` and `STACKED_TONE_MARK` have less than the provisional
10 pp downward headroom above chance at their point estimates;
`UPPER_VOWEL_VARIANT` has point-estimate but not interval-lower-bound
headroom. Strong blank A-position preference and large member/condition
asymmetries remain unresolved. Status is
`REPAIRED_CALIBRATION_COMPLETE_PENDING_HUMAN_REVIEW`; Gate 0 remains
`NOT_RUN` and locked validation remains blocked. Full evidence is in
`docs/stage0/CHECKPOINT_C_REPAIRED_INSTRUMENT.md`.

**Checkpoint C human review:** the human researcher determined that the
output/parser/runtime contract is valid, but the current measurement
instrument is not adequate for every component under the provisional 10 pp
planning SESOI. `BASE_CHARACTER` and `TONE_MARK` are currently
measurement-usable, `UPPER_VOWEL_VARIANT` is borderline, and
`LOWER_VOWEL_VARIANT` plus `STACKED_TONE_MARK` are not currently adequate.
This is measurement-validity evidence only and does not test compression or
reject H1. Gate 0 criteria remain unfrozen and locked validation remains
sealed.

**Checkpoint D result presented for human review:** analysis of only the 100
already exposed calibration pairs found large, oppositely directed canonical
member asymmetries; descriptive font-by-size variation, especially for lower
vowels; and strong blank position bias that aligned with 51.74% of
FULL_INFORMATION errors under the same pair and candidate orientation. The
evidence does not identify one dominant mechanism. Exact run 2 remained a
reproducibility audit and was not pooled. The pinned adapter can technically
expose raw A/B next-token logits, but existing artifacts do not contain them,
so a proposed 1,040-call margin diagnostic requires new human authorization.
Recommendation is `MULTIPLE_DIAGNOSTICS_REQUIRED`; details are in
`docs/stage0/CHECKPOINT_D_CALIBRATION_ONLY_DIAGNOSTICS.md`. Gate 0 remains
`NOT_RUN`, and locked validation plus all later stages remain blocked.

## 2026-09-06 — Checkpoint A final freeze for Stage 0 calibration

**Stage/Gate:** Stage 0 calibration only; Gate 0 remains `NOT_RUN`.

**Human decision:** `APPROVED FOR STAGE 0 CALIBRATION ONLY`. The calibration
design status is `FROZEN_CALIBRATION`. This authorizes the exact two-run,
2,000-call Kaggle T4 workload and does not authorize locked validation, Gate 0
approval, Stage 1A, Resolution Reduction, Token Pruning, Token Merging, or any
other compression intervention.

**Frozen evidence identity:**

- candidate inventory SHA-256:
  `cf69f0d23bec61fbeaca7fd5ed34d48219aaad9624e509cc2208a0c98a8021b2`;
- source review packet SHA-256:
  `e340a2b8386751352beb36732d21a6c613fd3bbdd1822262880e4a0a4b671df3`;
- pair allocation version: `stage0_pair_allocation_v1`;
- pair allocation SHA-256:
  `385c283091852820016bd6b1247a01af90ee04e966d298761f14cd392b8f47e8`;
- 100 calibration and 100 disjoint locked-validation `pair_id`s, balanced at
  20 per component category in each split;
- four centered 448 x 448 black-on-white rendering conditions listed in
  `configs/stage0/calibration_design.yaml`;
- all 100 calibration pairs receive both orientations of
  `LANGUAGE_CANDIDATE_BIAS_BLANK`; these controls have no visual ground truth
  and never enter visual accuracy.

**Frozen numerical/runtime contract:** Kaggle `NvidiaTeslaT4`, `float16`,
`sdpa`, Python 3.12, `torch==2.14.0+cu130`, `transformers==4.57.6`, pinned
model and processor revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`, `use_fast=False`, the pinned
processor parameters in `configs/stage0/qwen25_vl_3b_calibration.yaml`,
deterministic decoding (`do_sample=false`, `max_new_tokens=4`), and seed
`20260906`. The exact rerun measures realized reproducibility; deterministic
PyTorch algorithms were not newly enabled because the approved configuration
follows the verified backend proof run.

**Interpretive boundaries:** Current lexical status remains provisional;
`UNCERTAIN` is neither recoded as `CONSTRUCTED` nor excluded automatically.
Current `BASE_CHARACTER` pairs remain
`size_matched_stage2_status = NOT_ASSESSED_NOT_ASSUMED`. The 10 percentage
point SESOI remains measurement-planning guidance only.

**Required next checkpoint:** stop after calibration and report observed
evidence, interpretation, proposed numeric Gate 0 criteria, and unresolved
uncertainty separately. Human review is required before locked validation.

**Execution note:** Kaggle kernel version 1 failed during source verification,
before environment setup or model inference, because the Windows working-tree
hash of `uv.lock` used CRLF while the Linux checkout used the committed LF
form. No calibration or blank-control prompt reached the model. The failed
attempt is retained as an execution artifact. The portability fix pins
`uv.lock` to LF in `.gitattributes`; it does not alter the frozen dataset,
allocation, prompt, model, runtime, or analysis design.

**Calibration result presented for human review:** both exact 1,000-call runs
completed with zero call-level execution failures and exact raw-output/token
agreement. However, all 2,000 raw responses violated the registered `^[AB]$`
parser by returning forms such as `A. <text>` or `B. <text>`. Registered parser
failure is therefore 100%, conditional parsed accuracy is undefined, and the
current instrument status is
`CALIBRATION_INSTRUMENT_INVALID_PENDING_HUMAN_REVIEW`. This is classified as
`REGISTERED_OUTPUT_PARSER_CONTRACT_FAILURE`. Gate 0 remains
`NOT_RUN`; locked validation and Stage 1A remain blocked. Full evidence and
the non-frozen criteria proposal are in
`docs/stage0/CHECKPOINT_B_CALIBRATION.md`.

## 2026-09-06 — Stage 0 Checkpoint A conditional approval

**Stage/Gate:** Steps 4–6 / Stage 0 pre-calibration review

**Human decision:** `CONDITIONAL APPROVAL`. The five initial contact sheets
were accepted for Thai shaping, mark placement, clipping, and visible A/B
distinction. Calibration remains unauthorized until the revised inventory and
allocation receive a final human freeze.

**Frozen interpretation changes:**

- component labels are `BASE_CHARACTER`, `TONE_MARK`,
  `UPPER_VOWEL_VARIANT`, `LOWER_VOWEL_VARIANT`, and `STACKED_TONE_MARK`;
- current `BASE_CHARACTER` pairs are valid for Stage 0 but are not assumed
  size-matched for Stage 2;
- each pair member records `lexical_status` as `REAL`, `CONSTRUCTED`, or
  `UNCERTAIN`, and constructed strings remain admissible;
- blank images are language/candidate-bias controls without visual ground
  truth and must not be scored as OCR/visual accuracy;
- the provisional SESOI is 10 percentage points absolute differential
  degradation for Stage 0 planning and Advisor Readiness only.

**Already approved unless a new methodological issue is found:** Kaggle T4,
the pinned Qwen2.5-VL-3B revision, fixed prompt, exact A/B parser, pair-level
splitting, registered metrics, rendering-condition candidate pool, and
`FULL_INFORMATION`-only calibration.

**Operational backend status:**
`KAGGLE_T4_APPROVED_FOR_STAGE0_CALIBRATION`.

**Still prohibited:** Qwen calibration before final freeze, locked validation,
Gate 0 approval, Stage 1A, and every compression intervention.

**Revision presented for final freeze:** immutable review packet
`20260905T204206Z_e1ad6f35` contains 200 pairs (40/category), a proposed
20/20 pair split per category, 2,000 proposed calibration calls including the
exact rerun, and zero automated validation issues. The planning floor is not a
power guarantee. `ฬา/ฬ่า` was replaced before model exposure after the new
shaping audit detected a contextual base-glyph change.

## Status vocabulary

- `BLOCKED` — prerequisite gate not passed
- `NOT_RUN` — eligible but not evaluated
- `PILOTING` — exploratory work in progress; not final evidence
- `PASS_PROPOSED` — evidence suggests pass; awaiting human approval
- `FAIL_PROPOSED` — evidence suggests fail; awaiting human approval
- `INCONCLUSIVE_PROPOSED` — evidence insufficient; awaiting human decision
- `PASS` — human-approved gate pass
- `FAIL` — human-approved gate fail
- `INCONCLUSIVE` — human-approved decision that more evidence is required

---

# Gate 0 — Measurement validity

**Status:** NOT_RUN

## Question
Can the selected model + controlled dataset + forced-choice task reliably measure the intended distinctions without compression?

## Evidence required
- full-information baseline results;
- per-component accuracy;
- rendering spot-check;
- parser validation;
- Unicode validation;
- token-count validation;
- reproducibility check.

## Predefined decision criteria
To be proposed from Stage 0 calibration estimates of measurement precision,
ceiling/headroom, negative-control separation, and the intended Stage 1 effect.
The human researcher must freeze the criteria before locked Stage 0 validation.

Do not set or revise the threshold using Stage 1A or later compression results.

## Evidence
None yet.

## Decision
None yet.

## Consequence
- PASS → Stage 1A becomes eligible; a main Stage 1 experiment still needs
  its own registered intervention and analysis plan.
- FAIL → repair measurement setup; Stage 1A and main Stage 1 remain blocked.
- INCONCLUSIVE → improve Stage 0 precision or controls without weakening
  the frozen criteria; Stage 1A and main Stage 1 remain blocked.

---

# Stage 1A — Resolution Sensitivity Pilot

**Status:** BLOCKED

**Requires:** Gate 0 = human-approved PASS

## Question

Under processor-controlled Resolution Reduction, is there a preliminary
degradation signal worth studying in a later registered experiment?

## Evidence required

- grid frozen from processor/token mapping before predictions are opened;
- requested and actual visual-token budgets;
- per-component descriptive degradation curves;
- pair-clustered uncertainty estimates;
- raw-run audit and resource measurements.

## Decision authority

Stage 1A does not approve Gate 1. Its evidence status is `Preliminary/Pilot`.

## Consequence

- component-varying signal → consider a powered resolution experiment and a
  separately designed direct post-encoder study;
- generic signal → consider a generic micro-detail framing;
- no signal with wide uncertainty → resolution branch remains inconclusive;
- no signal with adequate precision → reduce or stop the resolution branch
  within the tested scope.

Post-encoder Token Pruning and H3 remain `NOT TESTED` in every Stage 1A outcome.

---

# Gate 1 — Differential degradation

**Status:** BLOCKED

**Requires:** Gate 0 = PASS

## Question
Does degradation across compression budgets meaningfully differ by orthographic component category?

## Evidence required
- registered budget grid;
- per-component degradation curves;
- uncertainty estimates;
- component × budget analysis;
- raw-run audit.

## Evidence
None yet.

## Decision
None yet.

## Consequence
- evidence of differential degradation → proceed to Stage 2;
- no meaningful differential degradation → stop Thai-component-specific interpretation and evaluate a generic compression/micro-detail framing;
- inconclusive → improve power or measurement before proceeding.

---

# Gate 2 — Visual-size/confound explanation

**Status:** BLOCKED

**Requires:** Gate 1 = PASS

## Question
Does the component-specific effect remain after accounting for critical visual evidence size and other major visual confounds?

## Evidence required
At minimum analysis of:
- critical pixel area;
- critical-region dimensions;
- contrast;
- font/font size;
- position / patch alignment when possible;
- stroke thickness when reliably measurable.

## Evidence
None yet.

## Decision
None yet.

## Consequence
- effect largely explained by generic visual properties → reframe as generic micro-detail robustness;
- residual component effect remains → orthographic structure becomes a plausible contributor, not yet a proven mechanism;
- inconclusive → do not advance a Thai-specific claim.

---

# Gate 3 — Failure localization

**Status:** BLOCKED

**Requires:** Gate 2 decision sufficient to justify localization work

## Question
Where does degradation primarily emerge under controlled interventions?

Compare clearly separated families such as:
- input-resolution reduction;
- pre-encoder reduction when included;
- post-encoder pruning;
- merging/pooling when included.

## Evidence
None yet.

## Decision
None yet.

## Consequence
Use wording such as `failure localization` unless stronger mechanistic evidence is collected.

---

# Gate 4 — Unresolved gap after existing methods

**Status:** BLOCKED

**Requires:** prior stages establish a meaningful failure worth testing

## Question
After fair evaluation of strong compatible existing methods, does a meaningful
unresolved failure remain?

## Evidence required
- strongest compatible baselines identified from current literature;
- fair matched-budget comparison;
- compatibility limitations documented;
- accuracy–resource trade-off reported.

## Evidence
None yet.

## Decision
None yet.

## Consequence
- PASS → a meaningful unresolved failure remains; Stage 5 may be considered
  only after human approval;
- FAIL → existing methods address the failure sufficiently; do not force a new
  method and retain an evaluation/analysis contribution;
- INCONCLUSIVE → Stage 5 remains blocked.

---

# Gate 5 — New-method value

**Status:** BLOCKED

**Requires:** Gate 4 = human-approved PASS, meaning that a meaningful unresolved
failure remains after fair evaluation of strong compatible existing methods.

## Question
Does the proposed distinction-preserving method improve the accuracy–resource trade-off compared with strong baselines?

## Evidence required
- matched budgets;
- multiple budgets, not one cherry-picked operating point;
- ablations;
- raw predictions;
- compute/resource measures where feasible.

## Evidence
None yet.

## Decision
None yet.

---

# Gate 6 — External validity

**Status:** BLOCKED

## Question
Do key findings extend beyond controlled synthetic data and beyond a single architecture?

## Evidence required
- real-world Thai text/OCR evaluation where appropriate;
- at least one additional architecture if feasible;
- claim boundaries explicitly updated.

## Evidence
None yet.

## Decision
None yet.

---

# Decision entry template

## 2026-09-06 — Stage 0 preparation and calibration authorization

**Stage/Gate:** Steps 4–6 / Stage 0 Measurement Validity

**Decision owner:** Human researcher

**Decision:** Record Step 3 as `COMPLETE`. Authorize Stage 0 dataset,
measurement-pipeline, and calibration preparation, including an uncompressed
Qwen2.5-VL-3B baseline and optional use of the verified Kaggle backend.

Locked Stage 0 validation may not begin until candidate/design review,
calibration evidence, a Gate 0 criteria proposal, and a separate human freeze
are recorded. Gate 0 itself is not approved.

### Evidence

- research contract: `docs/RESEARCH_SPEC.md`
- protocol: `docs/EXPERIMENT_PROTOCOL.md`
- execution plan: `docs/exec-plans/active/STAGE0_MEASUREMENT_VALIDITY.md`
- backend record: `docs/architecture/KAGGLE_BACKEND.md`

### Reasoning

Step 3 resolved primary-backbone feasibility. Stage 0 now needs to test the
measurement system at full information before any compression intervention.
Pair inclusion must be decided without viewing model outcomes, and Gate 0
criteria must be derived from calibration rather than invented in advance.

### Alternatives considered

- proceed directly to locked validation;
- run compression before measurement validity;
- use a fixed candidate count or universal accuracy threshold.

All are inconsistent with the approved protocol.

### Known limitations

- The candidate inventory and rendering-factor pool are not human-frozen.
- No Stage 0 model outcome exists yet.
- The smallest later-stage effect of interest and numeric Gate 0 criteria are
  unresolved.
- Kaggle engineering feasibility does not guarantee a valid scientific run.

### Consequence for next stage

Prepare Checkpoint A: candidate-pair inventory, automated Unicode/rendering
audit, proposed calibration allocation, prompt/parser, metrics, and backend
workload contract. Do not open model outcomes until the human freezes the
Checkpoint A design.

### Files/configs affected

- `configs/stage0/`
- `docs/exec-plans/active/ADVISOR_READINESS.md`
- `docs/exec-plans/active/STAGE0_MEASUREMENT_VALIDITY.md`

---

## 2026-09-06 — Human smoke approval and Step 3 completion

**Stage/Gate:** Step 3 — Sequential backbone feasibility

**Decision owner:** Human researcher

**Human approval record:** `Step 3 smoke review: APPROVED` for both frozen
Latin A/B controls.

**Decision:** Step 3 = `COMPLETE`. Retain
`Qwen/Qwen2.5-VL-3B-Instruct@66285546d2b821cf421d4f5eb2576359d3770cd3`
as the primary backbone. Do not open the secondary backbone.

### Evidence

- local run IDs: `20260904T064824Z_3280bbdf`,
  `20260904T064919Z_3280bbdf`, and `20260904T065945Z_3280bbdf`;
- architecture record: `docs/architecture/QWEN2_5_VL_3B.md`;
- human approval instruction received on 2026-09-06 for the two frozen smoke
  images.

### Reasoning

The processor, prompt, and runtime Vision Encoder counts agree at 256 visual
positions for each control; deterministic inference reproduced A→A and B→B;
and the human researcher approved the rendered smoke images. No recorded
secondary-backbone trigger remains.

### Known limitations

- The controls contain Latin A/B, not Thai linguistic stimuli.
- This is an engineering-feasibility decision, not Stage 0 measurement
  validity or evidence for H1–H4.
- Completion does not authorize Step 4, candidate-pair work, Stage 0, or any
  compression intervention.

### Consequence for next stage

The Step 3 prerequisite is resolved. Steps 4 and later remain blocked until
the human researcher explicitly authorizes them and records their required
decisions.

### Files/configs affected

- `docs/ARCHITECTURE.md`
- `docs/architecture/QWEN2_5_VL_3B.md`
- `docs/CLAIMS.md`
- `docs/CONSISTENCY_REVIEW.md`
- `docs/exec-plans/active/ADVISOR_READINESS.md`

---

## 2026-09-06 — Kaggle T4 backend feasibility proposal

**Stage/Gate:** Engineering backend feasibility; not a scientific gate

**Decision owner:** Human researcher; Codex recommendation recorded below

**Decision:** `KAGGLE_BACKEND_FEASIBLE_PROPOSED`. The backend implementation
is merged into `main`, the branch designated for continued research. Final
backend adoption remains a human decision.

### Evidence

- run ID: `kaggle-step3-6c17245ae8a6`;
- source commit: `6c17245ae8a6f25b1f428bcba9a12336674ade3f`;
- Kaggle kernel status: `COMPLETE`;
- local artifact verification: `VERIFIED`;
- observed accelerator: Tesla T4, compute capability 7.5;
- architecture record: `docs/architecture/KAGGLE_BACKEND.md`.

### Reasoning

The remote run reproduced A→A and B→B, matched all three token-count
observations at 256, used the pinned model and processor revision, and passed
all hard provenance, environment, accelerator, checksum, and artifact checks.
This demonstrates a viable execution path for the Step 3 smoke workload.

### Known limitations

- The run is one non-scientific two-image smoke workload, not a benchmark or
  experiment.
- The immutable run manifest predates human smoke approval and therefore keeps
  `PENDING_HUMAN_REVIEW`; the later approval is recorded in the preceding
  Decision Log entry rather than rewriting the artifact.
- The verified run sourced `refs/heads/infra/kaggle-phase1`; the operational
  profile now targets `refs/heads/main` and must pin each future run's exact
  commit.
- No Stage 0, Thai-rendering, Resolution Reduction, Token Pruning, H1, or
  cross-architecture claim follows from this proposal.

### Consequence for next stage

The Kaggle T4 backend may be considered for separately authorized future work.
The proposal neither starts Stage 0 nor approves a scientific gate.

### Files/configs affected

- `configs/runtime/kaggle_t4.yaml`
- `docs/ARCHITECTURE.md`
- `docs/architecture/KAGGLE_BACKEND.md`
- `docs/CLAIMS.md`
- `docs/exec-plans/active/ADVISOR_READINESS.md`

---

## 2026-09-04 — Primary-backbone feasibility proposal

**Stage/Gate:** Step 3 — Sequential backbone feasibility

**Decision owner:** Human researcher; Codex recommendation recorded below

**Decision:** `PRIMARY_FEASIBLE_PROPOSED`. Keep
`Qwen/Qwen2.5-VL-3B-Instruct` as the primary backbone. Do not open the
secondary backbone. Final Step 3 completion awaits human review of the two
non-scientific smoke images.

### Evidence

- run IDs: `20260904T064824Z_3280bbdf`,
  `20260904T064919Z_3280bbdf`, `20260904T065945Z_3280bbdf`
- analysis artifact: `docs/architecture/QWEN2_5_VL_3B.md`
- relevant official model revision:
  `Qwen/Qwen2.5-VL-3B-Instruct@66285546d2b821cf421d4f5eb2576359d3770cd3`

### Reasoning

The pinned primary processor and model run locally. Processor grid accounting,
language-model image-token positions, and runtime Vision Encoder output length
agree at 256 for both smoke images across two deterministic inference runs.
The raw outputs are reproducible, and local RAM is sufficient for this tiny
smoke configuration.

### Alternatives considered

- open Qwen3-VL as a secondary backbone;
- select a backbone based on degradation behavior.

Neither is justified: the primary did not hit a recorded secondary trigger,
and no compression effect was evaluated.

### Known limitations

- Smoke images are Latin A/B controls, not Thai linguistic data.
- Smoke-image human review is pending.
- CPU latency is high and only two examples were timed.
- The first model-load time includes the initial weights download.
- No Stage 0 measurement validity or H1 evidence has been produced.

### Consequence for next stage

After human smoke-image approval, Step 3 can be marked complete. Step 4 remains
blocked until that approval and explicit authorization to proceed.

### Files/configs affected

- `configs/step3/qwen25_vl_3b.yaml`
- `docs/ARCHITECTURE.md`
- `docs/architecture/QWEN2_5_VL_3B.md`
- `docs/exec-plans/active/ADVISOR_READINESS.md`

---

## 2026-09-04 — Provisional novelty framing and H1 direction

**Stage/Gate:** Pre-Stage 3 research governance

**Decision owner:** Human researcher

**Decision:** Proceed provisionally under an evaluation/diagnostic framing.
Freeze H1 as a non-directional `component_type × budget` interaction.
Authorize Step 3 only.

### Evidence

- analysis artifact: `docs/NOVELTY_TRIAGE.md`
- relevant literature: `docs/LITERATURE.md`

### Reasoning

The bounded review leaves a candidate controlled Thai orthographic diagnostic
gap but does not justify a new-method claim. A non-directional interaction does
not assume that any component degrades faster.

### Alternatives considered

- directional H1 without additional rationale;
- generic micro-detail pivot before measurement feasibility;
- new-method development.

### Known limitations

The novelty decision is provisional and must be revisited if new comparable
work is found. Step 3 does not test H1 and cannot support a degradation claim.

### Consequence for next stage

Step 3 primary-backbone feasibility is eligible. Steps 4 and later remain
blocked pending Step 3 evidence and their own required decisions.

### Files/configs affected

- `docs/NOVELTY_TRIAGE.md`
- `docs/RESEARCH_SPEC.md`
- `docs/CLAIMS.md`
- `docs/DECISION_LOG.md`
- `docs/exec-plans/active/ADVISOR_READINESS.md`

---

## 2026-09-04 — Advisor Readiness implementation contract

**Stage/Gate:** Evidence foundation through Advisor Readiness

**Decision owner:** Human researcher

**Decision:** Implement the approved staged plan with Stage 1A as a conditional
Resolution Sensitivity Pilot, calibration-derived Gate 0 criteria, `pair_id` as
the independent analysis unit, sequential backbone feasibility, and explicit
advisor evidence-status labels.

### Evidence

- analysis artifact: `docs/CONSISTENCY_REVIEW.md`
- relevant literature: `docs/LITERATURE.md`

### Reasoning

The contract front-loads novelty and measurement kill-tests and prevents
Resolution Reduction evidence from being treated as direct evidence about
post-encoder Token Pruning.

### Alternatives considered

- fixed universal Gate 0 thresholds;
- fixed canonical pair counts before validity review;
- simultaneous backbone comparison;
- treating Resolution Reduction as a proxy test of post-encoder pruning.

These alternatives were rejected in the approved plan.

### Known limitations

This entry approves the process constraints only. It does not approve the
provisional novelty framing, H1 directionality, any dataset item, any gate
outcome, secondary-backbone use, Stage 1A execution, or A100 use.

### Consequence for next stage

Complete literature triage and Source-of-Truth reconciliation, then pause for
the remaining human decisions before model or dataset implementation.

### Files/configs affected

- `docs/RESEARCH_SPEC.md`
- `docs/EXPERIMENT_PROTOCOL.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISION_LOG.md`
- `docs/CLAIMS.md`

---

## Entry template

Copy this block whenever a substantive scientific decision is made.

```md
## YYYY-MM-DD — <decision title>

**Stage/Gate:**
**Decision owner:** Human researcher
**Decision:**

### Evidence
- run IDs:
- analysis artifact:
- relevant literature:

### Reasoning

### Alternatives considered

### Known limitations

### Consequence for next stage

### Files/configs affected
```
