# P-ZOOM-2 — is what zoom "gained" in P-ZOOM zoom, or just a different read?

**Status: `APPROVED` 2026-10-04 (`DECISION_LOG.md` 2026-10-04): smoke first, then the full run.**
Written 2026-10-04. A mechanism probe on the calibration split, Typhoon only. It evaluates
no method and supports no claim beyond what §5 states.

**Superseded in part, 2026-10-04 (after an independent review).** The `bands` view is *not* "the
one new factor" that §3 calls it: it differs from the whole-page controls in crop geometry
(full-width tiles, not a grid), in scale (1.85×: input resolution is increased, source pixels
enlarged; nothing is pruned or merged after the encoder), in width (1,536 to 3,087 px, median
2,366, beyond the 1,800 px the model was trained at on 19 of 21 pages) and in visual tokens per
read (1,872 to 3,744, against about 2,250 for the whole page). The rule of §5 therefore measures
how far the band read departs from the baseline, not zoom. It is still computed and reported as
registered, under the key `p_zoom2_as_registered_NOT_A_ZOOM_RESULT`; any statement about zoom
uses `P_ZOOM3_CONTROLS_DRAFT.md` §4 (`bands` against `bands100`, same crops).
## 1. Why a second round

P-ZOOM (`P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md` §9) ended below its registered line (tiles recover
47.8% of the absent marks as text; the whole-page `TYPHOON_CARD` read recovers 50.6%), but
it left two things open:

1. Tiles recovered 87 marks (22.5%) that the whole-page read did not, and lost 98 (25.3%).
   One greedy decode per condition cannot say how much of that is **zoom** and how much is
   **any change of the input** producing a different read.
2. The 2×2 grid cut wide lines (control lines found 40% against a 97% ceiling), so the
   instrument was weak exactly where the control looked.

## 2. Literature, and what it changes

Read 2026-10-04 by fetching each paper's arXiv abstract page; unless stated, only the abstract
was seen. The Typhoon row also uses the paper's HTML page (its ROUGE-L figures come from a results
table, and the 1,800 px and figure-limitation statements from its text) and the model card, so that
row rests on more than an abstract. No paper found by these searches
tests Thai or text-in-infographic omission directly.

| source | what it says (abstract level) | what it bears on here |
|---|---|---|
| Zhang et al., *MLLMs Know Where to Look*, ICLR 2025, [arXiv:2502.17422](https://arxiv.org/abs/2502.17422) | accuracy falls as the visual subject gets smaller (shown causal by intervention); the model attends to the right region even when it answers wrongly; training-free cropping from the model's own attention/gradients improves seven VQA benchmarks, TextVQA and DocVQA among them | the reason to expect that enlarging a region helps; it is a VQA result, not transcription, and says nothing about omitted text |
| Typhoon OCR, [arXiv:2601.14722](https://arxiv.org/abs/2601.14722) and the [model card](https://huggingface.co/typhoon-ai/typhoon-ocr1.5-2b) | outputs `<figure>` tags for visual elements; the card's prompt tells the model to describe the image, "mention visible text and its meaning"; trained at a fixed 1,800 px; the paper lists figure understanding as a limitation; infographics are its weakest category (ROUGE-L 0.527 vs 0.677 for Gemini 2.5 Pro) | a `<figure>` holding a description of the text is the contract working, not a failure; this is why §3 of P-ZOOM counted `figure_only` apart |
| *Improving MLLM Historical Record Extraction with Test-Time Image Augmentations*, [arXiv:2509.09722](https://arxiv.org/abs/2509.09722) | transcribing several augmented variants of one image (padding and blur helped most) and fusing the transcripts with a sequence alignment gave +4 points over one unmodified read; Gemini 2.0 Flash, 622 death records | different views of one image give complementary transcripts; supports a perturbation control and, if perturbation explains the gain, multi-view fusion as the lever. One model, one document type |
| *How Much Information Can a Vision Token Hold?*, [arXiv:2602.02539](https://arxiv.org/abs/2602.02539) | as text density per vision token rises, accuracy goes from stable, to an unstable phase of "increased error variance", to failure; DeepSeek-OCR the example | if dense graphics sit in the unstable phase at page scale, read-to-read variance is large there, which is what a perturbation control measures |
| *Image Tiling for High-Resolution Reasoning*, [arXiv:2512.11167](https://arxiv.org/abs/2512.11167) (Monkey replication) | tiling recovers local detail; the effect varies with task and tile granularity | tiling is not uniformly beneficial: tile geometry is a variable (P-ZOOM's control suggested it, though part of that was a scorer limit, `P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md` §10) |
| MinerU2.5, [arXiv:2509.22186](https://arxiv.org/abs/2509.22186) | layout analysis on a downsampled page, then content recognition on native-resolution crops | the route a graphics-aware remedy would take; no abstract-level comparison with full-page decoding |
| PaddleOCR-VL, [arXiv:2510.14528](https://arxiv.org/abs/2510.14528) | two-stage layout then element recognition (abstract: element-level state of the art); its claims about hallucination reduction came from a search snippet and were **not** confirmed | same |

**What this changes.** The literature supports zoom as a lever for small details and
multi-view reads as a source of complementary transcripts, and it does not say which of
the two produced P-ZOOM's gain. Hence the design below: a control for the second, and a
zoom view that does not cut lines.

## 3. Reads (Typhoon, `TYPHOON_CARD`, greedy as T1, same 21 pages, fp16)

Everything but the image is as in P-ZOOM. 105 reads.

| view | image fed | purpose |
|---|---|---|
| baseline | whole page, `resize_policy` (T1 `TYPHOON_CARD`, exists) | zoom-free reference |
| `pad` | whole page on a white margin of 4% of the longer side, then `resize_policy` (content ≈0.93×) | perturbation control |
| `scale90` | whole page, `resize_policy`, then ×0.9 (content 0.9×) | perturbation control |
| `bands` | 3 full-width horizontal bands, 15% overlap, each cropped from source pixels and resized to **1.85×** page scale (the P-ZOOM zoom), *not* capped at 1800 px | intended as one new factor (same zoom, no vertical cut); in fact also a crop, a width beyond the trained size and more visual tokens (note at the top) |

The perturbation views move the content by a few percent without zooming. The bands carry
more pixels per read than the grid did (width 1,536 to 3,087 px, median 2,366, on these pages;
3,330 px is reached only by a landscape page); the visual-token count of every read is recorded
and checked against the size read (`visual_token_check` in the analysis output).

## 4. Measures, fixed before the run

Lines and scorer exactly as P-ZOOM §3 and §7 (`p_zoom_analysis.score_page`): `text`,
`figure_only`, `not_found` for each of 71 absent lines (387 marks) and 42 control lines.

- **Gain of a view** = marks of absent lines the view recovers as text and the baseline read
  does not, as a share of the 387; **loss** the reverse.
- **N** (perturbation gain) = mean of the gains of `pad` and `scale90`. **Z** (zoom gain) = gain of
  `bands`.
- Union shares of absent marks recovered as text by: baseline; baseline + perturbation views;
  baseline + bands; all four.
- **Control**: share of control marks the bands find as text.
- Paired bootstrap over the 21 pages (seed 20261004, 2,000 resamples) for the 95% interval of
  `Z − N`. Reported, not used by the rule.
- Also reported: reads reaching `max_new_tokens`, tokens, visual tokens, seconds.

## 5. Readings fixed in advance (`p_zoom2_analysis.reading`)

Thresholds are judgements (10 points = 39 marks; 80% control floor), not derived from data. In
lines the 10 points are not "about 7": marks per line are very skewed (median 3, 17 of 71 lines
have one mark, the heaviest line has 49 and the two heaviest 96, 24.8% of all marks), so the
threshold can be met by one to three lines.

1. **Control first.** Bands find < 80% of control marks ⇒ `instrument_fails_control`: the bands
   lose ordinary lines too, and the round says nothing about zoom.
2. **`zoom_adds_beyond_perturbation`**: `Z ≥ 10` points and `Z − N ≥ 10` points. Zoom recovers
   absent text that a mere change of input does not.
3. **`perturbation_explains_gain`**: otherwise, `N ≥ 10` points. A change of input alone
   recovers about what the band view does, so P-ZOOM's gain does not need zoom to be explained. (A
   union of several reads is higher than any single read for any extra read; whether views
   complement one another beyond that needs a same-read-count comparison this pilot lacks.)
4. **`no_gain_from_views`**: otherwise.

Consequences, each a *next draft*, never a run, and only through the controlled reading of
`P_ZOOM3_CONTROLS_DRAFT.md` §4 for anything about zoom: a registered re-read with order-free v2
precision charged; a registered multi-view fusion with the same charge and a same-read-count
comparison.

## 6. Cost and claims

105 reads, one T4 session, estimated 1 to 1.3 GPU-hours from the P-ZOOM rates (a whole-page
read took 48 s median in T1; a tile about 24 s). 0.55 of this week's 3-hour pzoom budget is
used; the smoke runs on the secondary account first. Claim level
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`; Typhoon only; 21 pages, 71 lines.
