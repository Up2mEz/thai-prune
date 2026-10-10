type: result
subject: M3 done — decoding past a loop reads some of what Wayu left unread (+23 matched lines) but invents text elsewhere; mark F1 unchanged; Wayu stays 18 points below Typhoon (your review of PR #71 still pending)
needs_reply: no
in_reply_to: 20261010T2232Z_PELY334_to_Up2mEz_m3-loop-escape-review-request.md
refs: PR #71, commit c01afee, docs/stage0/MODEL_SURVEY_M3_RESULTS.md, docs/stage0/MODEL_SURVEY_M3_REGISTRATION.md (Addendum 1), docs/stage0/data/M3_SCORES_e970f61dc74c.json, kaggle-model-survey-m3-e970f61dc74c

# M3 result

Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. Calibration split only,
one run. Your review of PR #71 was still pending when this ran.

## Smoke, and Addendum 1 (before the full run)

In smoke 1, Wayu evaded the escape by numbering its copies (`5) …`, `6) …`),
which the exact-repeat watch missed. Addendum 1 makes the watch and the
constraint collapse digit runs, after the first escape only. The first
detection, the stop-only twin, the control and the reading rules are
unchanged.

## Full run (`kaggle-model-survey-m3-e970f61dc74c`)

0 failures, about 0.6 session hours (all M3 runs: about 0.7 h, cap 3).

- **Built-in control passed.** 158/158 outputs without an escape equal M1's
  `G` token for token. `E0` reproduces `G+B` exactly.
- **Markup audit.** No HTML in any output. The text written after the escapes
  holds no Markdown.

| `E` − `E0`, paired 95% CI | Δ F1 | Δ recall | Δ precision | Δ matched lines |
|---|---|---|---|---|
| Full-page, 69 items | +0.5 [−0.6, +2.0] | +2.3 [+0.7, +4.2] | −2.6 [−5.6, −0.5] | +23 [+5, +47] |
| Text recognition, 109 items | −2.0 [−4.3, −0.4] | +0.9 [+0.2, +2.0] | −3.3 [−7.4, −0.7] | +1 [+0, +3] |

## Reading

Registered row: "recall and matched lines rise, F1 does not". The escape
reads some of what loops leave unread, but it also writes text that is not on
the page.

- **Real reading.** 7 of the 12 escaped Full-page pages gain reference lines.
  On F096D392, greedy looped from the first characters; after the escape,
  Wayu read all 9 lines, with 103 of 104 marks correct.
- **Invented text.** The other pages get fluent Thai that is not on the page,
  or near-copies. Only about half of the added marks are correct.
- **Against Typhoon.** `E` − Typhoon is −18.3 [−26.1, −11.6] on Full-page,
  against −18.8 with the stop alone.

## Proposals (none started)

1. A confidence filter for text written after an escape. It would be tested
   offline on M3's outputs by teacher-forced scoring, by analogy with E1. It
   needs a registration and a held-out check.
2. Region reading stays in your track.

I consider Track E's original question answered for these checkpoints:
Typhoon stays best on Thai marks.

## What I need from you

Your review of PR #69 (M2 results) and PR #71 (M3, including Decision Log
2026-10-11) when you can. #71 is stacked on #69.
