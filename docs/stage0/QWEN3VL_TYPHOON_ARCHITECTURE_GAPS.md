# Qwen3-VL-2B / Typhoon OCR 1.5 — layer map and research entry points

**Status: `DESIGN_ANALYSIS`, nothing authorized.** Every architectural number
below was read from the pinned configs and from
`transformers/models/qwen3_vl/modeling_qwen3_vl.py` (transformers 5.12.0), not
recalled. Literature entries were located by search and their abstracts read;
none is fully audited.

Pinned: `Qwen/Qwen3-VL-2B-Instruct@89644892e4d85e24eaac8bacfd4f463576704203`,
`typhoon-ai/typhoon-ocr1.5-2b@9c8a8fa14905041d793f1e4e922312147956dcc0`.
**The two configs are identical** except dtype metadata: Typhoon is a full
fine-tune of exactly this architecture, so every difference between them lives
in the weights.

## 1. Pipeline, stage by stage

| # | stage | Qwen3-VL-2B / Typhoon | PaddleOCR-VL-1.6 / Wayu |
|---|---|---|---|
| 1 | resize | `smart_resize`, factor 32, floor 65,536 px, ceiling 16.7 M px; Typhoon's card resizes long side to 1,800 px | factor 28, floor 112,896 px |
| 2 | patch embed | `Conv3d`, kernel (2, 16, 16): an image is duplicated along time; 16×16 px → 1,024-d | 14×14 px → 1,152-d |
| 3 | position | learned absolute table of 48×48 = 2,304, **bilinearly interpolated** to the actual grid, plus 2-D RoPE inside attention | NaViT-style |
| 4 | vision blocks | 24 layers, hidden 1,024, 16 heads, full attention within each image | 27 layers, hidden 1,152 |
| 5 | **DeepStack taps** | outputs of vision layers **5, 11, 17** each pass through their own merger (LayerNorm on the 2×2 concatenation, 4,096 → 4,096 → GELU → 2,048) | none |
| 6 | main merger | output of layer 23: LayerNorm per patch, concatenate 2×2 = 4,096, MLP → 2,048. **One LLM token = 32×32 px** | 2×2 merge, one token = 28×28 px |
| 7 | language model | 28 layers, hidden 2,048, GQA 16 query / 8 KV heads, head dim 128, SiLU MLP 6,144, tied embeddings, vocab 151,936 | 18 layers, hidden 1,024, vocab 103,424 |
| 8 | **DeepStack injection** | residual add **at visual positions only**: vision L5 after LLM layer 0, L11 after layer 1, L17 after layer 2 (`_deepstack_process`) | none |
| 9 | positions in LLM | interleaved M-RoPE, sections (t, h, w) = (24, 20, 20) over 64 frequency pairs, θ = 5×10⁶ | M-RoPE, non-interleaved |
| 10 | output | Markdown / HTML tables / `<figure>`; Qwen BPE at 0.57 tokens per Thai character; a tone mark shares a token with its base consonant only 23% of the time | 0.69 tokens/char, 46% with base |

## 2. What the geometry does to a Thai tone mark

| input | resized to | ViT patches | LLM visual tokens | area scale |
|---|---|---|---|---|
| TEMS crop (41×176) | 128×544 | 272 | 68 | **9.65×** |
| mekpro `official` median (537×651) | 544×640 | 1,360 | 340 | 1.00× |
| A4 page at 1,800 px long side | 1,792×1,280 | 8,960 | 2,240 | 1.00× |

Measured on a mekpro `official` page: text-line ink bands are **~15 px tall**
(median; including stacked marks). The consequences, as inference from the
geometry rather than measurement:

- A whole Thai cluster — base consonant, upper vowel, tone mark, lower vowel —
  fits inside **one 16-px patch row**. The tone mark is a few pixels of one
  patch that also contains its base and neighbours.
- After the 2×2 merge, one LLM token spans 32×32 px: **about two text lines
  and two to three characters** fused into a single 2,048-d vector.
- The patch grid is not aligned to the text baseline. A line can straddle a
  patch boundary, so a tone mark and its base can land in different patch rows
  depending only on where the page happens to sit.
- TEMS crops are upsampled ~10× here too, so the magnification regime of
  rounds 1–3 would repeat. mekpro pages render at native scale.

## 3. Entry points for the research question

Each is training-free. Ordered by how directly it addresses the finding in
`THAI_MARK_FAILURE_MODES.md` §7 — tone marks fail on correctly read consonants
at 3–4× the vowel rate, and compression does not change that rate.

### G1. Does tone-mark evidence travel through DeepStack?

*Hypothesis.* Fine positional detail lives in shallow and middle vision layers;
the deep main path carries what the model needs to name a character. Tone marks
need both. If their evidence rides the L5/L11/L17 taps, then removing a tap
should raise tone-mark error disproportionately to consonant error.

*Intervention.* Forward hook that zeroes or scales each of the three DeepStack
injections separately, and all three together. Measure mark-specific error per
component.

*Literature.* DeepStack ([arXiv:2406.04334](https://arxiv.org/abs/2406.04334),
NeurIPS 2024) reports its largest gains on TextVQA and DocVQA. Qwen3-VL
([arXiv:2511.21631](https://arxiv.org/abs/2511.21631)) adopts it. A layer-selection
study ([arXiv:2504.21447](https://arxiv.org/abs/2504.21447), EMNLP 2025) finds
deep layers best for OCR but shallow and middle layers best for fine positional
tasks — a tension Thai marks sit exactly on. **No located work ablates DeepStack
for diacritics.** Search-level only; not a claim of absence.

*Why it matters for compression.* Any token reduction on this architecture must
decide what happens to the three DeepStack streams. An OCR pruning audit on
Qwen3-VL-8B ([arXiv:2608.00077](https://arxiv.org/abs/2608.00077)) does not say,
in its abstract, how DeepStack was handled.

### G2. Does the patch grid decide whether a mark survives?

*Intervention.* Translate each page vertically by 0–15 px (sub-patch phase)
with padding, holding scale fixed. If tone-mark error oscillates with phase
relative to the 16-px grid while consonant error does not, the grid alignment —
not resolution — governs mark survival.

*Why it is clean.* Scale, content and token count are unchanged; only where
the grid falls on the glyphs moves.

### G3. Where is this model's scale optimum on pages?

Replicate the round-3 magnification sweep on mekpro `official`. Typhoon was
trained at 1,800 px; whether its optimum sits there, and whether the tone-mark
curve has the same shape as the consonant curve, is the page-level analogue of
the one robust result rounds 1–3 produced.

### G4. Where does Thai specialization live?

The architectures are identical, so the base/descendant pair supports two
experiments nothing else here can:

- **Weight delta per module** — relative change in patch embed, each vision
  block, each DeepStack merger, main merger, each LLM layer. No inference.
- **Component swap** — Typhoon with the base's vision tower, base with
  Typhoon's, and likewise for mergers and DeepStack mergers. Whichever swap
  moves tone-mark error locates where the Thai-mark gain is carried.

### G5. Perception or readout?

At each generated step that should emit a toned token: the probability margin
between the toned and untoned candidates, a logit lens over LLM layers, and the
attention mass on the visual tokens covering the mark's 32×32 cell. A mark that
was perceived but lost at readout looks different from one never encoded.

### G6. Compression, revisited

With DeepStack there are five insertion points: pre-ViT (PixelPrune exists for
Qwen3-VL-2B), inside the vision tower, post-merger main tokens, DeepStack
tokens, and inside the LLM (FastV, ET-Prune). **The efficiency conclusion of
rounds 1–3 does not transfer automatically**: those sequences had 40–160 visual
tokens, where prefill was ~21 ms of ~300 ms. A page carries 340–2,240. Whether
post-encoder reduction buys real time at page scale has to be measured, not
assumed from the crop results.

## 4. Prerequisites before any of it

1. A FULL baseline for Typhoon and the base on mekpro `official` band,
   including the §7 mark-specific decomposition — one new factor at a time.
2. An output normalization rule for Markdown and HTML, fixed before results are
   seen; reading order likewise.
3. Typhoon's card states it works only with its own prompt; the prompt is part
   of the pinned contract.
4. Pruning, if it returns, must be re-implemented for DeepStack.
5. Pinned revisions only — `main` falls outside the 2026-09-25 licence decision.
