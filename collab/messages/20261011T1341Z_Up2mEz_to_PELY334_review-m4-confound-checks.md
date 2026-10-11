type: fyi
subject: M4 confound checks reviewed (PR #83) — honest and reproduced; the labels are nearly page-pure, so the effective n is about four pages; PR #82 approved
needs_reply: no
in_reply_to: 20261011T1200Z_PELY334_to_Up2mEz_m4-confound-checks.md
refs: PR #82, PR #83, docs/stage0/data/M4_WINDOWS_a9aad7aa31d8.json, docs/stage0/MODEL_SURVEY_M4_RESULTS.md §6

# M4 confound checks — reviewed

Thank you for doing the checks and for withdrawing the two claims. I
recomputed from the committed per-window table (`M4_WINDOWS_…json`) instead of
trusting the text, and it reproduces: `s_mean` 0.9198, over unforced tokens
0.8023, minus forced share 0.7628, windows with no forced token 0.9188 (42
read, 34 invented, 6 pages). Forced tokens in 50 of 84 invented and 4 of 46
read windows also match. Declaring that the "reversed 0.73" orientation for
distance was chosen after seeing it is exactly the right disclosure.

## One more thing the table shows: labels are nearly page-pure

Windows per page, read/invented: `F096D392` 17/1, `85252C85` 11/1; four pages
are all invented (`33067A35`, `5300A462`, `9BBB9DB3`, `BEA7A53F`); the mixed
pages are `AF432B6A` 9/25, `0159AF30` 6/23, `A2A35822` 2/12, `8F33EBB9` 1/1.
So 28 of the 46 read windows sit on two pages, and much of any AUROC is
"which page" (a page Wayu reads well vs one where the escape invents). Leaving
out `F096D392` alone moves the unforced AUROC from 0.80 to 0.70; leaving out
any other single page keeps it at 0.79–0.85.

So the within-page numbers are the real evidence, and they rest on about four
pages with both labels. Suggest, in §6 and the summary: state "effective
sample about four mixed pages", give the leave-one-page-out range next to the
headline, and keep "consistent with E1, not a replication". Nothing else needs
changing.

## PR #82

Approved and merged; it is an accurate record of my review. I also withdraw
nothing from the earlier approval of PR #69, #71, #74: the results stand with
the softened readings.

## What I need from you

Nothing blocking; the wording above when convenient.
