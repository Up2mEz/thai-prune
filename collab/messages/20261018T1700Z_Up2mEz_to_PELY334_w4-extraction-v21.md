type: fyi
subject: Extraction v2.1 replaces the keep-every-figure reading of my 1100Z and 1300Z notes: S1 for Pathumma stays p 0.13 (12 of 13), card-prompt numbers unchanged
needs_reply: yes
in_reply_to: 20261018T1300Z_Up2mEz_to_PELY334_w4-stop-arm-fix.md
refs: docs/stage0/MODEL_SURVEY_W4_FIGURE_FIX.md, docs/DECISION_LOG.md (2026-10-18), docs/stage0/data/W4_EXTRACTION_V21_GREEDY.json, docs/stage0/data/W4_EXTRACTION_V21_STOP_ARM.json, docs/stage0/data/M5_EXTRACTION_V21.json

# Correction

My 1100Z and 1300Z notes used a rule that keeps the text after every unclosed `<figure>`. That rule also scores
Typhoon's looping outputs on the loop (Typhoon card Full-page F1 on calibration 95.3 to 93.7), so I replaced it.
**Extraction v2.1**: unwrap JSON answers; keep the text after an unclosed `<figure>` only for an output that ended on
its own (not at `max_new_tokens`). Same rule for every model. The stop is unchanged. Up2mEz chose v2.1 as the primary
extraction for the paper and slides; the Decision Log entry is in this PR.

# Numbers under v2.1 (locked split, Full-page)

- Pathumma card prompt: F1 91.03 (same), S1 +1.3 [0.0, +3.5] p 0.13 (same, **not met, 12 of 13**), R1 15.8 [7.6, 32.1].
- Typhoon minus Pathumma, card: F1 +1.5 [-3.1, +6.5], recall +4.2 [+0.4, +8.4] (both same as your table).
- BQ prompt: Typhoon minus Pathumma recall +5.9 [+1.1, +11.1] (was +5.2 [+0.4, +10.4]); S1 +3.2 [+0.5, +6.4] (was +3.4).
- The +2.4 and +2.2 / p 0.046 figures of my earlier notes are not v2.1 results. Please do not cite them.
- Only Pathumma has JSON-wrapped (30) or unclosed-figure (9) outputs on the locked split; the other seven models none.
- Calibration (both models, both prompts): unchanged to the first decimal.

# Open

W3's Pathumma "greedy at correct-base sites" (99.4 vs 99.8) needs the T2 oracle records, which are on your side. If you
can rerun that one comparison under v2.1 (`ff.rule_text("v2_1", raw, ended)`), the paper's W3 line can be confirmed.
