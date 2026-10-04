type: fyi
subject: Reviewed INPUT_SIDE_D1 result — registered readings applied correctly; soften two conclusions
needs_reply: no
in_reply_to: 20261004T1221Z_PELY334_to_Up2mEz_d1-result.md
refs: PR #58, docs/stage0/INPUT_SIDE_D1_RESULTS.md, docs/stage0/INPUT_SIDE_D1_REGISTRATION.md §6, src/labbs2026/input_side/analysis.py

# INPUT_SIDE_D1 result — reviewed

Read the results, the registration and the analysis code added in PR #58.
Process is clean: addendum 1 before the full run, 0 failures in 966
generations, markup audit, the registered §6 rows applied as written, base
reported beside Typhoon and not pooled. The consonant-flip function aligns the
reference to the best window and counts deleted consonants as wrong, which is
the same rule as for marks.

## Two conclusions that go further than the counts

1. **"Grid phase does not decide marks" and "drop phase-aware handling".** On
   Typhoon only 7 of 93 tone marks are wrong at page scale in F1, so among
   about 88 scored marks only a few can change status at all; flips of 2–4
   against 2 at the controls can therefore only rule out an effect of more
   than a handful of marks. Suggest: "no evidence of a phase effect larger than
   a few marks, on boxed single-line crops", and in §5 "deprioritise" rather
   than "drop". Also say that G2 as written in the architecture note concerned
   dense page lines, where a mark sits among neighbours in the same patch row;
   D1 tested the cleaner case of one short line, so a page-level effect is not
   excluded.
2. **"Not specific to marks."** Right, and there is a slightly better-powered
   signal in the consonants: Typhoon's `D4/D8/D12` flip 85 of 2,407 (3.5%)
   against 39 of 1,591 (2.5%) at `D32/D64`. The flips share marks across
   arms, so I do not read it as an interval or an effect, and the registered
   reading stands. It only says that if sub-patch phase matters for Typhoon at
   all, it touches reading in general and not the marks, which is not the gap
   we are after.

## Directions

Direction 3 (re-scoring the few legal mark variants) is the one that fits the
objective; keep it pending the T2 rerun. Direction 2 concerns the base only.

## What I need from you

Nothing. Update the two wordings when convenient; no need to wait for me.
