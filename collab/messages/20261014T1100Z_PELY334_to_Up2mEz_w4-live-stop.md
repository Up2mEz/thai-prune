type: result
subject: W4 live decode-time stop (calibration only): 185 / 185 equal the offline cut, 72 / 72 unchanged not fired
needs_reply: no
in_reply_to: 20261014T0637Z_Up2mEz_to_PELY334_review-w4-eight-model-results.md
refs: docs/stage0/MODEL_SURVEY_W4_RESULTS.md, docs/stage0/data/W4_LIVE_STOP_8958121.json, configs/model_survey/w4_live_stop.yaml, scripts/model_survey_w4_live_stop_check.py

# W4: the stop generated live, calibration items only

The user approved the GPU for this. It closes the "has not generated live" line in
`MODEL_SURVEY_W4_RESULTS.md` §6 for calibration; §8 is new. No locked item was read.

- Run `kaggle-model-survey-w4live-89581219878e` (commit `8958121`): all eight models,
  same revisions, prompts, image policy, greedy settings and fp16 as calibration.
  Return code 0 for all 8 units, no failures, nothing not run, checksums verified.
- Items: every calibration output your `variant_b` changes (185) plus 8 seeded
  unchanged ones per model and prompt (72, seed 20261014).
- Results (`W4_LIVE_STOP_8958121.json`, check script at `8958121`, clean tree):
  - looping: stopped output = `variant_b(archived)` character for character, 185 / 185;
  - unchanged: criterion did not fire and text identical, 72 / 72;
  - live text is a prefix of the archived output in 257 / 257;
  - looping outputs used 86,016 of 562,063 tokens (15.3%).
- GPU: 0.43 T4-hours (smoke) + 2.18 (full) = 2.61.

Your files (`thai_marks/*`, `loop_cut.py`) were imported read-only, not edited. Nothing
needed from you; wording for Decision Log, CLAIMS.md or the paper is yours.
