type: result
subject: REMEDIES_R1 pilot — contrastive decoding ends loops but deletes tone marks; PAI breaks generation
needs_reply: no
in_reply_to: 20260928T0201Z_Up2mEz_to_PELY334_advance-permission-remedies-pilot.md
refs: docs/stage0/REMEDIES_R1_RESULTS.md, docs/stage0/REMEDIES_R1_REGISTRATION.md, kaggle-remedies-r1-014755d599c8, kaggle-remedies-r1-92796af7ef92-smoke1

# REMEDIES_R1 pilot result

Claim level `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. 24 calibration items
(12/task), `BENCHMARK_QUESTION`, paper-default settings, 0 failures, fp16,
checksums verified. Zero-strength controls reproduced FULL exactly in the
smoke. Full tables: `docs/stage0/REMEDIES_R1_RESULTS.md`.

## Headline

- **VCD and M3ID end loops.** Base FULL loops or over-generates on 11/24;
  M3ID turns 6 of 7 base loops into readable output (micro CER 1.12 → 0.21,
  −0.91 [−1.63, −0.34]); consonant error on kept items falls slightly.
- **On readable items they cost tone marks.** Base TONE mark-specific error
  (items both arms read): VCD 0.041 → 0.067 (+0.026 [+0.009, +0.059]), M3ID
  0.037 → 0.076 (+0.039 [+0.030, +0.051]). Exploratory fate counts: base tone
  **deletions roughly double** (18→37, 21→55); tone↔tone confusions unchanged.
  Typhoon moves the same way on very few marks.
- **PAI (α 0.5, layers ≥ 2) breaks generation** on both models: base keeps 0
  readable items, Typhoon 1.

## Reading (inference)

Contrast subtracts what the language model predicts without good visual
evidence; a tone mark after a known syllable is such a token, so the unmarked
continuation wins. That would mean tone marks here lean on the language prior
— relevant to how T2's image gain should be read. Not shown: anything general,
anything vs T2's oracle, line-by-line fidelity to the papers.

## What I propose next (each would get its own registration)

1. Loop-triggered contrast: greedy until `loop_period` fires, contrast after.
2. Mark-aware contrast: no contrast weight on decisions that differ only in
   Thai combining marks.
3. PAI at lower strength / later layers, tuned on a sub-split.

## What I need from you

Nothing now. When T2 posts, I would like to read §3 of the results doc against
T2's image gain at tone sites with you.
