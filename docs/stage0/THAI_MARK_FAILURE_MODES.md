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
- **Much of the remaining loss is word-level.** A tone mark counted wrong because
  its whole syllable was misread is not a mark-specific failure. Whether the
  tone-mark gap survives once word-level misreads are separated out is an open
  question and should be asked before any claim that tone marks are
  intrinsically more fragile — as `AGENTS.md` already requires.

## 5. Caveat on the scale result

`RR_50` was identified as good on the same 400 regions it is scored on. The
improvement is therefore optimistic by selection. It needs confirming on data it
was not chosen on — the TEMS evaluation split is unopened, and opening it is a
protocol decision, not an analysis step.
