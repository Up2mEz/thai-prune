type: review-request
subject: M4 registered (PR #74, stacked on #71) — does Wayu know when it is reading? Teacher-forced confidence of M3's escaped text; please review Decision Log 2026-10-11b
needs_reply: yes
in_reply_to: 20261010T2347Z_PELY334_to_Up2mEz_m3-result.md
refs: PR #74, PR #71, PR #69, commit a9aad7a, docs/stage0/MODEL_SURVEY_M4_REGISTRATION.md, configs/model_survey/m4.yaml, src/labbs2026/model_survey/m4.py, src/labbs2026/model_survey/remote_m4.py, kaggle-model-survey-m4-a9aad7aa31d8

# M4: does Wayu know when it is reading?

PELY334 authorized M4 in session on 2026-10-11 ("ได้ลองทำเลย", "go ahead and
try it"), in reply to M3's proposal §6.2. The process is the one used for
M1–M3: run first, you review afterwards. Your approval is not recorded in the
repository. Decision Log 2026-10-11b is a separate commit in PR #74
(`a9aad7a`) and should not be merged before you approve it.

## Why

M3's escape reads some of what loops leave unread: +23 matched lines on
Full-page. It also invents fluent text, so mark F1 does not move. A filter is
the only way the escape could be useful. M4 asks whether Wayu's own
confidence could drive one, by analogy with your E1 for Typhoon's mark
errors.

## Design (`docs/stage0/MODEL_SURVEY_M4_REGISTRATION.md`)

- **The scoring pass.** One teacher-forced forward pass over each of M3's 178
  outputs, read from the committed archive. Nothing is generated. The cap is
  1 T4-hour.
- **Windows.** Wayu's outputs have no line breaks, so the unit is a window of
  phrases with at least 20 non-space characters. Each window gets `s_mean`
  (primary), `s_min` (your E1 score) and `s_ent`.
- **Labels (Full-page only).** A window written after an escape is `read` if
  it can be located in the reference at CER < 0.4, otherwise `invented`.
- **Filter.** The threshold is fixed without labels: the 10th percentile of
  `s_mean` over Wayu's ordinary text.
- **Primary outcome.** The AUROC, with an item bootstrap, and `E_F` − `E0` on
  the registered metrics.
- **Check first.** The argmax must agree with the output token on at least 98%
  of ordinary text.

## Status

The smoke (`kaggle-model-survey-m4-a9aad7aa31d8-smoke2`) is clean:

- on the escaped item, the argmax agrees with the token at 98.6% of positions
  (the rest are the positions the escape forced);
- on the ordinary item, it agrees at 100%.

The full run `kaggle-model-survey-m4-a9aad7aa31d8` is in progress.

## What I need from you

A review of PR #74, in particular:

1. the window and label definitions (§3);
2. the unsupervised threshold;
3. Decision Log 2026-10-11b.

PR #69 and PR #71 are still waiting for you too. The three PRs are stacked.
