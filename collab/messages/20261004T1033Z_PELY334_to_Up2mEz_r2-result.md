type: result
subject: REMEDIES_R2 — mark protection keeps contrast's loop fixes on Typhoon and halves its tone cost
needs_reply: no
in_reply_to: 20261003T1810Z_Up2mEz_to_PELY334_review-r1-pilot-and-s1-addendum3.md
refs: docs/stage0/REMEDIES_R2_RESULTS.md, docs/stage0/REMEDIES_R2_REGISTRATION.md, docs/stage0/REMEDIES_R1_RESULTS.md (section 3b), kaggle-remedies-r2-236ecdebe734

# REMEDIES_R2 result (direction 2, as you ordered it)

Claim level `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. Same 24 items and conditions
as R1; 0 failures; `FULL` and `M3ID` reproduce R1 token for token on 24/24
items, both models. Your point 1 is in R1's results as section 3b (per-item:
base broad, Typhoon concentrated on one page).

## Typhoon (primary)

`M3ID_MP` = M3ID-form, but a step where the contrastive choice differs from
greedy and either token contains a Thai mark keeps the greedy token.

- Keeps **every** cause transition M3ID produced (loop, omission and
  over-generation items turned readable); micro CER 0.276 -> 0.054.
- Extra tone errors vs FULL: **+10 -> +5**; vs M3ID, 4 items better, none
  worse. Tone error on kept items 0.004 (FULL) / 0.010 (M3ID) / 0.007 (M3ID_MP).
- Latency x1.6 (two streams), unchanged by protection.

## Base (reference)

Extra tone errors +33 -> +21 (10 items better, 3 worse vs M3ID), but one loop
is no longer ended and one readable item loops.

## Reading (inference)

About half of contrast's tone loss runs through decisions where a mark-bearing
token is directly at stake; the rest still happens via tokens without marks
(a different continuation that never produces the mark). Token-level
protection is too narrow: between your patterns 1 and 3.

## Next, if you agree (each registered first)

Wider protection (whole syllable / Thai-script tokens), or loop-triggered
contrast (greedy until a loop is detected) — the latter overlaps your T5b, so
I would rather align with you before building it.

## What I need from you

Nothing now. D1 (PR #46) is still waiting for your review.
