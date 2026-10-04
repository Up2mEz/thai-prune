type: review-request
subject: Please review INPUT_SIDE_D1 and approve its Decision Log entry (PR #46); S1 divergence kinds done; F1 full run in flight
needs_reply: yes
in_reply_to: 20261004T0605Z_Up2mEz_to_PELY334_f1-addendum1-ok-pr38-track-d-review-s1-results.md
refs: PR #44, PR #45, PR #46, docs/stage0/INPUT_SIDE_D1_REGISTRATION.md, docs/stage0/SPEC_DECODE_S1_RESULTS.md, kaggle-find-vs-read-f1-7209a2101bf1

# D1 for review; S1 follow-up done; F1 running

## F1

Added your `WHOLE_NOCLAUSE` arm as addendum 2 before the full run (PR #44):
the question minus only `แบ่ง…1000 ส่วน แล้ว` (pinned by SHA-256), which now
differs from the crop prompt only in the box clause; contrasts
`WHOLE_NOCLAUSE` vs `WHOLE` and `CROP_SAME_SCALE` vs `WHOLE_NOCLAUSE`, readings
stated in advance. Full run `kaggle-find-vs-read-f1-7209a2101bf1` (69 items,
five arms, both models) is running.

## D1 (G2) — PR #46, needs your approval

All three edits built in: the grid-aligned crop **window** moves by `d` over
the prepared page (no resampling, white outside, size unchanged — tested for
every `d`); `d ∈ {0, 4, 8, 12}` patch phase, `d = 16` merge pairing as a named
contrast, `d = 32` the phase-neutral control; primary outcome exact flip
counts vs `D0`, compared with flips(32), readings in §6, no interval rule,
consonant flips alongside. Same 69 items, prompt and scoring as F1, Typhoon
primary. The Decision Log entry (2026-10-04b) is in the PR.

## S1 — what kind of token diverges (CPU, PR #45)

| model | base rate of mark tokens in `REF` | at divergence `PLD5` / `PLD10` | tone involved |
|---|---|---|---|
| base | 12.1% | 19% (4/21) / 29% (4/14), incl. `่`↔`้` swaps | 3/21 / 5/14 |
| typhoon | 22.4% | 0% (0/12) / 5% (1/20) | 0/12 / 1/20 |

On the base, marks are over-represented at near-ties, so "identical except
near-ties" is not neutral there; on Typhoon, divergences are almost all
alternative Thai token boundaries. A handful of events — direction only.

## What I need from you

Review and approve PR #46 (or merge it). Then D1's smoke, and the full run
after it.
