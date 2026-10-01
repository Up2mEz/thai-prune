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

## 2d. Correction 2026-10-02 — a third of "missing" marks were read, in another order

§2b counted a whole-line deletion as `line_reordered` only if the line
appears **verbatim** elsewhere in the output. Reading the raw outputs of the
pages that lose most showed lines that are present but not verbatim: read in
a different column order, with their line break joined to the next line, or
with a character wrong (`52A433B2`: two paragraphs, 96 marks, both in the
output after the next section; `9BBB9DB3`: the sidebar read before the boxes
below the article). `attribution.py` now has `approximate_reorder`: a
whole-line deletion of 8+ characters is `line_reordered_approx` if some
stretch of the output matches the whole line below 20% CER. Lines matched
against *other* pages' outputs reach a median 5th percentile of 0.63–0.74,
so 0.2 is far from chance; shorter lines (axis ticks, page numbers) match
anywhere by chance and are never credited. The §2b rule stays the default,
so the 2026-10-01 numbers reproduce. Script `scripts/thai_marks_attribution.py`,
output `runs/kaggle/kaggle-thai-marks-t1-t2-a44199c29759/fetched/attribution_v2.json`.

Typhoon, Full-page OCR, as a share of **all** 16,266 reference marks:

| cause | `BENCHMARK_QUESTION` | `TYPHOON_CARD` |
|---|---|---|
| all wrong | 6.2% | 7.1% |
| read in another order, verbatim | 0.8% | 0.5% |
| read in another order, approximate (new) | 1.4% | 1.1% |
| **whole line absent** | **1.7%** (was 3.1%) | **2.3%** (was 3.3%) |
| span missing inside a kept line | 0.7% | 0.8% |
| misread, base right | 0.4% | 0.6% |
| misread with base | 1.1% | 1.8% |

Base is barely affected (`line_reordered_approx` 0.3% of marks), so the
RQ-C contrast of §2b stands and is sharper: Typhoon's mark loss is about
4% of marks once reading order is set aside, base's about 41%.

**What the absent lines are** (BQ: 48 lines with marks, 281 marks, on 14
pages; read from the page images, descriptive, not a statistic):

- text inside infographics and charts: legend entries, axis units, panel
  captions (`908E11C8`, 14 lines; `8F33EBB9`, 6) — Typhoon wrote an image
  placeholder there;
- an advertisement inset in a newspaper page (`AF432B6A`, 10 lines);
- titles, mastheads and form fields at the top of the page (`8F33EBB9`,
  `9BBB9DB3`, `048AEF1B`, `6BA97DBE`, `E666F212`, `E6803A95`, `F1D97B10`);
- two body paragraphs, which hold 96 of the 281 marks (`6BA97DBE` line 4, a
  newspaper lead; `8F33EBB9` line 60, under a chart).

**Consequences.**

1. The reference-anchored metric charges reading order as loss. For
   full pages with several columns or panels, an order-free measure is
   needed alongside it (per reference line: best-matching stretch of the
   output; with a precision guard against surplus text) before any coverage
   remedy is scored. Proposing one is a scoring change and needs the
   researcher's approval.
2. Most of what Typhoon truly omits is text inside graphics, inset
   advertising and page furniture. Whether that is in scope is a task
   definition question: ThaiOCRBench references include it, Typhoon's own
   prompt contract (`TYPHOON_CARD`) asks for figures to be described, not
   transcribed.
3. Typhoon's mark headroom on full pages is small: 1.7% whole lines absent,
   0.7% spans, 1.5% misreads.

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
