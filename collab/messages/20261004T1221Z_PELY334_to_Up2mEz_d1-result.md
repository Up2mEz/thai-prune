type: result
subject: INPUT_SIDE_D1 — grid phase does not decide Typhoon's marks; the base is unstable to any small shift
needs_reply: no
in_reply_to: 20261004T1139Z_Up2mEz_to_PELY334_d1-approved-review-f1-r2-results.md
refs: docs/stage0/INPUT_SIDE_D1_RESULTS.md, docs/stage0/INPUT_SIDE_D1_REGISTRATION.md (addendum 1), kaggle-input-side-d1-9f51ed7d83f0, docs/stage0/FIND_VS_READ_F1_RESULTS.md (3b)

# INPUT_SIDE_D1 result

Claim level `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. 69 Fine-grained
calibration items, seven shifts, both models, 0 failures in 966 generations,
checksums verified. Markup audit clean (no tags; 0.0% Thai removed by either
normalization). Your d = 64 control and the extra section 6 row are in.

## One fix before the full run (addendum 1)

The first smoke showed the registered window clipped the box: moving a
box-sized window up by d dropped the box's bottom d rows, so at d = 32/64 the
model read another line. The window is now the box extended 64 px downward and
then moved — the box is fully inside for every d (tested). Recorded before any
full-run output.

## Typhoon (primary) — flips vs D0 (scored in both)

| | D4 | D8 | D12 | D16 | D32 (ctrl) | D64 (ctrl) |
|---|---|---|---|---|---|---|
| tone | 2/89 | 3/87 | 4/86 | 3/88 | 2/88 | 2/84 |
| upper | 0/114 | 1/110 | 1/108 | 4/109 | 1/111 | 2/111 |
| lower | 0 | 0 | 0 | 0 | 0 | 0 |
| consonants | 3.3% | 3.2% | 4.0% | 2.1% | 2.2% | 2.7% |

Phase shifts flip one or two tone marks more than the controls, and consonants
move the same way: no mark-specific phase effect (section 6, row 1).

## Base

Every shift including both controls flips ~8-13% of characters, marks and
consonants alike: unstable to any small input change (section 6, last row).

## Reading

A phase-aware input remedy is not supported for Typhoon; its remaining crop
errors (F1 reading ceiling: 7/93 tone marks at page scale, mostly rare tone
marks and the falling/low tone pair) are not where the grid falls. The base's
instability is what multi-view voting (your P-ZOOM-2 control) would exploit.

## What I need from you

Nothing.
