# How Thai marks fail — diagnostic on round 3

**Status: `DESCRIPTIVE_DIAGNOSTIC_ONLY`.** Computed after the run, on data already
fetched, with no registration. No intervals, no tests, alignment-dependent. It
exists to decide which training-free remedies are even worth registering, not to
support a claim.

Data: `kaggle-region-ocr-db8b5b1bf59b`, 400 TEMS regions, `PaddleOCR-VL-1.6`.

## 1. The tone-mark gap is not a Unicode artefact

The project's CER is computed over raw codepoints with no normalization. Two
strings that render identically but order their combining marks differently
would count as an error, and that could inflate exactly the stacked-mark
components this project studies.

It does not. Normalizing both reference and hypothesis changes nothing:

| condition | component | raw | NFC | NFKC |
|---|---|---|---|---|
| `FULL` | tone mark | 35.9% | 35.9% | 35.9% |
| `FULL` | upper vowel | 18.0% | 18.0% | 18.0% |
| `FULL` | lower vowel | 20.1% | 20.1% | 20.1% |
| `FULL` | base consonant | 16.8% | 16.8% | 16.8% |
| `PRUNE_GRID_25` | tone mark | 43.9% | 43.9% | 44.2% |

**0 of the 241 regions wrong at `FULL` become correct after NFKC.** Whatever the
gap between tone marks and consonants is, ordering is not it.

## 2. What happens to a reference tone mark

Aligned with a codepoint Levenshtein backtrace. The split between "deleted" and
"aligned to a non-tone character" depends on tie-breaking and is not robust; the
first two rows are.

| fate | `FULL` | `RR_50` | `PRUNE_GRID_25` |
|---|---|---|---|
| correct | 64.1% | 72.1% | 56.1% |
| **replaced by a different tone mark** | **2.1%** | **2.1%** | **2.4%** |
| deleted | 16.9% | 12.5% | 16.3% |
| aligned to a non-tone character | 16.9% | 13.4% | 25.2% |

n = 337 reference tone marks in every condition.

**The model almost never confuses one tone mark for another.** The
visually-motivated story — ่ read as ้ — accounts for about 2% of tone marks.
The failures are the mark disappearing, or the surrounding syllable being misread
so that the mark aligns against something else.

## 3. The model does not write illegal Thai

Counting placements no Thai spelling allows — a tone mark with no consonant or
vowel to sit on, an upper or lower vowel with no consonant beneath or above it:

| | hypotheses | references |
|---|---|---|
| `FULL` | 2 | 2 |
| `RR_50` | 2 | 2 |
| `PRUNE_GRID_25` | 0 | 2 |

The hypotheses contain no more illegal placements than the ground truth does.

## 4. What this rules in and out

- **Orthography-constrained decoding has essentially no headroom here.** A
  decoder mask that forbids illegal mark sequences would forbid sequences the
  model does not produce. Ruled out on this evidence, for this model and corpus.
- **Remedies aimed at tone-mark confusion have ~2% to work with.** Not worth
  registering as tone-mark remedies.
- **Deletion is the target.** It is the largest reliable bucket, and it is where
  scale moved the numbers: `RR_50` deleted 42 marks against `FULL`'s 57, a 26%
  reduction with fewer visual tokens and a cheaper encoder.
- ~~**Much of the remaining loss is word-level.**~~ *Superseded by §7:* for
  tone marks it is not. Most tone-mark errors occur on syllables whose base
  consonant was read correctly. The word-level reading holds for vowels only.

## 5. Caveat on the scale result

`RR_50` was identified as good on the same 400 regions it is scored on. The
improvement is therefore optimistic by selection. It needs confirming on data it
was not chosen on — the TEMS evaluation split is unopened, and opening it is a
protocol decision, not an analysis step.

## 6. Is deletion caused by the tokenizer? (tested 2026-09-25, not supported)

**Hypothesis.** Both tokenizers split most tone marks away from their base
consonant. `PaddleOCR-VL-1.6` encodes `ไฟฟ้า` as `ไ | ฟ | ฟ | ้า`: the tone mark
rides on the *following* vowel's token. Writing the word correctly then means
choosing `้า` over the near-identical `า`, and a "deleted" tone mark could be that
choice going the wrong way — a decoding event rather than a perceptual one.

**Tokenization, 400 TEMS references:**

| tokenizer | tokens per character (median) | tone mark with its base | fused to the next character | a token on its own |
|---|---|---|---|---|
| `PaddleOCR-VL-1.6` | 0.69 | 46% | 43% | 12% |
| `Qwen3-VL-2B-Instruct` | 0.57 | 23% | 41% | 36% |

**Test.** Round-3 fate of each reference tone mark, by where the reference
tokenizer put it (`PaddleOCR-VL-1.6`; 43 regions skipped because their tokens do
not round-trip character by character):

| condition | category | n | correct | deleted |
|---|---|---|---|---|
| `FULL` | with base | 126 | 61.9% | 21.4% |
| `FULL` | fused forward | 127 | 68.5% | 13.4% |
| `FULL` | alone | 38 | 50.0% | 18.4% |
| `RR_50` | with base | 126 | 67.5% | 18.3% |
| `RR_50` | fused forward | 127 | 78.7% | 7.9% |
| `PRUNE_GRID_25` | alone | 38 | 34.2% | 23.7% |

**Result: the simple hypothesis is refuted.** Marks fused into the next
character's token are deleted *less* often than marks kept with their base, in
every condition, not more. Token position is associated with accuracy — marks
tokenized on their own do worst — but that association is confounded with which
words those patterns occur in (`้า`, `้อ` are frequent), and n is small with no
intervals. Nothing here establishes the tokenizer as a cause, and changing a
tokenizer would require retraining in any case.

## 7. Tone marks fail on their own, not as collateral (2026-09-25)

The question §4 left open: is the tone-mark gap real, or do tone marks merely
fail when their whole syllable is misread? Each reference mark is split by
whether its base consonant — the nearest preceding consonant, skipping other
marks — was read correctly. A mark wrong on a correctly-read base is a
*mark-specific* error.

| condition | mark | n | mark-specific error (base correct) | error when base wrong | share of errors riding on a wrong base |
|---|---|---|---|---|---|
| `FULL` | **tone** | 337 | **25.7%** (of 288) | 95.9% | **39%** |
| `FULL` | upper vowel | 638 | 7.9% (of 542) | 75.0% | 63% |
| `FULL` | lower vowel | 154 | 5.7% (of 123) | 77.4% | 77% |
| `RR_50` | **tone** | 337 | **21.4%** | 78.9% | 32% |
| `RR_50` | upper vowel | 638 | 7.1% | 73.0% | 57% |
| `PRUNE_GRID_25` | **tone** | 337 | **24.7%** | 83.6% | 62% |
| `PRUNE_GRID_25` | upper vowel | 638 | 11.8% | 80.6% | 76% |

**Findings.**

1. **On a correctly-read consonant, a tone mark is still wrong about a quarter
   of the time** — 3.3× the upper-vowel rate and 4.5× the lower-vowel rate at
   `FULL`. Most tone-mark errors (61%) are mark-specific. For vowels the reverse
   holds: most of their errors ride on a misread base.
2. **The mark-specific tone error barely moves with compression**: 25.7% at
   `FULL`, 21.4% at `RR_50`, 24.7% at `PRUNE_GRID_25`. What pruning adds is
   syllable-level damage — the share of tone errors riding on a wrong base
   rises from 39% to 62%.

**What this is and is not.** It is evidence of a higher *baseline*
mark-specific error for tone marks in this model on this corpus. It is **not**
evidence that tone marks *degrade faster* under compression — on this measure
they do not — and `AGENTS.md` forbids assuming that they do. §2 already showed
the mark-specific failure is overwhelmingly deletion rather than confusion
between tone marks.

**Limits.** No intervals. Alignment-dependent. "Base consonant" is a heuristic,
and conditioning on a correct base selects easier syllables, which if anything
should *lower* the tone rate. One model, one corpus, scene text.

## 8. Why quantization would not make this model faster (2026-09-25)

Measured at `FULL` on a T4, fp16, batch 1, Hugging Face `generate()`:

| | value |
|---|---|
| generated tokens per region, median | 12 |
| seconds per generated token, median | **0.0202** (p10 0.0194, p90 0.0213) |
| decoder weights read per token (18 layers, hidden 1024, vocab 103,424, incl. `lm_head`) | ~318 M params, **0.64 GB** fp16 |
| T4 bandwidth floor per token | **1.99 ms** fp16 · 0.99 ms int8 · 0.50 ms int4 |

**Decode runs at about ten times its memory-bandwidth floor.** Weight reads
account for roughly 2 ms of each 20 ms token; the remaining ~18 ms is per-kernel
launch and Python overhead in the generation loop, which quantization does not
touch. Even an ideal int4 conversion could remove at most ~1.5 ms per token,
under 8% of decode, and real dequantization kernels would give some of that
back. Peak memory is 1.87 GB, so there is no memory pressure to relieve either.

**For a model this small at batch 1, quantization has almost nothing to act on.**
The levers that address the ~18 ms overhead — CUDA graphs or `torch.compile`,
a serving engine such as vLLM, batching several regions per call — are
engineering rather than research. The bandwidth figure is approximate (KV-cache
and activation reads are ignored), but the order-of-magnitude gap is not.
