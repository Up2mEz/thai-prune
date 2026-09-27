# Specialization Pivot Review

> Status: `NOT_PURSUED_DUE_TO_USAGE_TERMS`
> Date audited: 2026-09-12
> Evidence scope: primary-source provenance/literature audit and experiment
> design only. No model inference, locked-data access, compression, fine-tuning,
> or new-method implementation was performed.

> Human decision recorded 2026-09-12: do not pursue Typhoon OCR because the
> current OpenTyphoon Terms create an operational prior-written-consent
> dependency for competitive benchmarking. This is not a scientific rejection.
> All provenance, architecture, literature, and proposed-design material below
> is retained as historical audit evidence. No Typhoon inference, smoke,
> compression, or benchmarking is authorized.

## 1. Proposed research question

> Does OCR specialization change robustness to visual-information reduction,
> and does that effect differ across Thai orthographic component types?

The defensible description of the proposed pair is:

> a closely related base and OCR-specialized descendant

Do not describe the pair as identical models differing only by fine-tuning.
The public artifacts establish matched architecture/config structure and a
declared base-model relationship, but they do not identify the immutable
parent revision or prove that OCR SFT was the only causal difference.

The primary future hypothesis remains non-directional:

```text
MODEL x BUDGET
```

`MODEL x BUDGET x COMPONENT` is secondary/descriptive until Stage S0 shows
adequate measurement capacity at the component level.

## 2. Provenance and architecture audit

The machine-readable record is
[`architecture/QWEN3VL2B_TYPHOON_OCR15_CONFIG_DIFF.json`](architecture/QWEN3VL2B_TYPHOON_OCR15_CONFIG_DIFF.json).

| Field | Base | OCR-specialized descendant | Audit conclusion |
|---|---|---|---|
| Exact model ID | `Qwen/Qwen3-VL-2B-Instruct` | `typhoon-ai/typhoon-ocr1.5-2b` | Exact current official repositories |
| Frozen revision | `89644892e4d85e24eaac8bacfd4f463576704203` | `15b381a2d62569e6736f9c085859dff68e48608d` | Immutable commit SHAs captured from HF API |
| HF license tag | `apache-2.0` | `apache-2.0` | Typhoon has an additional terms notice; see legal gate below |
| Declared provenance | Original Qwen checkpoint | HF metadata declares `base_model:finetune:Qwen/Qwen3-VL-2B-Instruct` | Parent revision is not declared |
| Architecture | `Qwen3VLForConditionalGeneration` | same | Matched config class |
| BF16 parameters | 2,127,532,032 | 2,127,532,032 | Exact HF safetensors metadata match |
| Text config | 28 layers, hidden 2,048, 16 heads, 8 KV heads | same | Match after ignoring serialization metadata |
| Vision Encoder | depth 24, hidden 1,024, 16 heads | same | Config match |
| Patch / spatial merge | 16 / 2 | 16 / 2 | Config match |
| DeepStack | indexes `[5, 11, 17]` | same | Three multi-level injection points declared |
| Processor core | `Qwen3VLProcessor`, `Qwen2VLImageProcessorFast` | same | Core size/normalization/patch fields match; Typhoon serializes more defaults explicitly |
| Tokenizer | `Qwen2Tokenizer`; 151,643 base vocab entries; 26 added tokens | same semantic vocab and merge sequence | Serialization differs; runtime equivalence remains untested |
| State dict header | 625 tensor keys | 625 tensor keys | All names, shapes, dtypes, and byte lengths match |
| Weight artifact | 4,255,140,312 bytes | same size | Different repository blob IDs; values were not compared |

The matched header means an architecture-level paired implementation is
plausible. It does **not** show that the learned weights differ only because
of OCR specialization, nor does it localize any change to Vision Encoder,
DeepStack, language model, or output head.

### Config differences that matter operationally

- Typhoon serializes `dtype=bfloat16` at top level and under
  `vision_config`; the base config omits those redundant fields.
- Recorded `transformers_version` differs.
- `generation_config.json` differs in BOS/EOS serialization and an omitted
  `repetition_penalty` default. Scientific runs must override and record a
  single deterministic decoding contract rather than inherit either file.
- The vocabulary and BPE merge sequence are semantically identical, but
  tokenizer serialization differs (`merges` strings versus arrays, an
  explicit `ignore_merges=false`, and different chat-template file layout).
  Runtime tokenization must still be smoke-tested at the pinned revisions.

### Official Typhoon prompt and output envelope

The exact 18-line prompt is frozen by the pinned
[Typhoon README lines 91-108](https://huggingface.co/typhoon-ai/typhoon-ocr1.5-2b/blob/15b381a2d62569e6736f9c085859dff68e48608d/README.md#L91-L108),
beginning `Extract all text from the image.` Its UTF-8 SHA-256 is
`0e6c57af282f83f3dfdfa30e33bb8e74e0e1addd974f6ee111c1c22b3d47594d`.
The model card specifies clean Markdown, HTML tables, LaTeX equations,
`<figure>` blocks, `<page_number>` tags, and checkbox glyphs. It also warns
that the model is task-specific and intended for the provided prompt.

The model card's Transformers example resizes pages up to a maximum dimension
of 1,800 px and slices generated IDs after the input IDs. These are interface
and training-distribution considerations, not evidence that 1,800 px is the
correct scientific budget for the controlled stimuli.

### Legal/terms gate

The HF repositories display `apache-2.0`, but the Typhoon model card also says
use is subject to the [OpenTyphoon Terms](https://opentyphoon.ai/tac). The
terms visible on 2026-09-12 prohibit competitive benchmarking without prior
express written consent and state that they apply through third-party/open
channels. Because the proposed work compares Typhoon with its declared base,
future inference is blocked under:

```text
LEGAL_TERMS_CLEARANCE_REQUIRED
```

This document does not give legal advice. Before any smoke or Stage S0 model
run, obtain written permission from SCB DataX/OpenTyphoon or a qualified legal
determination that the planned academic comparison is permitted. Archive the
terms snapshot and clearance with the run protocol.

## 3. Revised novelty boundary

The literature record was refreshed through 2026-09-12. This remains a
bounded primary-source search, not proof of absence.

| Question/claim | Status | Primary evidence | Consequence |
|---|---|---|---|
| Thai/OCR specialization can improve OCR/document extraction | `ALREADY_ESTABLISHED` at document-benchmark level | [Typhoon OCR report](https://arxiv.org/abs/2601.14722) reports full-parameter SFT of Qwen3-VL 2B and Thai document evaluations | Do not claim specialization itself is novel; results do not establish compression robustness or isolated orthographic capacity |
| OCR can be sensitive to permanent visual-token loss | `ALREADY_ESTABLISHED` as prior-work evidence | [FastOCR](https://arxiv.org/abs/2605.17447) motivates dynamic access because permanent eviction can harm dense OCR | Treat as background, not a universal law or a project result |
| OCR-aware reduction methods exist | `ALREADY_ESTABLISHED` | [FastOCR](https://arxiv.org/abs/2605.17447), [ET-Prune](https://arxiv.org/abs/2608.01979), [RTPrune](https://arxiv.org/abs/2605.00392) | No new-method motivation from “OCR needs special handling” alone |
| Text/evidence-aware pruning exists | `ALREADY_ESTABLISHED` | ET-Prune and earlier text-guided methods in `LITERATURE.md` | Evidence-aware selection is not novel by itself |
| Generic benchmarks can be inadequate for compression evaluation | `ALREADY_ESTABLISHED` | [VTC-Bench](https://aclanthology.org/2026.acl-long.195/) identifies task mismatch | Controlled Thai evaluation may be useful, but benchmark inadequacy is not the contribution |
| OCR specialization changes the degradation curve under matched visual-information reduction | `CANDIDATE_GAP` | No inspected source jointly tested the declared base/descendant pair, controlled budgets, and Thai orthographic components | Eligible only after provenance, terms, prompt fairness, and S0 capacity gates |
| Thai component types differ in that specialization effect | `CANDIDATE_SECONDARY_GAP` | Not found in the bounded search | Keep three-way interaction secondary until supported by capacity |

The candidate contribution is a specialization-robustness evaluation, not a
compression method. A defensible novelty statement must say that the bounded
search did not locate the full combination; it must not claim “first.”

## 4. Proposed stage-gate amendment

This map supersedes nothing until human approval. Historical Stage 0/Qwen2.5
and Qwen3.5 records remain diagnostic history under their original contracts.

| Stage | Question | Allowed evidence/action | Entry condition | Stop/falsifier |
|---|---|---|---|---|
| S0 — matched specialization baseline feasibility | Can both checkpoints validly transcribe controlled Thai targets at full visual information? | Open calibration only; no compression | Terms clearance, pinned revisions, frozen prompt/parser, smoke pass | Stop or redesign before scientific screening if either model cannot execute a fair contract; do not open locked data |
| S1 — Resolution Reduction pilot | Is a measurable degradation curve plausible under input-resolution change? | Preliminary open-calibration pilot only | Human-approved S0 measurement capacity | Stop if realized budgets duplicate, baselines lack headroom, or precision is inadequate |
| S2 — registered specialization x resolution | Does `MODEL x BUDGET` exist? | Locked registered Resolution Reduction experiment | Human-approved protocol/gate after S1 | `FAIL`/`INCONCLUSIVE` is valid; do not rescue by changing prompts or budgets |
| S3 — direct post-encoder reduction | Does direct LLM-boundary token reduction behave differently? | Architecture-validated direct intervention with actual counts | Independent access/count validation and new authorization | Stop if features, placeholders, RoPE/positions, or DeepStack accounting cannot be kept consistent |
| S4 — strong compatible existing methods | Do compatible OCR-aware methods remove the residual failure? | Audited implementations only | Meaningful residual failure and compatibility review | Do not force FastOCR/ET-Prune/RTPrune into incompatible architecture |
| S5 — new method | Does an unresolved failure justify method development? | New-method work | Existing strong methods fail under fair evaluation and human approves | If existing methods solve it, record `NO_NEW_METHOD_REQUIRED` |

Resolution Reduction evidence is never evidence for post-encoder Token
Pruning. FastOCR-style dynamic decoding access is also a distinct mechanism
from permanent token deletion.

## 5. Exact proposed Stage S0 workload

### Sampling unit and cells

- Reuse only the frozen 25 open-calibration `pair_id` subset after verifying
  that every selected render and label remains scientifically valid.
- Five `pair_id` per component category across five categories = 25
  independent linguistic units.
- Both pair members x two frozen fonts x two frozen sizes = eight repeated
  renders per `pair_id`.
- Therefore: 200 images/observations per model and 400 calls for the two-model
  shared-contract screen.
- `pair_id`, not 400 calls or 200 images, remains the independent unit.
- Do not use locked pairs. Do not add jitter, backgrounds, or new sizes after
  observing model outcomes.

Primary S0 outcome: exact target transcription at full visual information,
with parser/contract failure reported separately. Secondary diagnostics may
include Unicode code-point CER, grapheme-aware error categories, component
retention, font/size strata, and within-pair model contrasts. Component-level
estimates are descriptive with only five independent pairs per category.

### Parser contract

Use one deterministic parser for both models:

1. save raw output and generated token IDs;
2. decode with the same processor settings and no model-specific cleanup;
3. normalize line endings and remove only outer Unicode whitespace;
4. preserve both raw code points and NFC diagnostics;
5. accept a response only when the remaining output is exactly the displayed
   target string;
6. label Markdown/HTML wrappers, explanations, empty outputs, multiple strings,
   or undecodable text as explicit contract failures rather than silently
   repairing them.

Freeze parser tests before any model response is observed.

### Capacity decision to propose for human freezing

Do not invent a universal numeric pass threshold. Before S0, the human should
freeze a decision rule tied to the smallest Stage S2 interaction worth
detecting. At minimum it must address:

- baseline exact-transcription accuracy and headroom for both models;
- pair-clustered uncertainty overall and by component;
- parser/contract failure ceiling;
- font/size dependence;
- deterministic repeat agreement on the non-scientific smoke; and
- whether five pairs per component can support anything beyond descriptive
  three-way estimates.

## 6. Prompt/output-contract fairness

### Preferred contract

After legal clearance, first test the exact pinned Typhoon OCR prompt on both
models in the non-scientific smoke. If both execute its output envelope, freeze
that identical prompt, identical images, deterministic decoding override, and
identical parser for the 400-call S0 screen. This best isolates checkpoint
differences while acknowledging that the prompt is optimized for Typhoon.

### Pre-outcome fallback

If the smoke—not S0 outcomes—shows the base cannot execute the official
Typhoon contract, freeze a two-contract sensitivity design before S0:

- Contract A: one short shared semantic OCR instruction for both models,
  written and hashed before inference.
- Contract B: Typhoon's official pinned prompt versus a predeclared Qwen
  general-chat OCR instruction. Qwen publishes an interface, not an exact
  OCR-native prompt, so this cell is unavoidably researcher-specified.

The two-contract design has 200 images x two models x two contracts = 800
calls. Report Contract A as the cleaner checkpoint comparison and Contract B
as capability under each interface. A model-by-contract interaction indicates
prompt/interface sensitivity; it cannot be attributed solely to specialization.
Never choose the better prompt per model after seeing scientific results.

## 7. Engineering smoke proposal

Run only after terms clearance. This smoke is explicitly non-scientific and
must live in a separate run namespace.

Proposed fixed set per model/contract:

- one large Latin control;
- one large common Thai string;
- three already exposed minimal-pair examples spanning base, upper/lower, and
  stacked-mark behavior;
- one exact deterministic rerun of every item.

With five images, two models, and one shared contract this is 20 calls
(5 x 2 x original/rerun). Under the two-contract fallback it is 40 calls.

Smoke checks only: checkpoint load, chat template, image processor, generation
slicing, Unicode decoding, parser status, byte-identical deterministic rerun,
Vision Encoder grid, pre-merge patches, post-merge primary visual positions,
DeepStack metadata, LLM image-placeholder count, peak VRAM/RAM, and latency.
Accuracy must not enter S0 or any scientific report.

## 8. Compute estimate and budget accounting

The BF16 weight file is 4.255 GB (3.963 GiB) per model. Models should load
sequentially on a 16 GiB Tesla T4; simultaneous residency is unnecessary and
would reduce activation headroom. Actual feasibility remains unknown because
attention implementation, prompt length, image grid, KV cache, and generated
length determine peak memory.

| Proposed work | Calls | Planning estimate |
|---|---:|---|
| Shared-contract smoke | 20 | Measure, do not extrapolate accuracy |
| Shared-contract S0 | 400 | `400 x measured median seconds/call`; add two model-load times |
| Two-contract smoke | 40 | Only if pre-outcome fallback is activated |
| Two-contract S0 | 800 | Sensitivity design; approximately twice the shared-contract calls |

For scheduling only, the call-time scenarios below exclude model loading,
artifact upload/download, and retries; they are not measured forecasts:

| Median call time assumption | Shared S0 (400) | Two-contract S0 (800) |
|---:|---:|---:|
| 2 s | 0.22 GPU-h | 0.44 GPU-h |
| 5 s | 0.56 GPU-h | 1.11 GPU-h |
| 10 s | 1.11 GPU-h | 2.22 GPU-h |

Do not publish an invented wall-clock estimate. After the smoke, compute:

```text
estimated_GPU_hours =
  sum_over_model_contract_cells(load_seconds + calls * p50_seconds_per_call)
  / 3600
```

Also report p90 latency and peak allocated/reserved GPU memory. Typhoon's
official page-oriented prompt allows long generation, but S0 uses isolated
short targets; freeze the smallest safe `max_new_tokens` before the scientific
screen and count contract truncation separately.

## 9. Future compression accounting

Before S1 inference, generate a processor-only mapping artifact for each pinned
revision:

```text
requested image resolution
-> actual preprocessed height/width
-> processor grid_thw
-> pre-merge patch count
-> post-merge primary visual positions
-> DeepStack feature accounting
-> runtime LLM image-placeholder positions
```

Candidate square requests may include 448, 384, 320, and 256 px only to map
processor behavior. Do not label their nominal percentages as budgets until
both processors realize and runtime hooks confirm the counts. If both models
map a request differently, match on realized counts where scientifically
possible and report the mismatch rather than silently coercing it.

Keep these mechanism labels separate in configs and reports:

1. `INPUT_RESOLUTION_REDUCTION`
2. `PRE_ENCODER_REDUCTION`
3. `POST_ENCODER_TOKEN_PRUNING`
4. `TOKEN_MERGING_OR_POOLING`
5. `DYNAMIC_DECODING_TOKEN_ACCESS`

## 10. Risks and falsifiers

| Risk/falsifier | What would be observed | Required consequence |
|---|---|---|
| Terms prohibit the comparison | No written permission/clearance | Do not run; keep pivot pending or choose a legally usable model pair |
| Parent provenance is underidentified | No immutable Typhoon parent revision/training lineage | Keep causal language observational; do not say “only fine-tuning differs” |
| Prompt specialization dominates | Strong model x contract interaction or base cannot execute Typhoon prompt | Separate interface from capability; S0 may be inconclusive |
| Baseline capacity is insufficient | Low exact transcription or high contract failures at full information | Stop before S1; no compression conclusion |
| Ceiling leaves no degradation headroom | Near-perfect but too-small/low-power component cells | Expand open calibration or redesign before locked work; no post-outcome patching |
| Five pairs/category lack precision | Wide pair-clustered intervals | Three-way interaction remains descriptive; increase independent pairs only by new approval |
| Training-data overlap | Controlled strings/fonts plausibly overlap Typhoon synthetic training | Treat as unknown contamination; add overlap/provenance analysis where possible |
| Processor/runtime mismatch | Different realized grids/counts or placeholder mismatch | Do not call nominal resolutions matched budgets |
| DeepStack accounting is incomplete | Primary tokens match but multi-level features differ/untracked | Block S3 and causal compute claims |
| Existing methods solve the effect | Residual failure disappears in fair S4 tests | Record `NO_NEW_METHOD_REQUIRED`; do not invent S5 motivation |
| No `MODEL x BUDGET` interaction | Registered estimate is negligible or imprecise | Report `FAIL` or `INCONCLUSIVE`; do not switch directionality or budgets |

## 11. Historical proposed Source-of-Truth amendments

The following changes record the proposal as it stood before the human
decision. They are retained for provenance, not active authorization:

- `RESEARCH_SPEC.md`: add the specialization research question, non-directional
  `MODEL x BUDGET` primary hypothesis, conditional component interaction, and
  S0-S5 map.
- `EXPERIMENT_PROTOCOL.md`: add the matched model IDs/revisions, prompt fairness
  decision, exact S0 workload, parser rules, terms gate, sequential loading,
  and realized-budget mapping requirement.
- `DECISION_LOG.md`: the historical proposal used
  `SPECIALIZATION_PIVOT_PENDING_HUMAN_REVIEW`; the current Typhoon status is
  `NOT_PURSUED_DUE_TO_USAGE_TERMS`. All Qwen2.5/Qwen3.5 decisions and
  `Gate 0 = NOT_RUN` remain preserved.
- `CLAIMS.md`: add the provenance facts as bounded architecture audit evidence,
  the new research question as `HYPOTHESIS`, and explicit forbidden causal,
  robustness, component, attention, representation, and new-method claims.

## 12. Closed branch boundary

The researcher decided not to pursue this branch because its consent
dependency is operationally unacceptable. The former checklist is superseded;
no Typhoon inference, smoke, benchmarking, or compression may be scheduled.

Current terminal state:

```text
NOT_PURSUED_DUE_TO_USAGE_TERMS
```
