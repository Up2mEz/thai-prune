# MODEL_SURVEY W3 — registration: T2 (prior vs image) on Pathumma and Qwen3-VL-4B

**Status: `APPROVED` by PELY334 in session on 2026-10-12** ("ทำทุกอันเลย", "do
all of them"). Written before any W3 output existed. Up2mEz's work split
(collab `20261011T1315Z_Up2mEz_to_PELY334_paper-prep-work-split.md`, W3).
Calibration only, PELY334's quota, own namespace; under the standing
delegation (DECISION_LOG 2026-10-11c) Up2mEz reviews afterwards. Claim level:
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. Parameters:
`configs/model_survey/w3_t2.yaml`.

**Question.** T2 found that, given the correct preceding text, both T1 models
choose the right mark at sampled sites about 98–100% of the time. They do so
with the image and almost as often without it. Greedy reading is far below
that, and most of the gap is text the model never produced
(`THAI_MARKS_T1_T2_RESULTS.md` §1). This is the evidence behind claim (2),
"marks are lost by not reading, not by misreading". It rests on one pair:
Typhoon and its base. W3 asks whether the same holds for:

- **Pathumma Vision 3.0.0-Re**, a second Thai OCR fine-tune of the same base;
- **Qwen3-VL-4B-Instruct**, a larger general model.

## 1. Fixed inputs: T2's, unchanged

The config copies `configs/thai_marks/t1_t2.yaml` without editing it, and a
test checks the copy field by field. Only the models change.

- **Items.** T2's calibration items (seed 20260927); T2's sites
  (`orthography.find_sites` + `sample_sites`, seeded by item id).
- **Prompt.** `TYPHOON_CARD`, the same file and SHA-256 as T2.
- **Scoring.** `runtime.score_item`:
  - in-context tokenization;
  - summed log-probability of each legal variant, with and without the image;
  - window 8 characters;
  - fp32;
  - consistency guard 0.001 nats, which stops the process if exceeded.
- **Models.**
  - Pathumma `@08bb11dc` (M5's).
  - Qwen3-VL-4B `@ebb281ec` (M1's). In fp32 it needs 17.7 GB, more than
    one T4, so it is loaded over both T4s (`device_map="auto"`) in one
    process. Placement changes no arithmetic, and the guard still applies.
- **Code.** `model_survey.remote_w3` runs T2's item loop and imports
  `thai_marks` read-only. `thai_marks.remote` accepts only the roles `base`
  and `typhoon`, and that file is not this track's to edit.
  - Records have T2's format.
  - Launcher: `scripts/model_survey_w3_kaggle.py --run w3a` (Pathumma) and
    `--run w3b` (Qwen3-VL-4B).
- **Greedy column.** Each model's archived `BENCHMARK_QUESTION` outputs:
  Pathumma from M5, Qwen3-VL-4B from M1. Neither was run with
  `TYPHOON_CARD`, and T2's results use BQ greedy for the base for the same
  reason. Scored with scoring v2's located rule, as in
  `scripts/thai_marks_score_v2.py`.

## 2. Outcomes

- **Primary.** Per model, task and mark kind (tone, upper, lower): the oracle
  (with image) and prior (without) accuracy at the sites, item bootstrap as
  in T2 (`thai_marks.analysis.summarize_t2_v2`).
- **Secondary.**
  - image gain (oracle − prior);
  - contrastive re-scoring at λ = 0.5 and 1.0;
  - greedy accuracy at the sites, overall and restricted to sites inside text
    the greedy read produced;
  - the summed vs per-token-mean convention check.

## 3. What each pattern would mean, stated in advance

| pattern | reading |
|---|---|
| oracle ≥ 97% on tone for a model, and greedy at produced sites close to it | given the text, the model reads marks; its mark loss is mostly not-reading. Claim (2) extends to it on teacher-forced evidence |
| oracle ≥ 97% but greedy at produced sites far below it | the model's misreads happen in generation, not in its mark knowledge; claim (2) holds only partly for it |
| oracle clearly below T2's models (< 95% on tone) | the model does not know the marks well even with correct context; a misreading component is real for it |
| image gain near 0 or negative (as the base, −0.8) | the prior carries the mark choice in context; an image-contrastive remedy would cost marks (as R1 found) |
| image gain clearly positive (as Typhoon, +0.9) | the image adds evidence at mark sites |
| contrastive re-scoring below the oracle at both λ | same as T2; R1's §6.4 reading extends to the model |

"Close to" and "far below" are read with the intervals, and nothing here is
a gate.

## 4. Budget, smoke, stopping

- **No measured T2 time in this account.** T2 ran on Up2mEz's account.
- **Smoke first: `--smoke 2` on each run.** It gives:
  - seconds per item, which the deadlines below may be revised against in an
    addendum written before the full run;
  - that the guard holds in fp32;
  - for W3b, that the two-GPU placement loads and scores.
- **Deadlines.**
  - Pathumma: 4.0 h per shard.
  - Qwen3-VL-4B: 8.0 h as one unit, inside Kaggle's 12-hour session limit.
  - No item starts later. Items not run are listed, and the results report
    the items scored.
- **Cap: 24 T4-hours** over both runs: W3a at most 2 × 4, and W3b at most
  2 × 8, because it holds both GPUs. That is at most 12 Kaggle session-hours
  in all.

## 5. Not in scope

Typhoon and base (T2 has them), any generation, any remedy, the locked split,
and other models.
