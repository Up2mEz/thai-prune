# ThaiOCRBench — which tasks can carry the research question

**Status: `TASK_SELECTION_PROPOSAL`, nothing authorized.** Profiled without model
weights by Kaggle kernel `labbs2026-thaiocrbench-profile` on
`typhoon-ai/ThaiOCRBench@ca610d1ab330` (2,808 items, 13 tasks).

ThaiOCRBench was published at the IJCNLP-AACL 2025 main conference
([arXiv:2511.04479](https://arxiv.org/abs/2511.04479)). Card licence:
CC-BY-SA-4.0. It comes from the same group as Typhoon OCR.

## Selection criteria, fixed before looking at any model output

1. **A transcription target**, so the per-component decomposition of
   `THAI_MARK_FAILURE_MODES.md` §7 applies.
2. **No formatting convention in the target** — the lesson of mekpro's
   `table` subset.
3. **Enough Thai marks** for tight intervals. TEMS had 337 tone marks in 400
   regions.
4. **Images not systematically below the pixel floor** — the lesson of TEMS.

Token counts use Typhoon OCR 1.5's card policy: long side resized to 1,800 px,
then `smart_resize` (factor 32, floor 65,536 px). "Scale" is processed area over
native area.

## All thirteen tasks

| task | n | native area p50 | tokens p50 | scale p50 | answers with markup | tone marks | upper | lower | verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Full-page OCR** | 197 | 1.64 M | 2,240 | 1.47 | 31 | **17,188** | 24,132 | 4,705 | **primary** |
| **Text recognition** | 333 | 1.85 M | 2,352 | 1.37 | 13 | **4,243** | 5,534 | 1,184 | **primary** |
| **Fine-grained text recognition** | 206 | 1.64 M | 2,352 | 1.47 | 0 | 386 | 463 | 109 | secondary, mechanistic |
| Handwritten content extraction | 209 | 1.99 M | 2,352 | 1.15 | 30 | 1,829 | 1,934 | 549 | excluded for now |
| Document parsing | 211 | 0.61 M | 2,296 | 4.25 | **211** | 14,980 | 20,876 | 4,019 | excluded |
| Table parsing | 193 | 1.41 M | 2,296 | 1.67 | **193** | 6,399 | 10,122 | 2,316 | excluded |
| Chart parsing | 200 | 0.62 M | 1,960 | 3.28 | **200** | 3,768 | 5,101 | 925 | excluded |
| Key information extraction | 201 | 0.31 M | 2,352 | 9.53 | **201** | 2,577 | 4,329 | 588 | excluded |
| Key information mapping | 209 | 0.53 M | 2,352 | 4.50 | **209** | 1,322 | 2,769 | 245 | excluded |
| Infographics | 213 | 1.64 M | 2,520 | 1.55 | 24 | 599 | 696 | 133 | excluded |
| Cognition VQA | 217 | 1.46 M | 2,352 | 1.75 | 8 | 339 | 557 | 122 | excluded |
| Diagram VQA | 204 | 1.40 M | 2,352 | 1.63 | 0 | 209 | 439 | 97 | excluded |
| Document classification | 215 | 0.50 M | 2,296 | 4.64 | 0 | 79 | 342 | 44 | excluded |

## Why each selected task qualifies

### Full-page OCR — primary

- Prompt asks for plain text (*"แสดงออกมาเป็นข้อความธรรมดา (plain text)"*),
  85 phrasings of one instruction.
- **17,188 tone marks — 51× TEMS.** Component intervals will be tight.
- **Real documents**, not rendered synthetic pages: Government 54, Education 35,
  Lifestyle 18, Medical 16. This removes the external-validity cost that mekpro
  carried.
- Native pages are large (p50 1.64 M px), so reduced budgets genuinely discard
  source pixels for most items.
- The 31 "markup" hits are mostly leading `- ` bullets that are real document
  text, not serialisation.
- Every answer is multi-line, so reading order is live; line breaks in the
  reference make a line-level, order-robust sensitivity metric possible.

### Text recognition — primary

- Scene and signage photographs, often 3,024×4,032, where the text is small
  relative to the frame — the regime where fine marks are most at risk.
- 4,243 tone marks; answers p50 99 characters; mixed Thai–English.
- 242 phrasings of "what does the text in the image say".
- **A formatting convention exists in some answers**: separate text blocks are
  joined with ` | ` (e.g. a Thai line `| Thank you`). Only 13 answers are
  flagged, but the normalization rule must be registered before any output is
  scored.

### Fine-grained text recognition — secondary, mechanistic

- Every question gives a box in 0–1000 normalized coordinates, the convention
  Qwen3-VL uses for grounding; answers are short (p50 18 characters).
- Only 386 tone marks: too few for the primary decomposition.
- **Its value is design, not power.** Because the box is given, each item can
  be run twice — whole image plus coordinates, and an oracle crop of that box
  with a plain reading prompt. The difference separates *finding* the text from
  *reading* it, without training.
- Risk: Typhoon's OCR fine-tune may have weakened grounding relative to the
  base, which would show up here as a localization effect, not a reading one.

## Why the rest are excluded

- **Markup in every answer** — Document parsing (scored by tree edit
  distance), Table, Chart, KIE, KIM. The target mixes structure with text.
- **Not transcription** — the three VQA tasks and Document classification;
  few marks and free-form answers.
- **Handwriting** is a different visual domain and several questions are
  VQA-like ("หัวข้อที่ 3 ... เขียนว่าอย่างไร"). Reserve for later.

## Conditions any registration must meet

1. **Stratify by native scale.** Scale ranges from ~0.2 to ~7 across items.
   Items the processor upsamples heavily reproduce the TEMS regime, where
   resolution reduction discards nothing. The primary population for any
   compression arm must be the items where the lowest budget genuinely
   discards source pixels, counted exactly before the run.
2. **Prompt.** Typhoon's card says it works only with its own prompt; the
   benchmark ships Thai question prompts and a published metric (BMFL). The
   baseline run should score both prompts for both models, and one must be
   pinned before any compression or ablation arm.
3. **Normalization** of Markdown (Typhoon), ` | ` separators, whitespace and
   line breaks — fixed before scoring.
4. **Metrics.** CER and the §7 component decomposition primary; the
   benchmark's own BMFL secondary, for comparability with the published table.
5. **Contamination.** Typhoon's report (arXiv:2601.14722) does not evaluate on
   ThaiOCRBench and makes no decontamination statement; the benchmark draws on
   "publicly available materials, and licensed commercial datasets". Typhoon's
   absolute scores must be read with that in mind. Within-model contrasts —
   component decomposition, DeepStack ablation, compression deltas — are less
   exposed than base-versus-Typhoon level comparisons.
6. **Licence.** CC-BY-SA-4.0: results may be reported; derived images or crops
   may not be redistributed under another licence. Whether the researcher's
   2026-09-25 rule for Apache-2.0 extends to this card licence is a human
   decision not yet recorded.
7. **Cluster unit** is the item (image); `category` is a stratum.
