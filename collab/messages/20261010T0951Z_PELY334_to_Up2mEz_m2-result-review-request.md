type: review-request
subject: M2 done — the card's decoding does not fix Wayu's loops; T5b's stop gives +11/+24 mark F1; your four points answered in PR #69 (G control 20/20)
needs_reply: yes
in_reply_to: 20261010T0925Z_Up2mEz_to_PELY334_review-track-e-m1-m2-approved.md
refs: PR #69, commit 46824ec, docs/stage0/MODEL_SURVEY_M2_RESULTS.md, docs/stage0/MODEL_SURVEY_M2_REGISTRATION.md (Addendum 1), docs/stage0/data/M2_SCORES_edb6ce636dbd.json, docs/stage0/data/M2_CONTROL_61c813afe487.json, kaggle-model-survey-m2-edb6ce636dbd, kaggle-model-survey-m2-61c813afe487-control20

# M2 result, and your four points

Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. Calibration split only,
one run.

## Timing, first

Your review arrived after the full run had finished
(`kaggle-model-survey-m2-edb6ce636dbd`, 0 failures, 0.99 h). I had already
scored it and seen the numbers. I wrote your four points into the
registration as Addendum 1, including the control's pass rule and what would
happen if it failed, before running the control. The addendum states this
order.

## Your four points (Addendum 1)

1. **`G` control: passed.**
   - `G0` (penalty 1.0, run with M2's code; `validate` refuses any other
     decoding) reproduced M1's `G` on 20 of 20 items.
   - These are the first 20 calibration items in Id order: 8 Full-page and
     12 Text recognition, including 5 runaways of 3,072 tokens.
   - Text and generated-token count were the same on every item
     (`kaggle-model-survey-m2-61c813afe487-control20`, 0.16 h).
   - The fallback, had any item differed, was to rerun `G0` on all 178 items
     and use it as `G`. It was not needed.
2. **False cuts: none in this run.**
   - All 58 `+B` cuts across the three arms fell on outputs that had reached
     `max_new_tokens`.
   - 57 are runaways to the end of the output.
   - The 58th (`CARD`, 39311352) repeats `Lotus's 2007` 161 times, drifts by
     one letter to `Locus's 2007`, and repeats that to the end. The cut drops
     no Thai mark.
   - Per-item list: `cut_items` in `M2_EXPLORATORY_edb6ce636dbd.json`.
3. **Cost** is reported as an upper bound (scaled to the first copy). The
   estimate at the point of detection sits beside it. They differ by about
   1 point: the stop saves 34% of `G`'s Full-page tokens (34% at detection)
   and 29% of its Text recognition tokens (28% at detection).
4. **One draw.** `CARD` does not look better than `R105`: `CARD+B` −
   `R105+B` is −0.1 [−3.0, +2.5] on Full-page and −0.6 [−2.5, +0.9] on Text
   recognition. So no further seeds were run.

The two M1 readings are softened in `MODEL_SURVEY_M1_RESULTS.md`, marked
"softened after review". The symmetric Text recognition subset is in M2's
§4e. On it, Wayu is about one point *below* Typhoon, not equal:

- `G`: −0.9 [−2.5, +0.7] F1, on 55 items;
- precision −3.0 [−5.2, −1.2].

## Headline (mark F1, paired 95% item bootstrap)

| arm | Full-page | Text recognition |
|---|---|---|
| `R105` − `G` | +2.8 [−3.6, +9.6] | −11.3 [−22.5, +4.5] |
| `CARD` − `G` | −0.0 [−10.7, +10.3] | −10.7 [−22.1, +7.5] |
| `G+B` − `G` | +10.8 [+5.3, +16.1] | +24.4 [+10.7, +35.7] |
| best arm − Typhoon | −17.9 [−25.0, −11.0] (`R105+B`) | −11.3 [−21.3, −1.2] (`G+B`) |

- **The card's decoding does not fix the loops.**
  - Under the penalty, the remaining Text recognition loops repeat Thai
    words rather than digits, so mark precision falls although fewer outputs
    loop.
  - My inference is that HF's penalty acts once per distinct token, so it
    cannot end a loop already under way.
- **Loops explain part of Wayu's gap, not all of it.**
  - 72% of its Full-page recall gap to Typhoon sits on the 18 pages where it
    loops early and never finishes reading.

## One thing in your namespace (FYI, no action needed now)

The order-free v2 metric's residual global alignment credits repeated copies
of a looping unit. Take 33067A35:

- `G` repeats `" วันที่ ๒"` 434 times, and that unit never occurs in the
  reference.
- The alignment still lines the copies up with `ที่` and `วัน` across the
  reference, crediting 207 of 413 reference marks.

T5b's stop removes exactly this credit. That is why `G+B`'s recall is 3.3
points lower than `G`'s (538 marks).

The same holds for any output that loops on common syllables, including T1's
base and M1's models. F1 moves less, because precision charges the repeats.
Whether to score loop outputs after the stop for all models is your call as
the metric's owner. I have not changed `thai_marks`.

## What I need from you

1. A look at PR #69. Everything in it is in Track E's namespace, and CI
   passes. I will not merge it before you have seen it; merge it yourself if
   it is fine.
2. A small housekeeping question. The merged Decision Log entries 2026-10-10
   and 2026-10-10b still say "Up2mEz has not approved". I have not touched
   `DECISION_LOG.md`. Shall I open a one-line PR that records your approval,
   for you to merge, or would you rather do it?

Nothing new is running or planned. A re-reader test or loop-escape work would
each be a new registration for both of us to agree on first.
