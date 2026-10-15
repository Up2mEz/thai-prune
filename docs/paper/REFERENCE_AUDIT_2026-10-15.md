# Reference audit, 2026-10-15 (ref-verify protocol)

Scope: all 23 entries of `docs/paper/references.bib`, as cited in `docs/paper/ieee/v2/*/body_*.tex`.
Mode: Quick Screen on all, then source-depth checks for every reference cited for a specific claim
(abstract for topline claims, full text or code for mechanism claims). The `ref-verify` CLI was not
installed, so the manual protocol was run with CrossRef, arXiv, OpenAlex, DOI landing pages, the
arXiv PDFs and the pinned code. Nothing below is from memory. PDFs were fetched into a scratch
directory and read with PyMuPDF; the code was read from the pinned GitHub files.

Retraction layer: CrossRef has no `update-to` record for the six DOI-backed entries. No web search
for retraction notices beyond that was run.

## Result

21 ACCEPT, 2 WARN, 0 REJECT.

| key | verdict | what was checked and found |
|---|---|---|
| nonesung2025thaiocrbench | ACCEPT | CrossRef, arXiv and ACL page agree (title, first author, 8 authors, pages 1653-1675). Full text: metrics are BLEU, METEOR, F1, **Normalized Levenshtein Similarity** (composite BMFL) and ANLS; "stacked diacritics" appear in its introduction among the features of Thai that English-centric datasets do not capture. Dataset licence CC-BY-SA-4.0 (HF API). **Two wording fixes made** ("similarity" not "distance"; "lists ... among the features", not "names ... as a difficulty"). |
| nonesung2026typhoonocr | ACCEPT | arXiv 2601.14722. Full text: "Typhoon OCR V1.5 is trained using full-parameter SFT on the Qwen3-VL 2B VLM"; infographics: "an area for improvement that we aim to improve in future iterations". |
| nectec2026pathumma | ACCEPT (model card, no paper) | HF page resolves; card snapshot in the repo: base Qwen3-VL-2B-Instruct, Apache-2.0, 377K OCR samples. |
| pipatanakul2026synthetic | ACCEPT | arXiv 2609.03595, sole author Pipatanakul. Full text: Wayu-Paxa-OCR-Zero is "a crop-level OCR model", adapted from PaddleOCR-VL-1.6 (0.9B) with 45,723 synthetic pages. This supports the paper's "region recognizer" wording. |
| cui2025paddleocrvl | ACCEPT | arXiv 2510.14528; abstract: 0.9B VLM for element recognition. |
| paddlex2025truncate | ACCEPT (code) | Pinned commit file read: `truncate_repetitive_content` runs on the decoded content (only if it is at least 3,000 characters). |
| bai2025qwen3vl | ACCEPT | arXiv 2511.21631 metadata match. |
| do2025reference | ACCEPT | CrossRef and OpenAlex: Vietnamese historical OCR with diacritics, LLM post-OCR correction; AAAI 39(27), pages 27951-27959 match. |
| elsafty2025arabic | **WARN** | Exists (CrossRef and OpenAlex agree on title, authors, IEEE BigData 2025, pages 5437-5442; DOI added to the bib). Closed access and no abstract in CrossRef, OpenAlex or the Lamarr search page, so the claim "an evaluation of Arabic OCR treats diacritized text as a separate condition" could **not** be re-checked today. `RELATED_WORK_DRAFT.md` says an earlier session saw its abstract. The author should read the paper or abstract once before submission. |
| holtzman2020curious | ACCEPT | arXiv abstract: likelihood as a decoding objective gives text that is "strangely repetitive". |
| blecher2024nougat | ACCEPT | Full text: the model degenerates into repeating a sentence (1.5% of test pages); repetition detection from a sliding-window variance of the logits, and generation is stopped early. |
| poznanski2025olmocr | ACCEPT | Full text: failures with endless repetitions are caught automatically and retried; raising the temperature from 0.1 to 0.8 reduces repetitions. |
| wei2025deepseekocr | ACCEPT, note | Metadata match. The paper contains no mention of n-gram blocking or repetition (searched); the claim rests on the code entry below, and the paper is cited beside it only to identify the system. |
| deepseekocr2025code | ACCEPT (code) | `NoRepeatNGramLogitsProcessor` bans repeated n-grams inside a window; `run_dpsk_ocr_image.py` sets `ngram_size=30, window_size=90`, with a whitelist for two table-tag tokens (the paper's text does not mention the whitelist). |
| yang2025ccocr | ACCEPT | CrossRef (ICCV 2025, pages 21744-21754) and arXiv 2412.02210 agree; the paper has a section "Hallucination of Repetition Output" with a repetition ratio. |
| keskar2019ctrl | ACCEPT | Full text: "penalized sampling works by discounting the scores of previously generated tokens". |
| leng2024vcd | ACCEPT | CrossRef (CVPR 2024, pages 13872-13882); arXiv abstract: contrasts output distributions from original and distorted visual inputs. |
| favero2024m3id | ACCEPT | arXiv abstract: M3ID amplifies the influence of the image over the language prior. |
| liu2024pai | ACCEPT, bib fixed | CrossRef and arXiv both give "Paying More Attention to **Image**"; the bib had "Images" (an earlier note in `RELATED_WORK_DRAFT.md` said ECCV uses "Images"; the publisher page is behind a bot check, so the CrossRef title was used). Abstract: amplifies attention to image tokens and subtracts the logits of multimodal input from pure-text input. |
| leviathan2023speculative | ACCEPT | arXiv abstract: sampling faster "without any changes to the outputs". |
| saxena2023pld | ACCEPT (code/README) | README: draft model replaced by string matching in the prompt; "no effect on output quality". |
| aisingapore2026sealion | ACCEPT (model card) | Card snapshot: built on Qwen3-VL-4B-Instruct, MIT, fine-tuned on seven languages including Thai. |
| wei2026deepseekocr2 | ACCEPT | arXiv 2601.20552: title, three authors and date match; the arXiv id is the one in the model card's own citation. |

## Changes made because of the audit

- `docs/paper/ieee/v2/*/body_*.tex` (EN and TH): ThaiOCRBench metric and diacritic wording; the
  contrastive-decoding sentence now describes VCD, M3ID and PAI as the sources do (M3ID and PAI
  are not plain "no-image" contrasts).
- `docs/paper/references.bib`: PAI title; DOI added to `elsafty2025arabic`.

## Not changed, for the author

- Elsafty (WARN above).
- The n-gram blocking sentence omits the table-token whitelist; the paper's own experiment is on
  Typhoon outputs, so whether to mention it is the author's call.
