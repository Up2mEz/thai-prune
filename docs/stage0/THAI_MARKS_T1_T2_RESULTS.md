# T1 and T2 — results and the registered routing

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`** — calibration split
(178 items: 69 Full-page OCR, 109 Text recognition), both pinned models,
Kaggle T4. The locked split is unopened.

- T1: run `kaggle-thai-marks-t1-t2-a44199c29759`, scored with scoring v2
  (`THAI_MARKS_T1_SCORING_V2.md`).
- T2: run `kaggle-thai-marks-t2-09cfb2da2307` (fp32, in-context tokenization,
  178/178 both models, no failures, guard ≤ 0.00012 nats, checksums verified).
  It supersedes the fp16 run (tone sites invalid, base incomplete) and the
  2026-10-01 fp32 run (tone sites invalid: standalone window tokenization).
- Analysis: `runs/kaggle/kaggle-thai-marks-t2-09cfb2da2307/fetched/analysis_v2.json`.

## 1. T2 at the registered sites

Oracle = the legal variant with the highest log-probability with the image;
prior = the same without it; greedy = the T1 output at that site (scoring v2,
chance-located). Registered summed convention.

| model · task | mark | oracle | prior | greedy `BQ` | greedy `TC` (registered) |
|---|---|---|---|---|---|
| typhoon · Full-page | tone | 99.7% | 98.8% | 94.2% | 92.2% |
| | upper | 99.8% | 98.4% | 93.6% | 90.3% |
| | lower | 99.8% | 98.5% | 93.4% | 90.2% |
| typhoon · Text rec. | tone | 98.8% | 97.3% | 82.7% | 95.6% |
| base · Full-page | tone | 98.1% | 98.9% | 62.8% | 18.4%¹ |
| | upper | 98.4% | 98.5% | 63.1% | 16.8%¹ |
| base · Text rec. | tone | 96.6% | 97.3% | 71.9% | 18.9%¹ |

¹ Base fails `TYPHOON_CARD`'s format contract (scoring doc §1); its TC greedy
measures format, not reading. Its `BENCHMARK_QUESTION` greedy is used instead.

**Headroom is not where it looks.** Restricted to sites inside text the greedy
read actually produced (`BENCHMARK_QUESTION`): Typhoon Full-page 98.5% greedy
vs 99.8% oracle (95% of sites), Text recognition 96.1% vs 99.5% (84%); base
Full-page 81.4% vs 98.9% (76%), Text recognition 88.7% vs 98.5% (80%). Most
of Typhoon's apparent headroom is text it skipped, which re-scoring variants
cannot recover.

**Image-contrastive re-scoring hurts.** `score_image − λ·score_no_image` at
λ = 0.5: Typhoon Full-page tone 97.3% (oracle 99.7%); at λ = 1.0, 42.3%. Base
at 0.5: 84.7% (oracle 98.1%). The same direction for every mark and task.

**Scoring convention.** Summed and per-token-mean scoring agree (tone 99.4% /
99.2% Typhoon, 97.5% / 98.0% base). The first-divergent-token convention is
lower (86.9% / 83.1%) because it compares tokens that cover different
lengths of text; it is not a valid stand-alone score.

**Real-word share** of mark errors (T1, `BENCHMARK_QUESTION`): Typhoon 18–29%,
base 17–35% — most misread marks land on non-words.

## 2. The registered routing (`T1_T2_CONTINGENT_REMEDY_PLAN.md` §2)

| quantity | Typhoon | base |
|---|---|---|
| headroom, registered sites | 5–8 pts, but 1.3 pts (Full-page) inside text produced | 35 pts; 17.5 pts inside text produced |
| image_gain (oracle − prior) | +0.9 to +1.5 pts (tone, Full-page / Text) | −0.8 to −0.7 pts (tone) |
| oracle_accuracy | ≥ 98.8% | ≥ 96.6% |
| real_word_share | low (18–29%) | low (17–35%) |

- **Typhoon → "oracle high, both do well" at the sites it reads.** No mark-level
  remedy is indicated there; the claim narrows to the sites still wrong, which
  are mostly in skipped lines (`TYPHOON_FAILURE_PROFILE.md` §2b). The tree's
  next step for those is outside T2's reach: T3 (line-skip diagnostic).
- **Base → "headroom large, image_gain small, prior ≈ oracle".** The plan says
  §3.A is worth building only with the plain statement that any gain would come
  from the language prior, not the image. Two cautions the plan did not have:
  the oracle is given the *correct* preceding text, which base's own garbled
  output does not supply (its errors are mostly whole-word misreadings), so the
  realisable share of the 17.5 points is unknown; and the image-contrastive form
  of §3.A lowers accuracy here.
- **Cross-cutting.** Low real-word share is not the prior-dominance signature
  of §3.C. **RQ-C is not supported** by this measure: Typhoon's image_gain is
  higher, not lower, than the base's; the "prior override is worse in OCR
  specialists" expectation does not replicate here, reported as a finding.

## 3. What this means for RQ-A (pilot level)

Given the correct preceding text, both models pick the right tone or vowel
98–99.8% of the time with the image and almost as often without it: at the
mark itself, neither missing visual evidence nor a prior overriding it is the
main source of error. Typhoon's errors are upstream (skipped lines); base's are
upstream too (misread words, so its own context is wrong). This is an
inference from teacher-forced scoring; it is not shown for free generation.

## 4. Withdrawn earlier figures

All T2 tone-mark oracle/prior figures before this run (fp16 run and
2026-10-01 fp32 run): standalone window tokenization. The 2026-09-28 R-FUSE
exploratory gain: reference-side metric artefact.
