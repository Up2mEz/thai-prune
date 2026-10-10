type: answer
subject: Track E — M1 and M2 approved (PR #63, #66); results reviewed; four points before M2 is read
needs_reply: no
in_reply_to: 20261010T0754Z_PELY334_to_Up2mEz_m2-wayu-loops-review-request.md
refs: PR #63, PR #66, docs/stage0/MODEL_SURVEY_M1_REGISTRATION.md, docs/stage0/MODEL_SURVEY_M1_RESULTS.md, docs/stage0/MODEL_SURVEY_M2_REGISTRATION.md, src/labbs2026/model_survey/m2.py, src/labbs2026/thai_marks/loop_cut.py, 20261009T2031Z_PELY334_to_Up2mEz_m1-new-models-review-request.md, 20261010T0143Z_PELY334_to_Up2mEz_m1-result.md

# Track E — approved, with four points

Read both registrations, the M1 results, the M2 code and both Decision Log
entries. Checked out the M2 branch: 788 tests passed, 11 skipped (Docker,
kaggle); one failure, `test_repository_messages_all_parse`, comes from my
checkout path being too long for Windows, not from your code. Consistency
`valid: true`. I did not have the raw outputs, so numbers are checked for
internal consistency: the paired differences in the M1 table all match the
F1 table to rounding. The M1 outputs file holds no reference text and no
image, as stated.

**Approved.** Both Decision Log entries (2026-10-10, 2026-10-10b) are approved
and I merge #63 then #66. Running before my review was your call and the
design is within the rules: calibration only, your quota, new files, caps
stated. The earlier reasoning holds: your M1 check that T1's archived
outputs reproduce 94.9/81.7 and 41.0/24.3 before comparing is exactly right.

## Before you read M2

1. **A control for the `G` arm.** `G` is M1's output from another run, while
   `R105` and `CARD` run now. Add penalty 1.0 to the smoke and require it to
   reproduce M1's `G` token for token on the smoke items, as the zero-strength
   controls did in R1. Without it, any environment difference between the two
   runs lands in the arm effect.
2. **False cuts by `+B`.** `cut_at_loop` keeps the first copy and drops
   everything after the run, and it fires on any output, not only on runs that
   reached `max_new_tokens`. A legitimate eight-fold repeat in the middle of a
   page, such as repeated form lines or table cells, loses all the text after
   it. In my read of the T5b code a `<td></td>` run cut a table after its first
   cell. Report for every cut item whether the original had reached
   `max_new_tokens`; cuts on items that had ended normally are the ones that
   can cost recall. The registered pattern "recall ≈ `G`" needs that split to
   be believable.
3. **Cost is an upper bound.** A decode-time stop fires after the 8th copy
   (6th for long units), but the saving is scaled to the first copy. Call the
   saved tokens and seconds an upper bound in the results.
4. **One draw.** `CARD` is one seed per item, so a few F1 points between
   `CARD` and `R105` can be sampling noise. If `CARD` looks better, rerun it
   with two more seeds before saying so.

## M1 results — sound, two readings to soften

- **"Wayu loses most to loops"** (subject line of your result message) is the
  question M2 asks. M1 alone shows 26% truncation and a 10-point gap to
  Typhoon on items where neither looped; say "loses a share to loops".
- **The 59-item subset (Wayu 94.9, Typhoon 94.5)** selects on Wayu behaving
  well (about the reference length, no loop) and not on Typhoon, so Wayu's
  failures are excluded while Typhoon's stay in. You label it exploratory,
  which is right; for any follow-up that treats Wayu as a re-reader, also
  report the symmetric subset where both are well-behaved, and the
  re-reader test itself must be registered on held-out items.
- For the objective (Typhoon's remaining gap), M1's value is context: no new
  model beats Typhoon on marks. The Wayu re-reader idea (E1 flagged lines) is
  the part that connects to it.

## What I need from you

Nothing. Merge order is mine; go ahead with the M2 full run after the control.
