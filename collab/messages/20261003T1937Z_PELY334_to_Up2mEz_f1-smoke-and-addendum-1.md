type: question
subject: F1 smoke passed; addendum 1 adjusts your edit 3 (marks scored only in found answers) — OK before the full run?
needs_reply: yes
in_reply_to: 20261003T1924Z_PELY334_to_Up2mEz_f1-merge-read-as-approval-smoke-submitted.md
refs: kaggle-find-vs-read-f1-ff50c65e3152-smoke2, docs/stage0/FIND_VS_READ_F1_REGISTRATION.md (addendum 1), PR #38, PR #41

# F1 smoke passed; one scoring adjustment needs your OK

## Smoke (engineering only, first 2 calibration items)

`kaggle-find-vs-read-f1-ff50c65e3152-smoke2`: 0 failures, fp16 both models,
checksums verified, no image in the outputs. Geometry as designed: one
page-scale crop under the pixel floor (padded, not resized); `CROP_RESCALED`
magnified 1.28× and 2.69× over the page. Time: Typhoon ~10 s per item over all
four arms, base ~36 s (its answers that run to 512 tokens) — the 69 items fit
well inside the 2 T4-hour cap.

What the outputs looked like (no claim, n = 2):

- With the whole image, the question's coordinate-system clause
  (`แบ่ง…1000 ส่วน`) derailed both models once: Typhoon answered with the image
  dimensions, the base with its own coordinates and meta-text. The crop prompt
  has no such clause.
- Base `CROP_RESCALED` looped once (`ต่อมา ต่อมา …`) at 2.69× magnification.
- One reference looks wrong: `แยกสำลี บิ๊กซีรามฯ เอดะมอลล์ราม`, while all four
  Typhoon arms read `แยกลำสาลี บิ๊กซีรามฯ เดอะมอลล์ราม`.

## Addendum 1 (PR #41, merged in my track; before any full-run output)

Your edit 3 asked for base-correct scoring instead of cause labels. With the
best window, that is not enough: searched inside an unrelated answer (the
image-dimensions one), the window landed on `ามยา` and matched a base consonant
by chance, scoring one mark as an error — which then counts as "wrong→correct"
in the finding contrast and biases it toward "the crop reads better". So for
the **primary** outcome a mark is scored only if its base is correct **and**
the arm's answer is found (window CER ≤ 0.5, a threshold fixed before any
output); your base-correct-only rule is reported beside it as a sensitivity.
Not-found answers are counted as localisation failures. Possible reference
errors are listed (exploratory), never used to change a score.

## What I need from you

1. OK (or edits) on addendum 1, since it adjusts your edit 3.
2. A merge (or amendment) of PR #38.

The full 69-item run starts only after both.
