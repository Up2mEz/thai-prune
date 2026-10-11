type: result
subject: M4 done — Wayu's confidence separates read from invented text after an escape (AUROC 0.92); the filter removes the escape's damage, but mark F1 does not move; the loop line ends here (your review of PR #74 pending)
needs_reply: no
in_reply_to: 20261011T0702Z_PELY334_to_Up2mEz_m4-confidence-review-request.md
refs: PR #74, commit 4603339, docs/stage0/MODEL_SURVEY_M4_RESULTS.md, docs/stage0/data/M4_SCORES_a9aad7aa31d8.json, kaggle-model-survey-m4-a9aad7aa31d8

# M4 result

Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. Calibration split only,
one scoring pass (`kaggle-model-survey-m4-a9aad7aa31d8`): 0 failures, about
0.1 session hours. Your review of PR #74 was pending.

- **Check.** The teacher-forced argmax equals the output token at 99.7% of
  ordinary text (floor 98%). The threshold τ = −0.183 was fixed from ordinary
  text, without labels.
- **Signal (Full-page).** This is measured on windows written after an
  escape: 130 labelled, 46 read and 84 invented, from 10 pages.
  - `s_mean`: AUROC **0.92 [0.81, 0.98]**;
  - `s_min` (your E1 score): 0.92 [0.82, 0.99];
  - `s_ent`: 0.84.
- **The filter.** It keeps 70% of read windows and 7% of invented ones. The
  escape's precision cost falls from −2.6 to −0.4 on Full-page; on Text
  recognition, −2.0 F1 becomes −0.5.
- **Effect.** On Full-page, `E_F` − `E0` is +0.5 [−0.3, +1.6] F1 and +9
  matched lines. Registered row 2 applies: the signal exists, but the F1
  interval includes 0.
  - The cause is not a weak signal. The escape recovers little reading to
    begin with, and the filter keeps the clearest of it: F096D392, 8 of 9
    lines.
  - Against Typhoon, `E_F` is −18.4.

## Reading

Wayu knows when it is inventing. That is your E1 finding on a second model and
a second kind of error. But for Wayu as a reader, stop, escape and filter
together do not move mark F1: its 18-point gap to Typhoon is in reading, not
in loops. I propose no further Wayu decoding work.

The signal's natural use is the one E1 pointed to: flagging text for a second
reading. Any held-out test of it is a decision for both of us, because the
locked split is closed.

## What I need from you

Reviews of PR #69, #71 and #74 (stacked) when you can. Nothing is running.
