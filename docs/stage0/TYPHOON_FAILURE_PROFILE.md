# What Typhoon OCR 1.5 gets right and wrong — and a remedy proposal

**Status: `PROPOSAL`, nothing authorized.** Evidence from run
`kaggle-thai-marks-t1-t2-a44199c29759`, calibration split (178 items), scored
with `THAI_MARKS_T1_SCORING_V2.md`. Claim level
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. Typhoon only; nothing here is claimed
for base or for other models.

## 1. Typhoon rarely misreads a mark

Conditioned on a correctly read base consonant, Typhoon's mark error is
0.3–0.7% (tone, upper, lower) on Full-page OCR and 0.6–2.5% on Text
recognition. Substitutions of tone marks and vowels together are under 2% of
its errors in every cell.

## 2. Where its errors come from

Share of error characters, primary cells (`BENCHMARK_QUESTION`):

| source | Full-page OCR | Text recognition |
|---|---|---|
| text skipped in runs of ≥10 characters | 61.3% | 24.4% |
| of which found elsewhere in the output (reading order, not loss) | ~32% of those characters | ~3% |
| output never located the reference (answered another region or line) | 0% | 54.0% (10/109 items) |
| consonant substitutions (ส→ศ, น→ม, ก→ย, …) | 7.5% | 5.0% |
| tone/vowel substitutions | < 2% | < 2% |

Skipped runs cluster at the top of the page (21 of 122 runs start in the first
tenth: titles, headers, sign labels) and are concentrated in few pages (10
items hold 74% of skipped characters). None is caused by truncation
(Full-page truncation 2.9%).

**Consequence for the research question.** Measured over every reference
mark, not only those with a correct base, Typhoon reads 93.8% of marks
correctly on Full-page OCR: most of its mark errors are marks inside text it
skipped, not marks it misread. For this model, reducing mark errors means
reducing omission.

## 2b. Every wrong mark, by cause (`attribution.py`, added 2026-10-01)

Each reference mark not read correctly gets exactly one cause. Single reads
only, so anchored alignment is valid here.

| model · task · prompt | marks wrong | whole line missing | line reordered | span missing | misread, base right | misread with base |
|---|---|---|---|---|---|---|
| typhoon · Full-page · BQ | 6.2% | **50%** | 13% | 11% | 7% | 18% |
| typhoon · Full-page · TC | 7.1% | **48%** | 7% | 12% | 8% | 25% |
| typhoon · Text rec. · BQ | 17.2% | 46% | 1% | 28% | 6% | 18% |
| typhoon · Text rec. · TC | 3.5% | 5% | 7% | 26% | 19% | 44% |
| base · Full-page · BQ | 41.5% | 11% | 0% | 33% | 18% | **38%** |
| base · Text rec. · BQ | 23.0% | 1% | 0% | 33% | 24% | **42%** |

(Base under `TYPHOON_CARD` is the format failure of the scoring doc: 87–94%
"missing" because its text sits in `<figure>`.)

Of the 178 reference lines Typhoon leaves out on Full-page OCR (BQ), 124 more
are read in another order; of the 178 truly absent, 108 are digits, dates or
Latin only (page numbers, map compass letters, logos) and carry no Thai mark;
60 hold Thai marks (514 marks). The page-level loss correlates between the two
prompts (Spearman 0.50) but only 32% of lost characters are lost by both.
Neither downscaling (ρ 0.10–0.15, n.s.) nor text density (inconsistent sign
across prompts) explains which pages lose text, so resolution is **not**
supported as the cause.

**For RQ-C:** specialization changes the kind of error, not only its amount.
Base's mark errors are mostly misreadings (38% with the base consonant, 18%
of the mark alone); Typhoon's are mostly skipped lines.

## 2c. Text recognition: the misses are question-following, not reading

The 10 of 109 Text recognition items where Typhoon's `BENCHMARK_QUESTION`
answer never located the reference (questions read from the pinned
benchmark's `question` column; 84 distinct phrasings among the 109):

| failure | n | example |
|---|---|---|
| paraphrased or described instead of transcribing | 4 | asked what the yellow text says, answered with a summary of the speaker's pledge; one answer in English |
| selected the wrong text for a condition in the question | 3 | "the red Thai text", "the orange Thai text", "option 3 of item 4" |
| transcribed only the first line | 2 | a ward sign, a menu |
| declined | 1 | "I do not know what Thai text is in the image" |

Under `TYPHOON_CARD`, which asks for all text on the image, the same model
reads the reference region with 3.5% of marks wrong. On this task the
remaining errors are about which text to return and in what mode, which a
reading remedy cannot touch.

## 3. Evidence that two reads cover each other's gaps

The two prompts skip different text. Upper bound (a reference-aided choice
per character, *not* a method): marks correct 93.8% → 97.1% (Full-page OCR),
96.5% → 97.7% (Text recognition, `TYPHOON_CARD` read).

A **reference-free** rule, fixed before it was run and run once: start from
the `BENCHMARK_QUESTION` read; align the `TYPHOON_CARD` read to it; insert
every run of ≥10 characters that only the second read contains; keep the
first read on substitutions. Full-page OCR:

| read | micro CER | characters correct | marks correct | output / reference length |
|---|---|---|---|---|
| `BENCHMARK_QUESTION` | 9.8% | 91.2% | 93.8% | 1.02 |
| `TYPHOON_CARD` | 10.5% | 90.4% | 92.8% | 1.06 |
| fused | **8.9%** | **93.2%** | **95.6%** | 1.15 |

Exploratory: one rule, one run, calibration split, the same data that
suggested it. The 1.15 length shows some duplication (reordered blocks
inserted a second time).

**Correction 2026-10-01 — the gain above is a measurement artefact.** The
negative control (`CAT`: both reads concatenated, no merging) scored *higher*
on this table's metrics (96.4% marks correct), because reference-anchored
alignment and "marks correct" count only reference characters and so reward
extra text. Under global alignment with every surplus character charged
(Full-page OCR, both reads ≈ reference length, so this is the right scale):

| read | global CER | insertions / reference | mark precision | mark recall | mark F1 |
|---|---|---|---|---|---|
| `BENCHMARK_QUESTION` | 16.0% | 7.9% | 91.9% | 94.3% | 93.1% |
| `TYPHOON_CARD` | 21.3% | 11.6% | 94.5% | 92.9% | **93.7%** |
| fused (rule above, duplicate filter) | 25.5% | 18.0% | 90.3% | 94.7% | 92.5% |
| `CAT` (control) | 113.9% | 109.4% | 48.4% | 97.2% | 64.6% |

Fusion raises recall slightly and loses more precision: global CER rises 9.5
points (95% interval +0.03 to +23.0). Most inserted runs are text the first
read already has in a slightly different form, which an exact-substring
duplicate check cannot see. The upper bound in this section's first paragraph
is a recall bound only and says nothing about recoverable precision. §1–§2
stand: they are single-read measurements at ≈1.0× reference length.

## 4. Proposal — omission-recovery by fusing complementary reads (R-FUSE)

Training-free, Typhoon only first (one new factor per round).

1. **Register** the fusion rule and its single parameter (≥10-character runs)
   before any new output; evaluate on the **locked** split.
2. **Reads.** Two decodes of the same page with different prompts, as above;
   a third arm replaces the second prompt with a tiled read (overlapping
   crops, targeting headers and peripheral text) to test whether the gain is
   about prompts or about coverage.
3. **Merge.** Align reads; add content present in one read only; resolve
   substitutions by the higher per-token log-probability (requires recording
   generation log-probabilities, a T1 change); suppress re-inserting blocks
   already present elsewhere (the duplication in §3).
4. **Outcomes.** Mark accuracy over all reference marks (primary),
   mark-specific error (must not rise), CER, duplication, latency. Two
   decodes roughly double decode time; prompt-lookup speculative decoding
   (`SPEC_DECODE_S1`, Track A) is the intended offset, measured, not assumed.
5. **Text recognition is a separate problem** — the model answering a
   different line than asked (54% of errors) — and needs its own design,
   e.g. transcribe the page, then select the asked span.

Open question for the researcher: this shifts the Typhoon track from
"mark misreading" to "omission", which the evidence supports but the current
objective wording (`RESEARCH_SPEC.md`) does not name explicitly.
