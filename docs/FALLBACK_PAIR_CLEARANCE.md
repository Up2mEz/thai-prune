# PaddleOCR-VL / Wayu-Paxa Fallback Pair Clearance

> Status: `APPROVED_FOR_S0_OPEN_CALIBRATION_BASELINE_ONLY`
> Audited: 2026-09-12
> Scope: current official terms, model cards, immutable repository metadata,
> safetensors headers, configuration, processor, tokenizer, and source code.
> No inference, locked-data access, compression, or fine-tuning was performed.

## 1. Decision summary

- Terms classification: `TERMS_CLEAR`.
- Recommendation: `APPROVE_PADDLE_WAYU_FOR_ENGINEERING_SMOKE`.
- Defensible pair description: **PaddleOCR-VL-1.6 base and its
  Thai-specialized full-finetuned descendant**.
- This is a recommendation for a non-scientific smoke only. It is not human
  approval, a Gate 0 decision, or evidence for robustness under compression.

The revised research question is:

> Does Thai-specific OCR adaptation change robustness to controlled
> visual-information reduction?

For this particular candidate pair, “specialization” means additional Thai
OCR full fine-tuning of an already OCR-specialized multilingual/document OCR
base. The primary comparison is therefore base OCR VLM versus Thai-specialized
OCR descendant, not general-purpose VLM versus OCR model. The declared
45,723-page synthetic training set is not assumed to be the only difference.

## 2. Terms and license audit

| Artifact | Governing text found | Finding |
|---|---|---|
| `PaddlePaddle/PaddleOCR-VL-1.6` | HF repository license tag and `LICENSE` | Apache License 2.0 |
| `wayu-ai/wayu-paxa-ocr-zero` | Model card license section | Apache-2.0, plus incorporated Wayu Research Acceptable Use terms |
| Wayu additional terms | Wayu Terms of Use, updated 2026-08-31 | Artifact license controls in a conflict; the Acceptable Use section applies when incorporated by a model card |

The current Wayu Acceptable Use list prohibits impersonation, deception,
unlawful/harmful uses, rights/privacy/law violations, sole-basis significant
decisions and safety-critical deployment, burdensome automated access, false
affiliation, and abusive/harmful conduct. It contains no clause requiring prior
consent for comparative or competitive benchmarking.

Under the inspected texts, benign academic comparative benchmarking,
publication of truthful aggregate results, model modification, representation
extraction, Token Pruning, and Resolution Reduction experiments are not
prohibited. Apache-2.0 expressly permits use and derivative works. This is a
research governance reading, not legal advice.

Redistribution is permitted subject to Apache-2.0 Section 4: include the
license, mark modified files, retain applicable notices, and propagate NOTICE
attribution. Reproducibility can instead pin public revisions and publish
code/config/checksums. Modified-weight redistribution would retain these
duties and the Wayu Acceptable Use terms.

**Classification: `TERMS_CLEAR`.** Re-snapshot and hash the applicable model
cards, licenses, and Wayu Terms before any authorized run because the Wayu
page says its terms may change.

Primary sources:

- <https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6>
- <https://huggingface.co/wayu-ai/wayu-paxa-ocr-zero>
- <https://www.wayuresearch.org/terms>
- <https://www.apache.org/licenses/LICENSE-2.0>

## 3. Provenance and structural audit

### 3.1 Immutable identities

| Field | Base | Specialized |
|---|---|---|
| Model ID | `PaddlePaddle/PaddleOCR-VL-1.6` | `wayu-ai/wayu-paxa-ocr-zero` |
| Audited revision | `c5630abae1d940eafe0697512a0325494b02ab42` | `af0204b4f334a6d5068b6bac2b3738932d6e289b` |
| Declared base | not applicable | `PaddlePaddle/PaddleOCR-VL-1.6` |
| Training relationship | base checkpoint | full fine-tune; all 0.9B parameters updated |
| Training data | existing PaddleOCR-VL-1.6 lineage | 45,723 synthetic pages from public English-source documents; no real Thai-document OCR label declared |
| BF16 parameter count from HF metadata | 958,588,736 | 905,601,648 |

Wayu does not identify the immutable base revision used for fine-tuning.
Therefore the evidence supports a declared descendant relationship, not an
exact causal minimal pair or a claim that training data is the only difference.

### 3.2 Architecture and interface

Both configs describe `PaddleOCRVLForConditionalGeneration` with an 18-layer,
hidden-size-1024 ERNIE language model and a 27-layer, hidden-size-1152 Vision
Encoder. Both use `patch_size=14`, `spatial_merge_size=2`, a 4608-to-1024
projector, the same core image-processor limits, and the same `OCR:` prompt.
The pinned repositories expose the same `chat_template.jinja` blob and the
same `tokenizer.model` blob.

The base repository contains older remote custom code, whereas Wayu uses the
native Transformers `paddleocr_vl` implementation. Runtime equivalence must be
frozen and checked in the proposed smoke; configs alone do not establish it.

### 3.3 State-dict evidence

- Base header: 620 tensors.
- Wayu header: 608 tensors.
- All 608 Wayu keys exist in the base with equal shapes and dtypes.
- Wayu has no additional keys.
- The base-only 12 tensors are
  `visual.vision_model.embeddings.packing_position_embedding.weight` and 11
  `visual.vision_model.head.*` tensors.

The native Transformers implementation explicitly ignores the packing
position embedding and vision head as legacy load keys. The inspected
generative path does not use the vision pooling/classification head. This
supports core structural compatibility, not equality of common weight values.
Machine-readable evidence is in
`architecture/PADDLEOCRVL16_WAYU_PAXA_CONFIG_DIFF.json`.

Pinned primary sources:

- <https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6/tree/c5630abae1d940eafe0697512a0325494b02ab42>
- <https://huggingface.co/wayu-ai/wayu-paxa-ocr-zero/tree/af0204b4f334a6d5068b6bac2b3738932d6e289b>
- <https://arxiv.org/html/2609.03595v1>
- <https://raw.githubusercontent.com/huggingface/transformers/v5.12.1/src/transformers/models/paddleocr_vl/modeling_paddleocr_vl.py>

## 4. Source-only compression feasibility

Let `t, h, w = image_grid_thw`. The processor makes `h` and `w` divisible by
the 2x2 spatial merge:

- pre-merge positions: `N_pre = t * h * w`;
- projector/LLM-boundary positions: `N_llm = t * (h / 2) * (w / 2)`.

| Location | Tensor / shape logic | Native module path | Observe/count | Intervention feasibility |
|---|---|---|---|---|
| A. Input resolution | image and `image_grid_thw` | `processor.image_processor` | Yes: pixels, grid, `N_pre`, `N_llm` | Yes through frozen processor controls; this is Resolution Reduction |
| B. Vision patch sequence | embeddings `[N_pre, 1152]` | `model.visual.vision_model.embeddings.patch_embedding` / encoder input | Yes | Conditional/high risk: removal must update grid, cumulative lengths, and position/RoPE metadata |
| C. Post-encoder, pre-projector | `last_hidden_state`, `[N_pre, 1152]` | `model.visual.vision_model.encoder` / `model.visual` output | Yes | Conditional/high risk: projector expects ordered 2x2 groups |
| D. Projector / merge output | `[N_llm, 1024]` | `model.projector` (legacy `mlp_AR`) | Yes | Natural pre-LLM boundary, but selection/merging must keep placeholders and positions consistent |
| E. LLM boundary | features scattered into equal-count image-token slots | `model.get_image_features` then language-model input scatter | Yes | Feasible but nontrivial: rebuild placeholders, masks, and 3D position IDs together |

Zeroing while retaining sequence length is not Token Pruning. The source audit
establishes accessibility, not correctness of a future intervention.

## 5. Scientific match quality

| Criterion | Assessment | Boundary |
|---|---|---|
| Architecture matching | Strong for the 608-tensor generative core | legacy/native implementation and 12 base-only unused tensors remain |
| Parameter matching | Strong at shared shapes, not exact total count | 958,588,736 versus 905,601,648; common values not compared |
| Provenance strength | Moderate | declared full-finetuned descendant; immutable parent revision absent |
| Thai specialization | Strongly declared | synthetic-only; future stimulus/font overlap unknown |
| Prompt comparability | Strong | identical `OCR:` contract and shared chat-template blob; use direct region recognition |
| Baseline measurement capacity | Plausible, not established | paper results are prior evidence, not project Gate 0 evidence |
| Compression accessibility | Strong enough for engineering investigation | true pruning needs coordinated sequence/position changes |
| Reproducibility | Good | public pins; snapshot terms and runtime stack |
| Kaggle T4 feasibility | Plausible, unverified | activation memory, runtime compatibility, and latency need smoke evidence |

Major confounds are synthetic-training distribution and possible stimulus/font
overlap, full-model fine-tuning, unknown immutable parent revision, an already
OCR-specialized base, region-recognizer versus page-pipeline behavior, and
legacy remote-code versus native Transformers loading. These prevent a claim
that any future interaction is caused solely by Thai training.

## 6. Novelty boundary

The candidate contribution remains:

```text
MODEL x BUDGET
```

with a possible later, adequately powered and pre-registered:

```text
MODEL x BUDGET x THAI_ORTHOGRAPHIC_COMPONENT
```

Novelty is not claimed for Thai OCR fine-tuning, PaddleOCR-VL, Wayu, Token
Pruning, or synthetic Thai OCR data. No inspected source in the current matrix
establishes this exact controlled interaction, but the review is not claimed
exhaustive.

## 7. Exact authorized non-scientific smoke

Human approval for this exact workload was recorded on 2026-09-12:

1. Pin the revisions in Section 3.1 and one Transformers/runtime environment;
   archive terms, model-card, config, and weight checksums.
2. Use direct region recognition for both checkpoints, not `PP-DocLayoutV3`,
   with identical `OCR:` prompt, deterministic decoding, one parser, and one
   predeclared full-information processor setting.
3. Select five already exposed open-calibration `pair_id` values, one per
   registered component category. Render both members once at one frozen font
   and size. Do not inspect locked data.
4. Run both checkpoints on the 10 images twice identically:
   `5 pair_id x 2 members x 2 models x 2 repeats = 40 calls`.
5. Record revision, weight checksum, environment, seed, prompt bytes, decoding
   config, dimensions, `image_grid_thw`, `N_pre`, projector count,
   image-placeholder count, latency, and peak GPU memory for every call.
6. Engineering pass requires both pins to load without ignored generative-core
   keys, no OOM/runtime error, feature-placeholder count agreement,
   generated-token slices that can be isolated and Unicode-decoded (an empty or
   incorrect recognition is not by itself an engineering failure), repeat
   output/count identity, and complete provenance.
7. Do not calculate or use accuracy, component effects, or between-model
   performance for pair selection. Failure returns to human review; no prompt
   tuning, dependency substitution, expanded retry, or compression follows.

## 8. Human authorization and stop boundary

Human review accepted the audit and authorized only the exact 40-call
engineering smoke above. Stage S0 and all scientific/compression work remain
unauthorized. After the smoke report, the required state is:

```text
HUMAN_REVIEW_AFTER_ENGINEERING_SMOKE
```

Only the 40-call engineering inference above is authorized. Locked validation,
Stage S0, compression, and fine-tuning remain unauthorized.
