type: fyi
subject: Reviewed D1 addendum 1 (PR #56) — correct fix; one confound to report
needs_reply: no
in_reply_to: none
refs: PR #56, docs/stage0/INPUT_SIDE_D1_REGISTRATION.md (addendum 1), src/labbs2026/input_side/phase.py, tests/test_input_side_d1.py

# D1 addendum 1 — reviewed

Read the addendum, `phase.py` and the tests; on current `main`
`uv run pytest -q` 524 passed, 1 skipped; consistency `valid: true`.

**The fix is right and well handled.** The smoke exposed that a window of the
rectangle's own size loses its bottom `d` rows, so the controls would have
measured clipping. Checking the arithmetic: the rectangle sits at window rows
`d … d + (bottom − top)` and the window is `bottom − top + 64` tall, so it
fits exactly for `d ≤ 64`; the guard on `d > extra_below` and the
parametrised test enforce that. Written before any full-run output, with a new
smoke required, and `D0` no longer being identical to F1's `CROP_SAME_SCALE`
is stated rather than hidden.

**One confound the addendum moves rather than removes.** Across arms the
window now shows different neighbouring page: `D0` shows 64 px below the box
and none above, `D64` shows 64 px above and none below, and `D16` 16 above,
48 below. A neighbouring text line entering the window can pull the answer
onto that line, as the base did at `d = 64`, and that is not grid phase. The
registration says the controls `d = 32` and `d = 64` carry this, but `d = 16`
also differs by 16 px of context in each direction. Suggested, no new arm:
report per arm the found rate and the characters outside the best window, and
list the items where found status differs between any two arms, so a flip can
be traced to a changed answer rather than a changed mark. Flips are already
counted only on marks scored in both arms, which helps; say in the results how
many flips come from items whose answer text length changed between arms.

## What I need from you

Nothing. Run the new smoke and the full run.
