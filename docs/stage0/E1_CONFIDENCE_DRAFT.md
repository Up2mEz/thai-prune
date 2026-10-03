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
  v2 (≥ 8 characters, CER < 0.4, claimed output masked). Text recognition:
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
