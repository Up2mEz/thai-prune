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
