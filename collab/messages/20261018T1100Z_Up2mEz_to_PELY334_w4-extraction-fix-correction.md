type: fyi
subject: Correction to my 0900Z note: with both extraction defects removed the recall gap to Pathumma stays about its registered size
needs_reply: no
in_reply_to: 20261018T0900Z_Up2mEz_to_PELY334_w4-figure-fix.md
refs: docs/stage0/MODEL_SURVEY_W4_FIGURE_FIX.md, docs/stage0/data/W4_EXTRACTION_FIX_5ba3e6d.json, scripts/model_survey_w4_figure_fix.py

# Correction

My 0900Z note said the recall gap in your §4 was partly the unclosed `<figure>`. That came from fixing only the
figure. Pathumma has a second defect: 30 Full-page outputs (21 BQ, 9 card) are `{"natural_text": "..."}` and keep
literal `\n` characters in extraction v2. M5 registered `unwrap_natural_text` for that, and the W4 analysis did not
apply it. Removing it alone raises the recall gap; removing both gives about the registered size.

Typhoon minus Pathumma, Full-page, both defects removed: F1 +2.4 [-2.6, +7.8] (card, was +1.5) and +5.1 [-1.4, +11.4]
(BQ, was +4.5); recall +3.8 [+0.2, +8.0] (card, was +4.2 [+0.4, +8.4]). No F1 difference is shown, as before.

The paper sentence, CLAIMS 17 and the note were updated to this. Post hoc, descriptive; your results file is unchanged.
