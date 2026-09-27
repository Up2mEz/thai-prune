# Beyond pruning — literature scan, 2026-09-25

**Status: `SEARCH_LEVEL_SCAN`, not an audit.** Each source below was located by
web search and its existence confirmed at an official venue or arXiv listing.
None has been read in full, none has been added to `docs/LITERATURE.md`'s
evidence matrix, and no claim below may be cited from this note. Use the
`ref-verify` workflow before any of it enters a paper.

## Why this scan

Rounds 1–3 showed post-encoder pruning cannot shrink the model (weights are
untouched) and shortens only prefill, ~21 ms of a ~300 ms call; decode is
~230 ms. The researcher's goals are a smaller or faster VLM, or a way to keep
Thai vowels and tone marks from being lost, without fine-tuning.
`docs/LITERATURE.md` excludes pure weight quantization from scope, so any move
toward it is a scope change requiring a Decision Log entry.

## Making the model smaller or faster

| source | what it offers | relevance / gap |
|---|---|---|
| Q-VLM, [arXiv:2410.08119](https://arxiv.org/abs/2410.08119), NeurIPS 2024 | post-training quantization for vision-language models, cross-layer aware | attacks weight memory and decode, the real bottleneck; no Thai or diacritic evaluation |
| MBQ, [arXiv:2412.19509](https://arxiv.org/abs/2412.19509) | modality-balanced post-training quantization | same; vision/language imbalance may matter for fine glyph detail |
| GOT-OCR 2.0 (580M), SmolDocling ([ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/papers/Nassar_SmolDocling_An_ultra-compact_vision-language_model_for_end-to-end_multi-modal_document_conversion_ICCV_2025_paper.pdf)), LightOnOCR-1B, dots.ocr ([arXiv:2512.02498](https://arxiv.org/abs/2512.02498)) | smaller or faster OCR-specialized models | Thai support and licence unverified for each; earlier audit found most page readers do not declare Thai |

## Keeping Thai marks without fine-tuning

| source | what it offers | relevance / gap |
|---|---|---|
| ViCrop, "MLLMs Know Where to Look", [arXiv:2502.17422](https://arxiv.org/abs/2502.17422), ICLR 2025 | training-free cropping from the model's own attention/gradients for small details | directly aimed at small-detail perception; not evaluated on Thai or OCR diacritics |
| ThaiOCRBench, [arXiv:2511.04479](https://arxiv.org/abs/2511.04479) | 2,808-sample Thai benchmark; error analysis names stacked diacritics | a benchmark, not a remedy; licence previously flagged CC-BY-SA with upstream concerns |
| Vietnamese DAR survey, [arXiv:2506.05061](https://arxiv.org/abs/2506.05061) | documents the analogous stacked-diacritic confusion problem | cross-script evidence the problem is general; confusion there, deletion here |
| Type-Driven Tokenization for Brahmic Scripts, [arXiv:2609.22125](https://arxiv.org/html/2609.22125) | grapheme-cluster-atomic tokenization | requires retraining; and §6 of `THAI_MARK_FAILURE_MODES.md` found no support for tokenizer-caused deletion |
| PyThaiNLP `spell` | dictionary + edit-distance correction | training-free post-correction aimed at deletions; risky on proper nouns and brand names |

## Gap this scan did not find filled

No located source measures whether quantization, or any efficiency lever,
disproportionately removes Thai vowels and tone marks. That is a candidate gap
at search level only — a bounded scan is not proof of absence, and it must not
be written as "first".

## Addendum, 2026-09-28 — searched while T1/T2 was running on Kaggle

Located while preparing `docs/stage0/T1_T2_CONTINGENT_REMEDY_PLAN.md`, which
routes each to a specific branch of what T1/T2 could show. Same status as
above: search-level, not an audit, not citable until verified.

| source | what it offers | relevance / gap |
|---|---|---|
| "When Language Overwrites Vision", [arXiv:2605.08245](https://arxiv.org/abs/2605.08245) | names and mechanises exactly this project's prior-override hypothesis: visual embeddings pulled toward a "universal text subspace" during modality bridging; training-free fix projects that subspace out, no added inference cost by the authors' account | evaluated on POPE/CHAIR/AMBER/CLAIR hallucination benchmarks; no OCR, no diacritics, no Thai |
| Geometric Risk Control for VLM OCR, [arXiv:2603.19790](https://arxiv.org/html/2603.19790) | training-free, black-box: re-render under mild transforms, vote across views, abstain without consensus; 112x reduction in severe errors at ~90% coverage on scene-text OCR | English scene text only (IIIT5K, ICDAR 2013); is an abstention method, not a correction method, unless read as consensus voting |
| Consensus Entropy, [arXiv:2504.11101](https://arxiv.org/html/2504.11101v4) | training-free multi-VLM agreement metric; low-entropy trusts the majority, high-entropy routes to a stronger model | multi-model ensemble, not single-model; no Thai |
| "Reading Between the Lines" (latent representation probes), [arXiv:2511.19806](https://arxiv.org/html/2511.19806) | abstention from internal hidden-state probes, beats self-consistency on English OCRBench v2 etc. (75.0% vs 68.0%) | **requires trained probes on labelled error data — not training-free** in this project's sense; does not separate perception failure from decoding failure |
| Constrained CTC decoding for diacritic restoration, [arXiv:2607.18946](https://arxiv.org/html/2607.18946) | a lattice/WFST that fixes base characters and restricts decoding to legal diacritic slots — the same shape as this project's proposed mark-constrained re-scoring | **speech-to-text, Arabic, no image at all** — confirms the confusion-set idea has prior art in a different modality, not a competing OCR method |
| Catastrophic forgetting of visual grounding under instruction fine-tuning, e.g. [SMoLoRA](https://arxiv.org/pdf/2411.13949), [arXiv:2309.10313](https://arxiv.org/pdf/2309.10313) | motivates RQ-C: an OCR-specialized fine-tune may have measurably degraded grounding relative to its base | fixes proposed are all training-time (dual-expert, replay); no training-free analogue located beyond routing between models |
