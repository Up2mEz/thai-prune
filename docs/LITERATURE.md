# Literature Evidence Matrix

> Checked: 2026-09-12. This is an evidence matrix, not evidence that the
> search is exhaustive. Absence from this matrix must not be described as
> absence from the literature.

## Search protocol

### Scope

- visual-token pruning, merging, pooling, and resolution-based reduction;
- OCR/text-rich and detail-sensitive evaluation;
- controlled visual fidelity and language-prior diagnostics;
- Thai and multilingual VLM/OCR evaluation;
- implementation compatibility with Qwen2.5-VL and Qwen3-VL.

### Sources and query families

Primary sources were preferred: arXiv, ACL Anthology, official project pages,
and official code repositories. Query families combined terms such as:

```text
visual token compression OCR text-rich VLM Qwen
visual token pruning fine-grained detail character OCR
resolution reduction downsampling visual token benchmark
Thai OCR VLM visual token compression
Thai orthography minimal pair VLM tone mark
```

Backward/forward checks used the baseline families named by VTC-Bench,
UniPruneBench, LLMC+, ET-Prune, and RTPrune. Curated paper lists were used for
discovery only; claims below come from the primary paper or official code.

### Inclusion and exclusion

- Include work that changes visual information/token load, evaluates OCR or
  fine detail, supplies a compression benchmark, or directly bears on Thai
  text evaluation.
- Exclude pure weight quantization and video-only methods unless they clarify
  an intervention boundary relevant to this project.
- Do not infer compatibility from a title, abstract, or model-family name.
- `Unknown` means the exact compatibility claim has not been demonstrated by
  inspected official code.

## Evidence matrix

| Work | Year | Main question | Model(s) | Compression location | OCR/text-rich? | Controlled micro-detail? | Relevant evidence | Does NOT establish for this project | Code | Checked |
|---|---:|---|---|---|---|---|---|---|---|---|
| [FastV](https://arxiv.org/abs/2403.06764) | 2024 | Can later LLM-layer visual attention be reduced? | LLaVA-1.5, Qwen-VL-Chat, Video-LLaVA | Within later LLM layers | General benchmarks; not OCR-centered | No | Establishes a widely used training-free pruning baseline and the need to name the intervention layer | Thai robustness, character-level fidelity, or Qwen2.5 compatibility | [Official code](https://github.com/pkunlp-icler/FastV) | 2026-09-04 |
| [SparseVLM](https://arxiv.org/abs/2410.04417) | 2024 | Can text-guided layer-wise sparsification reduce VLM cost? | Primarily LLaVA-family evaluations | Within LLM visual-token sequence, with recycling | Some text-sensitive benchmarks, not Thai-specific | No | Shows text guidance and recycling are existing baseline families | Preservation of Thai combining marks or controlled critical regions | [Official code](https://github.com/Gumpest/SparseVLMs) | 2026-09-04 |
| [VisionZip](https://arxiv.org/abs/2412.04467) | 2024/2025 | Can vision features be selected/merged before LLM input? | LLaVA-family; later official Qwen2.5-VL support | After Vision Encoder, before LLM | General tasks; repository mentions OCR follow-up | No | Strong pre-LLM selection/merging baseline; official repository reports a Qwen2.5-VL branch | That text-agnostic compression preserves Thai micro-features | [Official code](https://github.com/dvlab-research/VisionZip) | 2026-09-04 |
| [VTC-Bench](https://aclanthology.org/2026.acl-long.195/) | 2026 | Are general benchmarks appropriate for visual-token compression evaluation? | Qwen2-VL and other MLLMs | Compares image downsampling with several token-compression methods | Includes OCR-oriented benchmark content | Compression-sensitive filtering, not orthographic minimal pairs | Shows benchmark/task mismatch and that downsampling can outperform advanced methods on common benchmarks | A Thai component-level effect; equivalence of downsampling and pruning | [Official code](https://github.com/Chenfei-Liao/VTC-Bench) | 2026-09-04 |
| [UniPruneBench](https://arxiv.org/abs/2511.02650) | 2025/2026 | How do pruning methods compare under a unified protocol? | LLaVA-1.5, InternVL3, Qwen2.5-VL | Multiple ViT-only, pre-LLM, and LLM methods | Yes; reports OCR as sensitive | No controlled Thai components | Establishes that OCR sensitivity and strong random/downsampling baselines must be considered | Why a specific script component fails or whether Thai differs by component | Public benchmark code not located in this pass; status `Unknown` | 2026-09-04 |
| [LLMC+](https://arxiv.org/abs/2508.09981) | 2025/2026 | Can VLM compression methods be benchmarked in a modular toolkit? | Multiple VLM families | Multiple token-reduction and model-compression locations | Detail-sensitive tasks included | No Thai minimal-pair design | Shows detail-sensitive degradation and provides reusable baseline infrastructure | The project's component-level estimand | [LightCompress](https://github.com/ModelTC/LightCompress) | 2026-09-04 |
| [ThaiOCRBench](https://aclanthology.org/2025.ijcnlp-long.89/) | 2025 | How well do VLMs perform on Thai text-rich tasks? | Proprietary and open VLMs | No controlled compression intervention | Yes, Thai | Fine-grained recognition, but not controlled orthographic pairs | Establishes a Thai external-validity benchmark and documents recognition/error categories | Compression causality, component-by-budget interaction, or minimal-pair discrimination | [Official code/data](https://github.com/scbdatax/ThaiOCRBench) | 2026-09-04 |
| [Typhoon OCR](https://arxiv.org/abs/2601.14722) | 2026 | Can Thai/document-specialized SFT improve end-to-end Thai and English document extraction? | Typhoon OCR V1; V1.5 uses Qwen3-VL 2B | No controlled compression intervention | Yes, Thai/English OCR | Document-level evaluation; not controlled orthographic pairs | Establishes OCR specialization, Thai-focused/synthetic training, and document-benchmark improvements as prior work; V1.5 reports full-parameter SFT on Qwen3-VL 2B | Robustness under matched information reduction, isolated-component capacity, a causal specialization effect, or an immutable parent revision | [Official code](https://github.com/scb-10x/typhoon-ocr) and [model](https://huggingface.co/typhoon-ai/typhoon-ocr1.5-2b) | 2026-09-12 |
| [How Far Can Synthetic Data Take Thai OCR?](https://arxiv.org/abs/2609.03595) | 2026 | Which synthetic-document properties transfer to real Thai OCR, and how far can synthetic-only training go? | Qwen3-VL-2B experiments; Wayu-Paxa-OCR-Zero full fine-tune of PaddleOCR-VL-1.6 | No controlled visual-token compression | Yes, Thai/English OCR | Document/region CER, not controlled orthographic minimal pairs | Declares all-parameter fine-tuning on 45,723 synthetic pages and establishes Thai specialization as prior work; exposes a public base/descendant candidate | Robustness under controlled information budgets, component-by-budget interaction, exact immutable parent revision, or training-data-only causality | [Model](https://huggingface.co/wayu-ai/wayu-paxa-ocr-zero), [inference code](https://github.com/wayu-research/wayu-ocr-inference), and [data generator](https://github.com/wayu-research/docaug) | 2026-09-12 |
| [Fico](https://aclanthology.org/2026.findings-acl.1758/) | 2026 | How robust are VLMs to controlled visual fidelity and density? | 13 VLMs, 3 OCR-specialized models | Rendering density/resolution; visual-text compression | Yes | Controlled fidelity variants, not Thai component pairs | Establishes that controlled visual fidelity can expose failures missed by VQA and that OCR differs from higher-level tasks | Post-encoder pruning behavior or Thai orthographic category effects | [Official code/data](https://github.com/wang-research-lab/fico-bench) | 2026-09-06 |
| [Visual Merit or Linguistic Crutch?](https://arxiv.org/abs/2601.03714) | 2026 | How much does DeepSeek-OCR rely on language priors? | DeepSeek-OCR and 13 baselines | Visual-token density and semantic corruption | Yes | Semantic corruption controls, not Thai minimal pairs | Directly supports language-prior diagnostics and reports increased prior sensitivity under lower visual-token regimes | Uncompressed Qwen behavior, component-specific degradation, or a Token Pruning mechanism | [Official data/results/scripts](https://github.com/dududuck00/DeepSeekOCR) | 2026-09-06 |
| [FastOCR](https://arxiv.org/abs/2605.17447) | 2026 | Can OCR inference attend dynamically without permanent token eviction? | Five VLMs including Qwen2.5-VL | Decoder-time KV/attention selection; tokens are not permanently evicted | Yes | No Thai component-controlled evaluation reported | Existing OCR-aware alternative that separates per-step attention from physical token deletion | That permanent pruning fails on every OCR setup or on Thai specifically | No official code located in this pass | 2026-09-04 |
| [RTPrune](https://arxiv.org/abs/2605.00392) | 2026 | Can post-encoding pruning/merging accelerate DeepSeek-OCR? | DeepSeek-OCR-Large | Post-encoder selection plus merging | Yes | No Thai component-controlled evaluation reported | Establishes a strong OCR-specific pruning/merging family and provides implementations of comparison methods | Compatibility with Qwen2.5-VL or a Thai effect | [Official code](https://github.com/BurnWan/RTPrune) | 2026-09-04 |
| [ET-Prune](https://arxiv.org/abs/2608.01979) | 2026 | Can evidence-aware dynamic budgeting preserve text-rich evidence? | Qwen3-VL-8B, InternVL3.5-8B | Progressive decoder-side pruning | Yes | OCRBench-level, not Thai minimal pairs | Most direct novelty threat: question-conditioned evidence, text-region safeguards, and dynamic token floors already exist | Thai component robustness; compatibility with the primary Qwen2.5-VL-3B adapter | [Repository](https://github.com/Labyrinth0419/ET-Prune) says implementation is TBD | 2026-09-04 |
| [LensVLM](https://arxiv.org/abs/2605.07019) | 2026 | Can a model selectively expand compressed rendered text? | Qwen3.5-based system | Resolution/density plus learned expansion tools | Yes | Character indistinguishability analyzed at document scale | Shows resolution compression and selective re-expansion are established directions | Post-encoder pruning or Thai component-by-budget effects | Code status `Unknown` in this pass | 2026-09-04 |
| [CARES](https://aclanthology.org/2026.acl-long.102/) | 2026 | Can input-dependent minimum sufficient resolution be selected? | VLMs evaluated with discrete/continuous resolutions | Preprocessing resolution selection | Text-rich tasks may be included but not the central controlled question | No | Establishes adaptive resolution selection as prior work | Controlled Thai orthographic degradation or post-encoder pruning | Code status `Unknown` in this pass | 2026-09-04 |
| [Benchmarking and Mitigating MCQA Selection Bias of Large Vision-Language Models](https://aclanthology.org/2025.emnlp-main.1703/) | 2025 | How do option-token identity and position affect LVLM multiple-choice answers? | LLaVA-v1.5-13B, InternVL2.5-8B, Qwen2.5-VL-3B | No compression intervention | No | Fine-grained natural-image classes, not orthographic detail | Direct evidence on the primary model family that option token and position interact, especially as alternatives become more ambiguous | A universal A bias, Thai OCR behavior, or validity of any debiasing change to our registered metric | [Official repository](https://github.com/Atabuzzaman/Selection-Bias-of-LVLMs) is partial relative to the full paper protocol | 2026-09-06 |
| [Choosing “Right” from Wrong](https://openaccess.thecvf.com/content/CVPR2025W/BEAM/html/Zeno_Choosing_Right_from_Wrong_A_Closer_Look_at_Selection_Bias_CVPRW_2025_paper.html) | 2025 | Does selection bias contaminate spatial multimodal MCQs? | Eight LMM architectures | No compression intervention | No | Spatial image-caption probes | Independent support for candidate permutation and position-bias audits in image-conditioned forced choice | Transfer of an architecture-specific bias to Qwen2.5-VL or Thai text | No official code located in this bounded pass | 2026-09-06 |
| [Debiasing Multimodal Large Language Models via Penalization of Language Priors](https://arxiv.org/abs/2403.05262) | 2024/2025 | Can dummy or absent visual evidence expose language-prior behavior? | Six MLLMs | No compression intervention | Toy visual questions, not OCR-centered | Controlled dummy-image variants | Supports comparing image-conditioned token evidence with matched dummy-image baselines | That a 448×448 blank is pure language-only input, or that logit subtraction is causal | No verified official code located in this bounded pass | 2026-09-06 |
| [Context-Independent OCR with Multimodal LLMs](https://arxiv.org/abs/2503.23667) | 2025 | How do resolution and glyph complexity affect isolated-character OCR? | GPT-4o, Gemini 2.0 Flash, Azure OCR | Input resolution | Yes, Japanese single characters | Context-independent glyph recognition | Close evidence that isolated-character OCR can be scale-sensitive and that glyph complexity alone may explain little | A Thai pixel-size threshold or behavior of the pinned Qwen model | No official code located in this bounded pass | 2026-09-06 |
| [FADE](https://aclanthology.org/2026.alvr-main.23/) | 2026 | How do VLMs recognize fine-grained text as visibility decreases? | Gemini 3, Claude 4.5 Sonnet, Gemma 3 | Visibility/contrast manipulation | Yes | Synthetic numeric strings with controlled clutter/transparency | Fine-detail OCR can collapse as visual evidence weakens, independently of semantic text context | Equivalence between visibility, resolution, Thai marks, or visual-token pruning | No official code located in this bounded pass | 2026-09-06 |

## Implementation compatibility audit

Compatibility is with the planned primary backbone
`Qwen/Qwen2.5-VL-3B-Instruct`, not with an abstract Qwen family.

| Candidate | Compatibility status | Evidence | Consequence |
|---|---|---|---|
| Vanilla Resolution Reduction | `Candidate — official path` | Qwen2.5-VL processor exposes resolution/pixel controls; exact revision still must be pinned | Appropriate for Stage 1A only |
| VisionZip | `Candidate — official implementation exists` | Official repository announces Qwen2.5-VL support | Inspect exact branch/revision before any later direct comparison |
| FastV | `Partial` | Original code predates Qwen2.5-VL; [AngelSlim](https://github.com/Tencent/AngelSlim) reports Qwen2.5-VL-3B FastV runs | Treat AngelSlim integration as a later compatibility candidate, not current evidence |
| LightCompress token-reduction suite | `Candidate` | Official source includes a `Qwen2_5VL` model class and multiple reduction algorithms | Potential Gate 4 infrastructure after direct code audit |
| VTC-Bench | `Partial` | Official code contains a Qwen2-VL path; paper covers multiple backbones | Reuse evaluation ideas, not assume drop-in Qwen2.5 compatibility |
| FastOCR | `Paper-compatible, code unavailable` | Paper reports Qwen2.5-VL; no official implementation located | Cannot be a reproducible baseline until code or a faithful audited implementation exists |
| ET-Prune | `No current primary-backbone implementation evidence` | Core results use Qwen3-VL-8B/InternVL3.5-8B; repository marks code TBD | Novelty threat, not an executable current baseline |
| RTPrune | `No` | Official implementation is tied to DeepSeek-OCR | Stage 4 background/baseline family only unless architecture is deliberately changed |

## Directly supported synthesis

### What prior work already establishes

- OCR and detail-sensitive tasks can be more vulnerable than aggregate VLM
  benchmarks under some compression settings.
- Generic benchmarks may be poorly targeted for evaluating visual-token
  compression, and image downsampling is a necessary baseline.
- Thai VLM/OCR evaluation and fine-grained Thai recognition benchmarks already
  exist.
- OCR-aware, text-aware, dynamic-budget, resolution-selection, and
  post-encoder compression methods already exist. A generic claim that such a
  method is new is not defensible.
- Language priors can contaminate apparent OCR success, so visual negative
  controls are required.
- Forced-choice output can depend jointly on option-token identity and option
  position. For `Qwen2.5-VL-3B`, the current primary evidence does not support
  simplifying this to a universal preference for one label.
- Dummy/blank visual conditions can diagnose prior-sensitive behavior, but a
  blank image still produces visual tokens and must not be described as a
  pure image-free or language-only condition.
- Resolution and visibility are established sources of OCR/fine-detail
  sensitivity. They do not identify the causal mechanism of an effect in the
  current Thai rendering design.
- Thai/document OCR specialization and its document-level benefit are already
  established research directions. The public Typhoon artifacts do not test
  robustness under matched visual-information reduction or controlled Thai
  orthographic components.

### What this pass did not find established

Within the recorded searches, no inspected work directly evaluated all of:

1. controlled Thai orthographic minimal pairs;
2. pixel-level difference masks for the distinction-critical evidence;
3. component category by actual visual-token budget interaction;
4. repeated render conditions analyzed with `pair_id` as the independent unit;
5. forced-choice plus language-prior controls; and
6. explicit separation of Resolution Reduction from post-encoder pruning.

The refreshed selection-bias, dummy-image, and visual-scale literature also
did not directly evaluate a matched blank-versus-image A/B decision-margin
shift for controlled Thai orthographic minimal pairs on a pinned
`Qwen2.5-VL-3B-Instruct` revision. This diagnostic remains a bounded local
measurement question rather than a claimed new method.

The 2026-09-12 specialization-pivot refresh did not locate an inspected study
that jointly compares a declared base checkpoint with its OCR-specialized
descendant across realized visual-information budgets using controlled Thai
orthographic minimal pairs and `pair_id`-clustered analysis. This is a
candidate bounded evaluation gap, not proof of novelty and not a causal
fine-tuning claim. Exact provenance, prompt-fairness, terms, and stage-gate
constraints are in `SPECIALIZATION_PIVOT_REVIEW.md`.

This is a bounded search result, not proof that no such work exists.

## Novelty assessment

**Level: `MODERATE_PROVISIONAL`**

The defendable candidate contribution is an evaluation/diagnostic study of
controlled Thai orthographic micro-feature robustness. The broad claims
"compression harms OCR", "benchmarks miss compression failures", "controlled
fidelity matters", and "Thai VLM OCR is difficult" are already occupied.

There is currently no literature-based justification for a new method. The
next evidence needed is measurement validity, not method development.

For the proposed specialization pivot, the candidate contribution is the
non-directional `MODEL x BUDGET` degradation comparison. The later
`MODEL x BUDGET x COMPONENT` question is conditional on measurement capacity.
Neither question is authorized for inference while the pivot remains
`SPECIALIZATION_PIVOT_PENDING_HUMAN_REVIEW`.

## Stop/pivot signals

- `STOP` the Thai-specific framing if a directly comparable component-level
  controlled study is found or if valid Stage 0 measurement cannot be built.
- `GO WITH PIVOT` to generic micro-detail robustness if Thai component effects
  are not distinguishable after controlling visual evidence properties.
- Keep post-encoder Token Pruning `NOT TESTED` until a direct experiment exists.

## Search limitations and required refresh

- Search-engine indexing and very recent 2026 releases may be incomplete.
- Several papers expose claims without released code; compatibility remains
  uncertain until code is available and inspected.
- Refresh this matrix immediately before advisor review and before Gate 4.
- A domain expert should inspect Thai linguistics/orthography literature during
  candidate-pair review; this pass focused on VLM/OCR/compression work.
