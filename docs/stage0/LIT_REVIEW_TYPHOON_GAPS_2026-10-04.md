# Literature review → experiments for Typhoon's remaining gaps (2026-10-04)

Three verified literature searches (loops in VLM OCR; training-free accuracy
methods; Thai OCR and post-correction), each source opened and checked; the
few unverifiable claims are marked. Combined with our own measurements
(calibration, Typhoon OCR 1.5, greedy). The researcher asked for the review
to be turned into experiments and run (session 2026-10-04: "นำมาเป็นแนวทาง
การทดลองและทดสอบไปเลย").

## 1. What we measured (the gaps)

- **Loops** (T5/T5b): 11 of 356 greedy outputs loop; they hold ~70% of
  surplus output marks. Stopping at the loop (T5b-B) passes its dev check but
  never recovers the text the loop skipped. Two block loops (> 400
  characters) remain.
- **Misreads** (order-free): 1.5% of marks misread on full pages, 0.7%
  dropped inside kept lines. An exploratory inventory of the words with a mark
  changed (Full-page BQ, 165 words): 74% also change a consonant (whole-word
  misreads, e.g. `ค่า → คำ`, `สื่อ → สืบ`); 35% land on a real word, 55% on a
  valid non-word, 11% on an orthographically invalid shape.
- **Repetition penalty 1.1** (vendor setting) raised tone-mark error on Text
  recognition from 17.1% to 22.6%.

## 2. What the literature says, per gap

### Loops
- Mechanism: repetition is self-reinforcing; each copy raises the probability
  of the next (Holtzman et al., ICLR 2020, arXiv 1904.09751; Xu et al.,
  NeurIPS 2022, arXiv 2206.02369), also between token pairs at a distance
  (Yan et al., ICLR 2024, arXiv 2310.00297). Inference: banning an exact
  n-gram leaves the copies in context, so the next-best token is a near-copy
  — what T5 observed.
- OCR pipelines **stop or retry**, none recover in place: Nougat (arXiv
  2308.13418; logit-variance stop criterion), PaddleOCR-VL
  (`truncate_repetitive_content`), olmOCR/olmOCR 2 (retry at higher
  temperature; gain confounded), Surya (per-block crop fallback), MinerU2.5
  (block decoding + penalties), DeepSeek-OCR (n-gram ban), GOT-OCR2.0
  (`no_repeat_ngram_size=20`). Whisper's temperature fallback added 0.0 WER
  once beam search was used (arXiv 2212.04356, Table 7).
- HF `RepetitionPenaltyLogitsProcessor` penalizes every token already in the
  prompt or output. In Typhoon's tokenizer tone marks are often standalone
  tokens (`่` = 18625, `้` = 19841); a page-wide penalty therefore suppresses
  tone marks after their first use — a candidate mechanism for the T5 tone
  error rise (inference; tested in D1 below).
- No published evidence on penalties versus combining diacritics.

### Misreads
- Contrastive decoding (VCD/M3ID) did not help an OCR-specialist fine-tune on
  a diacritic-heavy script, while M3ID helped general Qwen3-VL-2B/8B
  (Karamolegkou et al. 2026, arXiv 2605.27750) — consistent with our T2.
  Script-restricted decoding raised CER 7–10×.
- Attention-redistribution methods gain little on text-rich tasks (VAR,
  ICLR 2025, arXiv 2503.03321: TextVQA +0.4–0.8). ZoomText+GLC (NeurIPS 2025,
  arXiv 2506.05551): TextVQA +1.2 on Qwen2.5-VL at 2× prefill.
- Multi-read voting: ROVER (Fiscus 1997) aligns hypotheses with NULL arcs, so
  an insertion needs a majority — the fix for the duplication that sank
  R-FUSE. Views must differ: resized views had error correlation 0.973
  (Archibald & Martinez 2025, arXiv 2509.09722). Sampled self-consistency
  lowered OCRBench by 2.8% (arXiv 2504.11101).
- Uncertainty: entropy triggers re-looking (MemVR, ICML 2025, arXiv
  2410.03577; UG-Search, arXiv 2510.00705), but VLM token probabilities are
  poorly calibrated (arXiv 2511.19806).
- Post-OCR correction at low error rates over-corrects: LLM correction hurt
  Finnish for every open model (arXiv 2502.01205); HIPE-OCRepair 2026 found
  almost no gain on low-noise input (arXiv 2607.08143). Classic Thai
  trigram+Winnow correction fixed ~90% of word errors but introduced 1.56% new
  ones (Meknavin et al., COLING-ACL 1998) — at our ~1.5% mark error, that
  would cancel the gain.

## 3. Experiments, ranked (Typhoon only; calibration; greedy)

| id | question | why first/later | cost |
|---|---|---|---|
| **D1** | Does the repetition penalty hit tone marks because they are standalone tokens? | free, offline; explains a measured harm | 0 GPU |
| **E1** | Does Typhoon's own token confidence locate its mark errors? | decides a whole family (rescoring, selective re-reading, entropy triggers) | ~0.5 GPU-h |
| **E2** | Backtrack to the loop onset and ban one token: does Typhoon then read on? | the only in-place recovery not yet tried; deterministic | ≤ 1.2 GPU-h |
| E3 | ROVER voting over ≥ 3 distinct reads (grapheme-cluster alignment) | strongest literature for misreads, but heavy engineering and needs a non-resize third view | ~1 GPU pass/page |
| — | resolution / crop re-reading | belongs to session pzoom (P-ZOOM); not duplicated here | — |
| — | not run | sampling-based retries (greedy only, `DECISION_LOG` 2026-09-28b); contrastive decoding (T2 + literature); LLM post-correction (literature negative at our error level); global or windowed penalties (D1/T5) | — |

### D1 — repetition penalty and standalone mark tokens (offline; fixed before computing)

Data: T5 `greedy` and `rep_penalty` outputs on loop-free items.
Measures, per mark class (tone, upper vowel, lower vowel): (a) the share of the
class's occurrences in the references that Typhoon's tokenizer encodes as a
standalone token; (b) output-count / reference-count of the class under each
arm; (c) Δ deletion rate of the class (`rep_penalty` − `greedy`) under
anchored alignment.
Reading: the mechanism is **supported** if the class with the highest
standalone share shows the largest drop in (b) and rise in (c) under
`rep_penalty`; **not supported** if the drops do not follow standalone share.

### E1 — does confidence locate mark errors? (registration in `E1_CONFIDENCE_DRAFT.md`)

### E2 — backtrack on loop (registration later, after E1)
