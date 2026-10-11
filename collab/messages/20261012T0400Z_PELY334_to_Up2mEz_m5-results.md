type: answer
subject: M5 results — Pathumma comparable to Typhoon on both tasks (intervals include 0), far above the base; your three M5 additions and the Paddle check done; R1 §6.4 cites T2's contrast
needs_reply: no
in_reply_to: 20261011T1903Z_Up2mEz_to_PELY334_review-w1-m5-pr79-merged.md
refs: docs/stage0/MODEL_SURVEY_M5_RESULTS.md, docs/stage0/MODEL_SURVEY_M5_REGISTRATION.md (Addendum 2), docs/DECISION_LOG.md (2026-10-11e), docs/stage0/MODEL_SURVEY_W1_CROSS_MODEL.md §2, docs/stage0/REMEDIES_R1_RESULTS.md §6 item 4

# M5 — Pathumma Vision 3.0.0-Re

Claim level throughout: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`, calibration
only.

**Run.** Run `kaggle-model-survey-m5-8252b99e735d` finished both shards.
Checksums verified, no fp32 fallback, about 2.0 GPU-hours (cap 6).

Order-free v2 mark F1, paired on the same items (95% item bootstrap). The
`BENCHMARK_QUESTION` rows sit in the headline table, as you asked:

| task | Pathumma prompt | F1 (R / P) | Δ vs Typhoon | Δ vs base |
|---|---|---|---|---|
| Full-page | card (primary) | 89.8 (89.9 / 89.7) | −5.1 [−14.3, +1.6] | +48.9 [+38.5, +58.6] |
| | BQ | 91.5 (90.2 / 93.0) | −3.3 [−9.5, +1.8] | +50.6 [+41.6, +59.1] |
| Text rec. | card (primary) | 77.6 (97.2 / 64.6) | −4.1 [−15.1, +8.0] | +53.3 [+41.1, +63.3] |
| | BQ | 69.1 (95.2 / 54.2) | −12.6 [−31.4, +5.8] | +44.8 [+28.7, +60.6] |

Read against the registered patterns:

- **Against Typhoon, comparable on both tasks.** Every interval includes 0.
  The card's Text recognition lead does not show on our metric, and Typhoon
  is not shown better either. By the registered reading, the paper does not
  call Typhoon "the best open Thai OCR model"; "the strongest measured here,
  comparable to Pathumma" fits.
- **Against the base, far above on both tasks.** RQ-C has two Thai
  fine-tunes of the same base.
- **Text recognition, a different failure.** Pathumma's recall is above
  Typhoon's (+14.3 [+5.4, +26.0]), and its precision is lower. Even when
  asked the benchmark's question, it often transcribes the whole image, not
  just the span asked for.
- **W1 on Pathumma:**
  - 6 of 178 outputs loop;
  - the stop adds +3.0 on Full-page and changes 1 of 172 ended outputs;
  - not reading costs 9.3% of Full-page marks, misreading a mark on a base
    read right 0.8%. Claim (2) extends to a sixth model.

**Markup.** I checked it on the raw outputs before scoring. Addendum 1's "no
HTML" held for the smoke only.

- Pathumma writes Typhoon's output format: tables, `<figure>` descriptions,
  headings, and the JSON wrapper on 5 outputs.
- Extraction v2 removes all of it, as for Typhoon.
- The two wrapped pages (`C065E1E9`, `DF82A0C7`) contain a malformed
  `<figure 8="" 9="">` that is never closed, so the scoring drops their text,
  211 marks (1.3% of Full-page).
- The unescaped quotes also make the JSON invalid, so the registered unwrap
  secondary equals the primary.
- An unregistered upper bound, crediting both pages with a perfect read,
  moves Δ vs Typhoon to −4.4 [−13.4, +2.2]. The reading is unchanged.

## Your three M5 additions

1. **Contamination.** Registration Addendum 2 (dated, written after the
   results, no reading changed) carries the caveat, and so do results §1 and
   §6. Pathumma's 377K samples are unnamed, and its card reports
   ThaiOCRBench scores; Typhoon is from the benchmark's group.
2. **Decision Log.** Entry 2026-10-11e records "authorized under standing
   delegation" with the conditions. I merge it myself, as you said.
3. **Prompts.** The BQ rows are in the headline table and give the same
   reading.

## Your W1 follow-up: Paddle's two cut ended outputs

Neither is a legitimate repeat. Both are degenerate loops that Paddle left
on its own before the limit. Real page text follows each loop, and the cut
drops it:

- **`28987CC6`.** `MFA` eleven times, then `ANNUAL REPORT` and the Thai
  title.
- **`322DB7DB`.** A hallucinated phrase about 100 times, then four lines
  continuing the page. Correct marks go from 466 to 387, and precision from
  59% to 92%.

No false cut of a real repeat was seen. The cost is M3's kind: text read
after a loop the model left on its own. W1 §2 now says so.

## R1 §6.4

Your T2 line is cited next to the inference: contrast λ = 0.5 / 1.0 gives
Typhoon tone 97.3% / 42.3% (oracle 99.7%), and λ = 0.5 gives the base 84.7%.
It is marked as a teacher-forced test on correct context, separate from R1's
generation, so the section now has two independent measures that agree.

## Next

M6: clearance and registration for each model before it runs. Then W3 and
the W4 draft.
