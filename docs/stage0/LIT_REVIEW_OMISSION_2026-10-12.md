# Literature review: why does a full-page OCR VLM leave lines out?

**Date:** 2026-10-12. **Status:** review only; no experiment is registered or run by this document.

**Method:** four independent searches. Every source below was fetched during the search, and bibliographic data comes from the fetched page. The fetch tool summarised some pages, so quotes and section numbers should be checked against the PDF before they enter the paper. Items marked *preprint* are not peer reviewed.

**Why:** the paper says lines are *absent from the output*, and cannot say whether the model failed to see them or saw them and did not write them. The questions are (A) is omission a recognised problem, (B) which tests separate "cannot see" from "does not transcribe", and (C) which of them are feasible for us.

## A. Is omission a recognised problem?

Yes for omission in general. For Thai marks the answer is partly.

| Source | What it shows | Cause given |
|---|---|---|
| OmniDocBench (Ouyang et al., arXiv:2412.07626) | "Missing content" is the main VLM failure on dense pages; InternVL2 frequently misses content on multi-column pages | resolution and token-length limits (stated) |
| Gardella et al., Uruguayan documents (arXiv:2607.24077, 2026) | VLMs skip regions at the start, middle or end of a page; some stop transcribing, then loop | none tested |
| ThaiOCRBench (arXiv:2511.04479) | Thai VLMs differ in deletions (Gemma3 27B highest); omission is a count, not split by mark type | none |
| Typhoon OCR (arXiv:2601.14722) | degrades on low resolution and figure-heavy content; does not analyse its own omissions | none |
| DOCR-Inspector (arXiv:2512.10619) | "text segment lost" and "text characters lost" are named error classes | rates are from synthetic data |
| GlotOCR Bench (arXiv:2604.12978) | Thai is in the middle tier; "silence" (empty output) is 6% of failures | none |
| Karamolegkou et al., Ancient Greek (arXiv:2605.27750) | omission is only 2 to 8% of errors; accent errors are 37 to 57%; the two are separate | none |

**Not established anywhere we found:**
1. A split of lost diacritics into "in an omitted line" versus "misread in a kept line", for any script.
2. Whether omission is a perception limit or a generation effect.
3. An omission analysis of Typhoon, Pathumma or PaddleOCR-VL on Thai.
4. A per-line omission rate on a diacritic-heavy script.

These four are the paper's novelty, and also what it cannot yet explain.

## B. Tests that separate "cannot see" from "does not transcribe"

### B1. Crop, zoom and context (finding versus reading)

| Source | Finding | Design to copy |
|---|---|---|
| MLLMs Know Where to Look (arXiv:2502.17422, ICLR 2025) | attention lands on the right region even when the answer is wrong; an oracle crop fixes small-subject errors (LLaVA-1.5 TextVQA 39.4 to 70.0) | oracle crop beside the original; attention ratio inside the box |
| Dolphin (arXiv:2505.14059, ACL Findings 2025) | an element crop beats naming the box on the full page (edit distance 0.103 vs 0.185) | same model, same elements: crop versus box query |
| Monkey (arXiv:2311.06607, CVPR 2024) | at the same pixel budget, tiling beats resizing (DocVQA 66.5 vs 53.9) | same-pixel comparison (trained for tiling, so confounded) |
| ZoomEye (arXiv:2411.16044, EMNLP 2025) | zooming helps only when the search lands on the target (93% vs 55%) | split by whether the crop covers the target |
| UReader (arXiv:2310.05126), MinerU2.5 (arXiv:2509.22186) | grid crops, or a thumbnail then native-resolution crops | no ablation we could use |

### B2. Image support by probability

| Source | Measure |
|---|---|
| Li et al. 2016 (arXiv:1510.03055) | maximum mutual information, the origin of the image-versus-no-image likelihood ratio |
| Context-aware decoding (arXiv:2305.14739), VCD (arXiv:2311.16922), M3ID (arXiv:2403.14003), PAI (arXiv:2407.21771) | contrast the output with and without (or with a distorted) image |
| Visual Information Gain (arXiv:2602.17186, *preprint*), Token Visual Dependency (arXiv:2604.01840, *preprint*) | per-token image dependence |
| BEAF (arXiv:2407.13442, ECCV 2024) | edit the image, check whether the model notices |
| Yao et al. (arXiv:2511.19806) | OCR output probabilities are poorly calibrated for abstention, so a null result is plausible |
| Karamolegkou et al. (arXiv:2605.27750) | per-token image gain (log-probability with the image minus without) |

No source uses token probabilities directly as an omission test. Our T3 (image support of +1.3 nats at skipped lines versus -9 at ordinary transitions) is a 12-character, teacher-forced version of this idea.

### B3. Internal states

| Source | Finding | Model |
|---|---|---|
| Seeing but Not Believing (arXiv:2510.17771, *preprint*) | deep layers attend to the evidence even when the answer is wrong | LLaVA, Qwen, Gemma, InternVL |
| Hidden in Plain Sight (arXiv:2506.08008, *preprint*) | the vision encoder holds more than the VLM uses; the bottleneck is in the language model | unnamed |
| OCR Heads (arXiv:2505.15865, EMNLP 2025) | masking 20 "OCR heads" in Qwen2-VL-7B drops DocVQA F1 from 76.3 to 59.7 | Qwen2-VL, InternVL2 |
| Where Vision Becomes Text (arXiv:2602.22918, *preprint*) | activation patching locates an OCR routing bottleneck, near 50% depth for DeepStack models | Qwen3-VL, Phi-4, InternVL3.5 |
| Cross-modal information flow (arXiv:2411.18620, CVPR 2025), logit lens (arXiv:2410.07149, ICLR 2025) | where visual information enters the text positions | LLaVA |
| FastV (arXiv:2403.06764), SparseVLM (arXiv:2410.04417), attention sinks (arXiv:2503.03321, *preprint*) | most image tokens receive little attention in deep layers | LLaVA, Qwen |
| FastOCR (arXiv:2605.17447, *preprint*) | attention in document parsing shifts across decoding steps | Qwen2.5-VL |

Most mechanistic evidence is on LLaVA. Only the OCR-heads and routing papers use Qwen models, and only the routing paper uses Qwen3-VL. Attention is correlational.

## C. Feasibility on Kaggle 2xT4 (our arithmetic, not from a paper)

Qwen3-VL-2B has 28 text layers and 16 heads, and merges 2x2 patches (32x32 px per token). A page of 1800x1300 px gives about 2,300 visual tokens, so about 3,000 to 3,500 with the prompt. Full attention for all layers (`output_attentions`) would need about 11 GB and does not fit; one layer is about 0.4 GB.

- **Feasible:** forward-pass probability tests, per-layer hooks that keep only the rows of interest, logit lens and probes at chosen positions, attention knockout by a 4D mask.
- **Not feasible:** all heads and layers for whole pages, per-token gradient maps.
- **Caveat:** DeepStack adds visual features at early decoder layers, which complicates a logit lens there.

## D. Candidate experiments (to register; none is registered)

All use the calibration split, the items where Typhoon omitted a line (T3 found 34 skips; the E1 to E3 and P-ZOOM runs hold others), and matched controls on lines it read. Each states what every outcome would mean.

1. **Context ladder (generation; cheapest).** Read each omitted line as: whole page (repeat); whole page with the box in the prompt; tight crop; crop plus neighbouring lines; band; half page. Controls: read lines, a crop of a wrong region, the same arms at 1.85x.
   - Recovery on the crop but not the box-in-prompt arm: the line is readable and the failure is in finding or emitting it.
   - Recovery only as context shrinks: competition among lines.
   - No recovery on the crop: recognition fails.
   - Adapted from Zhang 2025, Dolphin, ZoomEye.
2. **Padded canvas (generation).** Paste the crop at native scale on a blank page-sized canvas, so pixels per glyph and token count equal the whole page.
   - Recovery: line density or sequence position matters, not resolution.
   - No recovery, but recovery on the tight crop: token count or size matters.
   - Adapted from Monkey.
3. **Teacher-forced image gain and rank (no generation).** After the preceding emitted line, force-decode the reference line with the image, with a blank image, and with the image where that line is erased. Record the rank of its first token against the model's actual next output.
   - High image gain, with the line ranked below the model's own continuation: the model sees the line and does not choose to write it.
   - Image gain near zero: it cannot see it.
   - Extends T3 with the erased-line control. Adapted from BEAF, Karamolegkou, T3.
4. **Attention and activation patching (heavier).** Attention ratio inside the omitted line's box against same-size boxes; then patch the line's activations from a run in which the line was cropped and read, sweeping layers.
   - A ratio equal to the controls with no recovery: an information-loss or sequence-level cause.
   - Recovery at specific layers: the failure is localised there.
   - Adapted from Zhang 2025, OCR Heads, Steinberg and Gal.

**Suggested order:** 3 (no generation, extends T3), then 1 and 2 (one run each), then 4 only if 1 to 3 leave the question open.
