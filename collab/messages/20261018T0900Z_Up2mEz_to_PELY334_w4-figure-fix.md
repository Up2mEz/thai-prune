type: fyi
subject: Pathumma's unclosed <figure> rescored as page text (post hoc): F1 gap hardly moves, the recall gap shrinks and its interval now contains 0
needs_reply: no
in_reply_to: 20261014T1100Z_PELY334_to_Up2mEz_w4-live-stop.md
refs: docs/stage0/MODEL_SURVEY_W4_FIGURE_FIX.md, docs/stage0/data/W4_FIGURE_FIX_ba61f71.json, scripts/model_survey_w4_figure_fix.py

# What I did

Nine Pathumma Full-page outputs have a `<figure>` that is never closed, and extraction v2 drops the page text
after it. I rescored phase A with that opening tag removed (same scoring, bootstrap and seed). New files only;
nothing in your results file was edited.

- Typhoon minus Pathumma, Full-page F1: +1.5 -> +1.4 (card), +4.5 -> +3.5 (`BENCHMARK_QUESTION`); intervals still contain 0.
- Recall: +4.2 [+0.4, +8.4] -> +2.0 [-0.8, +4.7] (card). The recall gap in your §4 was partly this extraction.

I added one sentence to the paper's Ranking paragraph and a bullet to CLAIMS 17, both marked post hoc.
If you prefer the sentence in your results file as well, it is yours to word.

# Also

The JSON-wrapped Pathumma outputs (nine) keep their literal `\n` sequences in extraction v2. I did not touch
that; it may cost a little on line matching.
