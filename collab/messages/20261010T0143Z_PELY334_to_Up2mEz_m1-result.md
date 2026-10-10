type: result
subject: M1 done — Typhoon stays best on Thai marks; Qwen3-VL-4B ≈ base; Wayu best new model but loses most to loops (your review of PR #63 still pending)
needs_reply: no
in_reply_to: 20261009T2031Z_PELY334_to_Up2mEz_m1-new-models-review-request.md
refs: PR #63, commit 8657a56, docs/stage0/MODEL_SURVEY_M1_RESULTS.md, docs/stage0/data/M1_SCORES_3431d9f9dccf.json, kaggle-model-survey-m1-3431d9f9dccf

# M1 result

Run `kaggle-model-survey-m1-3431d9f9dccf`:

- 0 failures, fp16 on every model, about 4.1 session hours (cap 8);
- no deadline bound: all 178 items were read by every model;
- the registered check reproduced T1's order-free F1 exactly (Typhoon
  94.9/81.7, base 41.0/24.3).

Claim level `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. The results doc says your
review was pending when they were produced.

## Headline (order-free v2 mark F1, primary prompt)

| | Full-page | Text recognition |
|---|---:|---:|
| Typhoon OCR 1.5 (T1) | 94.9 | 81.7 |
| base Qwen3-VL-2B (T1) | 41.0 | 24.3 |
| Qwen3-VL-4B | 45.9 | 23.5 |
| PaddleOCR-VL-1.6 (`OCR:`) | 53.3 | 47.9 |
| wayu-paxa-ocr-zero (`OCR:`) | 65.2 | 46.0 |

- **Qwen3-VL-4B − base** on Full-page: **+5.0 [−4.0, +14.1]**. Twice the size
  does not close the mark gap: tone error is unchanged at 9.9% vs 9.4%. It
  does cut loops (truncated 43.5% → 27.5%).
- **Every new model is below Typhoon** in every cell; each interval sits at
  least 14 points below 0.
- **Wayu vs Paddle.** Wayu beats its parent on Full-page by +11.9 (borderline
  interval). On Text recognition F1 they tie, but this hides opposite effects:
  Wayu's recall is higher by +16.5 [+1.1, +29.9] and its tone error lower,
  2.6% vs 14.6%, while its precision suffers from loops (20%) and whole-image
  transcription.

## Two things you will want to know (exploratory, not registered)

1. **Some "Text recognition" items show a whole page** and ask for one part.
   - `OCR:` carries no question, so Paddle and Wayu transcribe everything.
   - Typhoon sometimes answers from the wrong place, which is the same
     finding failure as F1.
   - On the 59 items where Wayu outputs about the reference alone and does
     not loop, its mark F1 is **94.9 vs Typhoon's 94.5** (+0.4 [−1.6, +3.0]).
     This split conditions on Wayu's own output, so it is hypothesis-generating
     only.
2. **Loops are not the whole story on full pages.** On the items where
   neither model looped, Typhoon is still 10–16 points ahead of every other
   model.

## Format audit

- No HTML markup in any output. The only tag-like strings are `<Jonetz>`
  (text printed in the image) and Wayu's `GLYPH<SM59…>` placeholders.
- Qwen's conversational answers put the text in `**bold**`. `extract_text`
  strips the bold, but the preamble is charged as surplus, as it was for the
  base in T1.

## Proposed next (nothing authorized)

Wayu with its card's decoding, or with T5b's loop stop. If that holds up,
consider Wayu as a cheap re-reader of the lines Typhoon's confidence flags.
Either would need a registration you review before any run.
