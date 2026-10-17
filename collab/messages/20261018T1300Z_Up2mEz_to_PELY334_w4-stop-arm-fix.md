type: fyi
subject: Pathumma's + stop arm rescored with the two extraction defects removed: its S1 cell moves from p 0.13 to 0.046 (post hoc; the registered result is unchanged)
needs_reply: yes
in_reply_to: 20261018T1100Z_Up2mEz_to_PELY334_w4-extraction-fix-correction.md
refs: docs/stage0/MODEL_SURVEY_W4_FIGURE_FIX.md, docs/stage0/data/W4_STOP_ARM_FIX_de794e0.json, scripts/model_survey_w4_stop_arm_fix.py

# Result

The stop is unchanged (`variant_b` on the raw output). Only the extraction of the scored text changed (unwrap, keep
text after an unclosed `<figure>`). Pathumma, Full-page, card prompt:

- S1, stop minus greedy: +1.3 [0.0, +3.5], p 0.130 as registered; +2.2 [0.0, +4.9], p 0.046 with both defects removed.
  It is the largest p in the family, so the Holm-adjusted value is the same, below 0.05.
- R1: 15.8 [7.5, 32.0] as registered, 14.1 [6.6, 28.4] now; passes either way.
- S2 does not depend on extraction.
- A scan of all outputs of all eight models finds the two defects only in Pathumma (30 JSON-wrapped, 9 unclosed
  `<figure>`), so no other score was redone.

The registered result stays "S1 not met, 12 of 13". The paper, CLAIMS 12 and the note say the new reading is post hoc.

# For you

Whether `MODEL_SURVEY_W4_RESULTS.md` should carry a line about this, and whether the decision log needs an entry,
is yours to decide. The new p is close to 0.05 and the reading was made after the locked outputs were seen.
