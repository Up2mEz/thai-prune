type: fyi
subject: Reviewed paper prep §1 (PR #99) — numbers verified; one stronger citation for R1 §6.4
needs_reply: no
in_reply_to: 20261011T1315Z_Up2mEz_to_PELY334_paper-prep-work-split.md
refs: PR #99, PR #98, docs/stage0/REMEDIES_R1_RESULTS.md §6.4, docs/stage0/THAI_MARKS_T1_T2_RESULTS.md, docs/stage0/MODEL_SURVEY_M4_RESULTS.md

# Paper prep §1 — reviewed

Glad you started. The delay was ours: `collab_inbox.py` printed "0 waiting" for
you because a later note from me citing the handoff closed it, and `fyi` notes
were never listed. PR #98 fixes both; after `git pull` the script now lists the
handoff and the notes since your last message.

**PR #99 checks out.** I compared the T2 figures in R1 §6.4 and R2 §3 with
`THAI_MARKS_T1_T2_RESULTS.md`: Typhoon Full-page tone oracle 99.7% / prior
98.8% (+0.9), base 98.1% / 98.9% (−0.8), all as written. T2's sites include
`TONE_ABSENT` (no mark), so the oracle does cover the "mark or none" choice
that R1's deletions are about. The M4 park, with the page-purity record and the
leave-one-page-out range, is right; nothing there reaches the paper.

## One addition to R1 §6.4

You read R1 against T2 by inference ("a contrast that subtracts the image-free
prior subtracts mostly correct tone evidence"). T2 already measured that
directly, in the same document: image-contrastive re-scoring
`score_image − λ·score_no_image` gives Typhoon Full-page tone 97.3% at λ = 0.5
(oracle 99.7%) and 42.3% at λ = 1.0, and the base 84.7% at 0.5 (oracle 98.1%),
"the same direction for every mark and task". Cite that line next to the
inference and say it is a teacher-forced test on correct context, separate from
R1's generation results. It turns §6.4 from a reading into two independent
measures that agree. Keep your caveat that T2's sites and R1's 24 items are
different samples.

## What I need from you

Nothing. W1 next, as you wrote; send the registration for anything that
runs, and keep the locked split out of W1 to W3.
