type: decision-request
subject: Track E (MODEL_SURVEY_M1) — three new models on T1's protocol; PELY334 ran it before your review, please review the Decision Log entry
needs_reply: yes
in_reply_to: none
refs: PR #63, commit 9039f61, docs/stage0/MODEL_SURVEY_M1_REGISTRATION.md, configs/model_survey/m1.yaml, kaggle-model-survey-m1-9039f616be81-smoke2

# Track E (MODEL_SURVEY_M1): please review the registration and the Decision Log entry

PELY334 asked for two or three new models tested "like we did in the past".
This is T1's protocol, unchanged, on the 178 calibration items, run for three
checkpoints this repository has never run on ThaiOCRBench:

- `Qwen/Qwen3-VL-4B-Instruct@ebb281ec`: the base's family at twice its size.
- `PaddlePaddle/PaddleOCR-VL-1.6@c5630aba`, 0.9B.
- `wayu-ai/wayu-paxa-ocr-zero@af0204b4`, 0.9B, Thai fine-tune of Paddle on
  synthetic pages only. These are the Paddle and Wayu revisions already pinned
  for your region-OCR rounds.

All three are Apache-2.0 and ungated.

## The process differs from Tracks C and D

I asked PELY334 whether to wait for your approval, as C and D did. PELY334
chose to run first and have you review afterwards. So:

- the smoke is submitted, and the full run will follow on PELY334's own Kaggle
  quota (cap 8 T4-hours);
- the Decision Log entry 2026-10-10 is a separate commit in PR #63, and I will
  not merge that PR until you approve it;
- every M1 result will say that your review was pending when it was produced.

If you object to the design, the results stay unreported, and nothing else
changes: only new files, plus one new row in `INDEX.md`.

## Choices worth your eye

1. **Prompts.**
   - Qwen3-VL-4B runs `BENCHMARK_QUESTION` only. That is T1's primary, and
     `TYPHOON_CARD` was 3.3 of the base's 5.3 GPU-hours of loops.
   - Paddle and Wayu run their documented prompt `OCR:`, which is their
     primary, and also `BENCHMARK_QUESTION`.
2. **`use_cache=true` for every model.** PaddleOCR-VL-1.6 ships
   `use_cache: false`. A local check on a synthetic Thai image (not
   ThaiOCRBench) gave identical greedy output at 0.94 vs 0.061 s/token.
3. **Paddle and Wayu on Full-page are off-design.** They are region
   recognizers that normally run after a layout detector. Text recognition is
   their fair cell. This is stated before the run.
4. **Base and Typhoon are not rerun.** Their archived T1 outputs are scored by
   the same functions against this run's references. There is a check that
   order-free F1 reproduces 94.9/81.7 (Typhoon) and 41.0/24.3 (base) before any
   comparison is reported.

## What I need from you

Review `docs/stage0/MODEL_SURVEY_M1_REGISTRATION.md` and the Decision Log entry
in PR #63, then approve PR #63, or say what to change.
