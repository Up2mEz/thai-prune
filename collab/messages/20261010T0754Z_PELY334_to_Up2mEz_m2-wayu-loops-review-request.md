type: decision-request
subject: Track E follow-up (MODEL_SURVEY_M2) — Wayu's loops under its card's decoding and T5b's stop; run first by PELY334's choice, please review
needs_reply: yes
in_reply_to: 20261010T0143Z_PELY334_to_Up2mEz_m1-result.md
refs: PR #66, PR #63, commit edb6ce6, docs/stage0/MODEL_SURVEY_M2_REGISTRATION.md, configs/model_survey/m2.yaml, kaggle-model-survey-m2-edb6ce636dbd-smoke2

# MODEL_SURVEY_M2: please review the registration and Decision Log 2026-10-10b

PELY334 replied "go" to the next step I proposed in the M1 results (§7),
under the same process as M1: run first, you review afterwards. The smoke is
submitted; the full run follows on PELY334's quota (cap 3 T4-hours).

## What M2 asks

In M1, Wayu, the best new model, loses most of what it reads to loops:
20-26% of its outputs reach `max_new_tokens`. M2 asks how much of its deficit
the loops explain, and whether its card's decoding removes them without
costing marks. The second part is the one to watch: T5 showed a vendor
penalty costs Typhoon tone marks.

Same model, same `OCR:` prompt, same 178 items; decoding only:

| arm | decoding | source |
|---|---|---|
| `G` | M1's greedy outputs | not rerun |
| `R105` | greedy, penalty 1.05 | run |
| `CARD` | the card's recipe: T 0.1, top_p 0.7, penalty 1.05; seed per item from its id | run |
| `+B` | T5b's stop, applied offline to all three | offline |

## Readings fixed in advance (§5)

- Loops fall and F1 rises without recall or tone error worsening: the card's
  decoding is safe for Wayu.
- Loops fall but marks suffer: prefer the stop.
- The best arm is still entirely below Typhoon: loops do not explain Wayu's
  gap.

## What I need from you

Review the registration and the entry in PR #66, which is stacked on #63, and
approve both PRs or say what to change.
