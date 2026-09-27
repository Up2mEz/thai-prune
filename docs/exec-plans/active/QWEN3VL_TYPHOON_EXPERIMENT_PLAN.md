# Research plan — fewer Thai vowel and tone-mark errors, at similar speed, without training

**Status: `PLAN_PENDING_HUMAN_REVIEW`.** Supersedes the 2026-09-27 draft of this
file (in git history), which the researcher rejected for defaulting to pruning
and to the `MODEL x BUDGET` frame. Authorizes nothing.

## 0. The goal, as the researcher stated it

Make a Thai document VLM misread vowels and tone marks less often. Any
training-free technique is admissible — pruning is not required. Faster is
better; slightly slower is acceptable. Test only what the next decision needs.

**Conflict with the current spec, for the researcher to resolve.**
`RESEARCH_SPEC.md` frames the project as a robustness evaluation under reduced
visual information and says it "does not assume … a new method is required";
the gate map puts a new method at Gate 5, after existing methods are fairly
evaluated. The goal above is a remedy study. The plan below keeps the gate
*logic* — diagnose, then evaluate existing training-free remedies, then a new
one only if a gap remains — but `RESEARCH_SPEC.md` §1–§3 need amending to the
new objective. Draft wording is in §8.

## 1. Foundations

### 1.1 How a VLM transcribes a mark

- **OCR in VLMs is dense copy-and-paste.** In Qwen3-VL-2B the heads that read
  text substantially overlap the retrieval/copy heads; OCR specialization
  keeps their identity and redistributes their importance
  ([arXiv:2609.21543](https://arxiv.org/abs/2609.21543)). Each emitted token is
  retrieved from visual evidence and weighed against the language model's
  prior.
- **The prior can override the image.** In Greek and Arabic, a fluent error
  produced largely without the image appears in OCR-specialist models while
  general-purpose models stay grounded even when wrong
  ([arXiv:2605.27750](https://arxiv.org/abs/2605.27750)). Diacritics are 37–57%
  of VLM errors in Greek against 16–17% for classical OCR. It supplies the
  measuring tool used below: **image gain**,
  `log p(t | image, prompt) − log p(t | prompt)` under teacher forcing,
  available on Qwen-architecture models.
- **Stacked-mark scripts fail structurally.** On Devanagari, VLMs fail on
  matras and conjuncts while classical OCR fails on surface elements
  ([arXiv:2606.29213](https://arxiv.org/abs/2606.29213)).

### 1.2 What the geometry does to a Thai mark

From `QWEN3VL_TYPHOON_ARCHITECTURE_GAPS.md`: text lines of ~15 px against 16 px
patches, so a base consonant, its vowels and its tone mark share one patch row;
one LLM token spans 32×32 px, about two lines and two or three characters. The
tone mark is a few pixels of a vector dominated by its base.

### 1.3 What the language does

- A Thai tone mark is **lexically contrastive** — นา, หน่า, หน้า, น้า, หนา
  differ only in tone. A lexicon cannot always decide it; the image must.
- **The choice set is tiny and structured.** At a position where a tone mark
  may legally attach there are five options: none, ่, ้, ๊, ๋. Orthography
  fixes where it can attach.

### 1.4 What this project has already measured

On PaddleOCR-VL/TEMS (`THAI_MARK_FAILURE_MODES.md`): tone marks are wrong on
correctly read consonants 25.7% of the time against 7.9% for upper vowels;
the failure is mostly **deletion**, confusion between tone marks is ~2%;
the model writes no orthographically illegal sequences; the tone-mark rate
does not move with compression. **None of this has been measured on
Qwen3-VL/Typhoon.**

## 2. Candidate remedies, by family

| family | representative work | what the evidence says | fit to the constraints |
|---|---|---|---|
| contrastive decoding | VCD ([CVPR 2024](https://arxiv.org/abs/2311.16922)), M3ID | Greek/Arabic: effects small and **reverse sign across scripts** | ~2× forward passes; global, can harm |
| attention amplification | PAI ([arXiv:2407.21771](https://arxiv.org/abs/2407.21771)) — counters "text inertia" | hallucination benchmarks; not OCR | near-free |
| OCR-head intervention | OCR Heads ([EMNLP 2025](https://arxiv.org/abs/2505.15865)) — sink-token redistribution improves performance | not tested on diacritics | near-free once heads are found |
| latent steering | VTI ([ICLR 2025](https://arxiv.org/abs/2410.15778)) | hallucination | near-free; needs a steering direction |
| zoom / visual search | ViCrop ([ICLR 2025](https://arxiv.org/abs/2502.17422)), ZoomEye ([EMNLP 2025](https://arxiv.org/abs/2411.16044)) | strong on small detail | ZoomEye: many passes, **violates the speed constraint** |
| text-only post-correction | "No Free Lunches" (ACL 2025 workshop); reference-based (AAAI 2025) | helps Greek, **hurts Arabic**; byte-level correctors do not transfer across engines | cheap; blind to the image |
| script-restricted decoding | tested in arXiv:2605.27750 | **highly damaging** in Greek | — |
| speculative decoding | HSD ([arXiv:2602.12957](https://arxiv.org/abs/2602.12957)) — training-free, drafts from PP-StructureV3, 2.6× on Qwen3-VL-8B | EN/ZH only | **speed without changing the output** under exact verification |

## 3. The gap

- No located work measures VLM tone-mark or vowel errors in Thai, or tests any
  remedy on them. Search-level only; not a claim of absence.
- The Qwen3-VL-2B specialization study (2609.21543) analyses heads but proposes
  no fix and analyses no diacritics.
- The prior-override finding (2605.27750) predicts that Typhoon, an OCR
  specialist, should show more prior-driven mark errors than its general base.
  Nobody has tested that on Thai, and this pair is the cleanest possible test:
  identical architecture, weights differ.

## 4. Proposed contribution

**Mark-constrained, image-contrastive re-scoring.** A descriptive name; it is
not an existing method.

1. Decode greedily as usual.
2. At syllables where a tone mark or vowel could legally attach and the model is
   uncertain (low top-1 margin), enumerate the orthographically legal variants
   that differ **only** in that mark — at most five for a tone mark.
3. Score every variant in one batched teacher-forced pass, with and without the
   image, and choose by `log p(v | image) − λ·log p(v | no image)`.
4. Consonants are never touched.

*Why it should work.* The candidate set is tiny and legal by construction, so
it cannot produce illegal Thai or wander into other words the way free
post-correction does. It is grounded — every choice is scored against the
image — so it attacks prior-override directly. And it acts only where the model
is uncertain, which contains the global side effects that made contrastive
decoding reverse sign across scripts.

*When it would fail, stated in advance.* If the correct variant does not score
highest under the image even with the full candidate set available, the
evidence is not in the representation, and no decoding-time method can recover
it; the remedy must move to the input side. §5 test T2 measures exactly this
before anything is built.

*Speed.* Re-scoring is prefill-only and touches a few syllables. If it still
costs time, speculative decoding (HSD-style, with drafts from a classical Thai
OCR pipeline) can recover it without changing the output under exact
verification.

## 4b. What to build after T1/T2 — routed by outcome, not decided now

`docs/stage0/T1_T2_CONTINGENT_REMEDY_PLAN.md` fixes, before either test has
run, which remedy family is indicated by each way the four T2 numbers
(headroom, image_gain, oracle_accuracy, real_word_share) could come out. It
also carries literature found after this plan was written, including a
mechanism paper that names the prior-override hypothesis directly
(arXiv:2605.08245) and a training-free candidate this plan did not have: a
scale-diverse consensus vote restricted to the mark sites T2 flags, combining
this project's own round-3 magnification finding with published consensus-
voting methods.

## 5. What to test now — and only this

Both on a calibration split (≈30%, seeded, stratified by task × category) of
ThaiOCRBench Full-page OCR and Text recognition. The remaining ≈70% stays
locked.

**T1 — FULL baseline, both models.** CER; the base-conditioned mark-specific
decomposition; deletion versus confusion; non-word versus real-word mark errors
against a Thai lexicon; decode ms/token. Answers: is the mark problem present
on this backbone, and is it prior-shaped (real-word substitutions) or
perception-shaped (non-words, deletions)?

**T2 — oracle variant scoring, no generation.** For every reference syllable
carrying a tone mark or vowel, teacher-force all legal variants with and
without the image. Report how often the correct variant wins, against how often
greedy decoding got it right, and the image gain at mark positions. This is the
upper bound on §4's method and the direct test of prior-override. It is
prefill-only and therefore cheap.

**Decision after T1–T2**, by the researcher: build §4, move to an input-side
remedy, or first evaluate the existing families of §2 on Thai.

## 6. What is deliberately not tested yet

| deferred | why |
|---|---|
| pruning, merging, any compression | not the goal; speculative decoding is the better speed lever |
| quantization | decode cost on this backbone is unmeasured; T1 measures it first |
| ZoomEye | many forward passes per image; violates the speed constraint |
| DeepStack ablation, patch-phase shift | become worth running only if T2 says the evidence is missing from the representation |
| weight delta, component swap, head analysis | mechanistic; not needed for the next decision |
| the §2 existing families | evaluated after T2, so the comparison is against the right upper bound |
| Handwriting, Fine-grained tasks | later, if the method works on the primary tasks |

## 7. Governance still required

Models pinned to the SHAs in the 2026-09-25 and 2026-09-27 entries.
ThaiOCRBench cleared 2026-09-27b. The Thai lexicon for the non-word split needs
its own licence check. T1 and T2 each need a registration before they run.

## 8. Draft amendment to `RESEARCH_SPEC.md` (for the researcher)

> **Objective.** Reduce Thai vowel and tone-mark transcription errors in a
> page-level OCR VLM without training, at comparable or better inference speed,
> and explain the mechanism of the errors it removes.
>
> **RQ-A.** Are Thai mark errors on Qwen3-VL-2B and Typhoon OCR 1.5 driven by
> missing visual evidence or by the language prior overriding it?
>
> **RQ-B.** Does a training-free remedy reduce mark-specific error without
> raising other errors, and at what latency?
>
> **RQ-C.** Does OCR specialization change the balance between evidence and
> prior for Thai marks?
