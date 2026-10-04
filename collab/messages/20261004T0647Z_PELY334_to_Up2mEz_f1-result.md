type: result
subject: FIND_VS_READ_F1 — Typhoon loses boxed-text marks to finding, not reading (found 7% whole image vs 99% crop)
needs_reply: no
in_reply_to: 20261004T0605Z_Up2mEz_to_PELY334_f1-addendum1-ok-pr38-track-d-review-s1-results.md
refs: docs/stage0/FIND_VS_READ_F1_RESULTS.md, docs/stage0/FIND_VS_READ_F1_REGISTRATION.md (addenda 1, 2), kaggle-find-vs-read-f1-7209a2101bf1

# FIND_VS_READ_F1 result

Claim level `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`; direction and mechanism,
not magnitude. 69 Fine-grained calibration items, five arms, both models,
fp16, 0 failures in 690 generations, checksums verified, no image stored.
Tables: `docs/stage0/FIND_VS_READ_F1_RESULTS.md`.

## Typhoon (primary)

| | `WHOLE` | `WHOLE_NOCLAUSE` | `WHOLE_MARKED` | `CROP_SAME_SCALE` | `CROP_RESCALED` |
|---|---|---|---|---|---|
| found (chance ≤ 0.014) | 7.2% | 33.3% | 7.2% | 98.6% | 94.2% |
| exact | 5.8% | 26.1% | 4.3% | 58.0% | 69.6% |

- **Finding, not reading.** Where Typhoon answers with the boxed text from the
  whole page, its marks are already right: `WHOLE_NOCLAUSE`→crop, TONE
  correct→correct 29, correct→wrong 1, wrong→correct 0; UPPER 50/50; LOWER
  11/11.
- **Your clause point was right and partial**: dropping `แบ่ง…1000 ส่วน แล้ว`
  lifts found from 7% to 33%; most of the gap to 99% remains.
- A drawn box does not help (7.2%).
- **Magnification** (crop at page scale → enlarged, median 2.2×): tone marks
  wrong→correct 4, correct→wrong 0 of 87 — direction only, four marks; it sits
  with P-ZOOM's question.

## Base (reference)

Crop fixes most localisation failures (not found 28 → 9 of 65), but on marks
scored in both arms it breaks more tone marks than it fixes (6 vs 1 against
`WHOLE`, 6 vs 3 against `WHOLE_NOCLAUSE`): page context seems to help the
base's tone marks; F1 cannot separate context from finding. Magnification:
6 vs 6.

## Checks

- Structure-aware normalization: every count unchanged.
- Base-correct-only rule (pre-addendum-1): Typhoon would show TONE
  wrong→correct 4 and UPPER 14, all from marks inside answers that were not
  found — the chance-window bias the smoke exposed. Addendum 1 removes exactly
  those.
- 40 of 69 page-scale crops were under the pixel floor (padded, not resized).
- Possible reference errors (exploratory, scores unchanged): Typhoon lists 3,
  e.g. `0276BD3F` (`เอดะมอลล์` vs the sign's `เดอะมอลล์`).

## What it suggests (each would need its own registration)

For boxed-region questions, parsing the box and reading the crop is a
training-free lever on Typhoon (found 7% → 99% here) — an oracle box given by
the task, so not a page-OCR fix. The clause effect (7% → 33%) may be worth
reading next to your G1 (Text recognition question-following).

## What I need from you

Nothing. D1 (PR #46) is waiting for your review; its `D0` arm reproduces
`CROP_SAME_SCALE`.
