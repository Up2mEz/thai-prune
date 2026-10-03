# E1 — does Typhoon's own confidence locate its mark errors?

**Status: `APPROVED_BY_STANDING_INSTRUCTION`.** The researcher asked on
2026-10-04 for the literature review to be turned into experiments and run
(`LIT_REVIEW_TYPHOON_GAPS_2026-10-04.md`). Written before any E1 output.
Calibration split, Typhoon only, no new generation.

## 1. Why

Several training-free remedies need to know *where* the model is likely
wrong: confidence-gated rescoring of marks (the T2 oracle found ~1.3 points of
headroom), entropy-triggered re-looking (MemVR, ICML 2025), uncertainty-guided
crops (UG-Search). VLM token probabilities are often poorly calibrated
(arXiv 2511.19806). E1 decides whether this family is worth building for
Typhoon's marks, before any of it is built.

## 2. Measurement

Cases: the 356 `greedy` outputs of T5 (identical to T1), both tasks, both
prompts. For each, one teacher-forced forward over prompt + image + the
output re-tokenized, dtype as T1 (fp16, fp32 fallback). Recorded per output
token: log-probability of the token, entropy of the full distribution, the
argmax, and the top-5 ids and log-probabilities.

Guards (reported; E1 is invalid if either fails):

- re-tokenization round-trip: decoding the re-encoded output gives the output
  back;
- greedy consistency: the argmax equals the next output token at ≥ 99% of
  positions overall (fp16 kernels may differ from generation slightly).

## 3. Labels and scores (offline)

- Outputs that reached `max_new_tokens` are excluded (loops).
- Full-page OCR: reference lines are matched to the output as in order-free
  v2 (≥ 8 characters, CER < 0.4, claimed output masked); only lines read at
  CER < 0.2 (the "read" threshold of `attribution`) are labelled, each over
  its own stretch of output. *Amended 2026-10-04 after the 4-case smoke and
  before the full run:* the first version labelled the whole span from the
  first to the last matched line (unmatched lines between them counted as
  inserted marks: 76 of 466 clusters "wrong" on one page), and a loose match
  of a long line across shuffled label fields (`048AEF1B`) marked correct
  marks as errors. The gate is unchanged. Text recognition:
  the reference is aligned reference-anchored to the output; items not
  located under the BQ null threshold are excluded.
- Output **grapheme clusters**: a consonant with its following combining
  marks (upper/lower vowels, tone marks, U+0E47, U+0E4C); any other character
  is its own cluster. A cluster is **mark-bearing** if it, or the reference
  cluster aligned to its base character, carries a mark.
- **Mark error**: the cluster's marks (as an ordered string) differ from the
  aligned reference cluster's, or the cluster's base is unaligned and carries
  a mark. Consonant errors are recorded separately and not used for the gate.
- Scores: `s_min` = −(lowest token log-probability among tokens overlapping
  the cluster); `s_ent` = the highest entropy among those tokens.

## 4. Gate (fixed)

Per cell, over mark-bearing clusters: AUROC of `s_min` for mark error, and
recall of mark errors when the top 5% of mark-bearing clusters by `s_min` are
flagged; 95% page-cluster bootstrap (seed 20261004, 1000 resamples).

- **Pass:** AUROC ≥ 0.75 **and** recall@5% ≥ 0.40 in both Full-page cells.
  Then E1-B (correcting flagged clusters with the model's own top-k
  alternatives) is registered next.
- **Fail:** confidence-triggered remedies are dropped for Typhoon's marks;
  reported as a finding (Typhoon is confidently wrong).
- `s_ent` and Text recognition are reported, not gated.

## 5. Cost

356 forwards, no generation; under 30 minutes on 2×T4 (`--shards 2`). New
test `t6` (infrastructure change): smoke on the secondary account first.

## 6. Result (2026-10-04): PASS

Run `kaggle-thai-marks-t6-7934890c22f6-typhoon-x2` (git `7934890`), 356
cases, 0 failures, 2×T4 (shards 422 s and 442 s), fp16. Guards: greedy
consistency 99.91% of 196,145 tokens; 0 round-trip failures. Excluded: 11
looping outputs, 12 Text recognition items not located. Summary:
`runs/kaggle/kaggle-thai-marks-t6-7934890c22f6-typhoon-x2/fetched/e1_summary.json`.

| cell | mark-bearing clusters | mark errors | AUROC `s_min` (95% CI) | recall @ 5% flagged (95% CI) | AUROC `s_ent` |
|---|---|---|---|---|---|
| Full-page BQ | 12,732 | 126 | **0.939** (0.911–0.970) | **0.683** (0.520–0.868) | 0.940 |
| Full-page TC | 12,423 | 106 | **0.947** (0.920–0.972) | **0.736** (0.617–0.868) | 0.949 |
| Text rec. BQ | 2,466 | 106 | 0.843 (0.747–0.915) | 0.472 (0.321–0.613) | 0.846 |
| Text rec. TC | 2,756 | 77 | 0.841 (0.744–0.922) | 0.403 (0.212–0.590) | 0.845 |

Both Full-page cells pass §4 with margin: Typhoon's lowest-probability token
locates its mark errors. Raw outputs of flagged clusters were read: the
errors are real misreads (`สิริมดี → สิริมติ`, `เบ้าตา → เป่าตา`,
`ลี้ภัย → สี่ภัย`, `หรั่ง → หรัง`); some "errors" are reference spellings
(`เปน` for `เป็น`). Flagging 5% of clusters yields 13.5% errors (BQ) against
a 1.0% base rate. Half the errors also change a consonant (70 / 126 BQ), and
the top-5 alternatives of the flagged token contain a mark-only variant for
18 / 86 (BQ) and 28 / 78 (TC) flagged errors. A correction must therefore
bring evidence the model's top-1 lacks: 86% of flagged clusters are correct.
Next: E1-B (registered separately).
