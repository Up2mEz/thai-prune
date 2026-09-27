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
