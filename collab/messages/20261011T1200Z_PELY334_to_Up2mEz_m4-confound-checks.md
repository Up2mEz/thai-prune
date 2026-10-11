type: result
subject: M4 confound checks done — forcing explains part of the AUROC, not all; claims withdrawn and wordings softened; Decision Log approval PR #82 open
needs_reply: no
in_reply_to: 20261011T1045Z_Up2mEz_to_PELY334_review-m2-m3-m4-approved.md
refs: PR #82, docs/stage0/MODEL_SURVEY_M4_RESULTS.md, docs/stage0/MODEL_SURVEY_SUMMARY.md, docs/stage0/data/M4_WINDOWS_a9aad7aa31d8.json, scripts/model_survey_m4_confound.py

# M4 confound checks, and the wordings

Thanks for the review. Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`;
exploratory, after the results, no new run.

**Approval PR.** PR #82 records your approval on the four entries (2026-10-10,
10-10b, 10-11, 10-11b), with your wording. It is waiting for you.

**Checks** (M4 results §6; the per-window table is committed, and the script
must reproduce the registered 0.9198 before it writes anything). A token that
is not the teacher-forced argmax is taken as forced. M3 did not record forced
positions, and this proxy also counts fp16 ties (about 0.3% on ordinary text).

| score | AUROC [95%, pages resampled] | within pages only |
|---|---|---|
| `s_mean` (registered) | 0.92 [0.81, 0.98] | 0.88 (6 pages) |
| `s_mean` over unforced tokens | 0.80 [0.57, 0.92] | 0.83 (6) |
| minus forced share alone | 0.76 [0.64, 0.97] | 0.63 (6) |
| `s_mean`, windows with no forced token | 0.92 [0.78, 0.99] (6 pages) | 0.84 (3) |
| minus window length | 0.55 | 0.66 |
| minus distance from latest escape | 0.27 (reversed 0.73, orientation chosen after seeing) | 0.45 |

**Reading.**

- The concern holds in part. Forced tokens sit in 50 of 84 invented windows
  and in 4 of 46 read ones.
- A signal remains without them and within pages, but it rests on 3 to 6
  pages.
- Distance from the escape separates the labels across pages but not within
  them.
- "Wayu knows when it is inventing" and "extends E1 to a second model" are
  withdrawn. §3 and §5.1 now say the result is consistent with E1, not a
  replication. The few-pages caveat is next to the headline.

**Wordings.** M4 §5.2 and the summary now use your wording: the gap sits on
pages where Wayu loops, no decoding remedy tested recovers it, and cause
versus symptom is not separated. The summary's approval line now says M1-M4
are approved by both of us.
