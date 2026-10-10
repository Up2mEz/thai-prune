# Track E — models not yet run on ThaiOCRBench (MODEL_SURVEY)

**Owner:** PELY334. **Package:** `src/labbs2026/model_survey/` (new; reuses
`thai_marks` read-only). **Branches:** `PELY334/model-survey-m1`,
`PELY334/model-survey-m2` (both merged), `PELY334/model-survey-m2-results`.

## Why

Every Thai-marks result so far rests on two checkpoints of one family
(Qwen3-VL-2B and its fine-tune Typhoon OCR 1.5). `AGENTS.md` forbids
generalizing Qwen-only results, and the researcher asked (2026-10-10) for two
or three further models tested "like we did in the past", i.e. with T1's
protocol. M1 answers two questions the remedies work keeps running into:
whether the base's mark deficit is a matter of size, and whether small
document-OCR specialists (one of them Thai-specialized on synthetic data) read
Thai marks better or worse than Typhoon.

## Steps

1. **M1** (`docs/stage0/MODEL_SURVEY_M1_REGISTRATION.md`): T1 on the 178
   calibration items for Qwen3-VL-4B-Instruct, PaddleOCR-VL-1.6 and
   wayu-paxa-ocr-zero; smoke first; cap 8 T4-hours on PELY334's quota.
2. Score offline with T1 scoring v2 and order-free v2; compare with T1's
   archived base/Typhoon outputs on the same items; write
   `docs/stage0/MODEL_SURVEY_M1_RESULTS.md`.
3. **Done:** M1 (`MODEL_SURVEY_M1_RESULTS.md`). Typhoon stays best; Wayu is
   the best new model but loses a share of what it reads to loops.
4. **M2** (`docs/stage0/MODEL_SURVEY_M2_REGISTRATION.md`, PELY334's "go" on
   2026-10-10): Wayu with its card's decoding (`R105`, `CARD`) and T5b's stop
   (`+B`). Do loops explain its deficit, and does the card's penalty cost marks?
   **Done** (`MODEL_SURVEY_M2_RESULTS.md`; Addendum 1's `G` control passed
   20/20). The card's decoding does not fix the loops. The stop recovers
   +11 / +24 mark F1. Wayu stays below Typhoon, mostly on pages it never
   finished reading.
5. Only if M2 warrants it: Wayu as a re-reader of the lines Typhoon's
   confidence flags (E1), as a new registration reviewed by Up2mEz. M2 does
   not strengthen the case: on the symmetric subset Wayu reads about one point
   below Typhoon (M2 results §4e). Not started.

## Governance

PELY334 authorized M1 in session and chose to run before Up2mEz's review.
The Decision Log entry (2026-10-10) stays unmerged until Up2mEz approves; a
`decision-request` message in `collab/` asks for the review. Results carry
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE` and say that the other researcher's
review was pending when they were produced.
