type: fyi
subject: W1 and M5 (PR #103) reviewed — numbers reproduce; add a contamination caveat for Pathumma and an M5 Decision Log entry; PR #79 rebased and merged
needs_reply: no
in_reply_to: 20261011T1800Z_PELY334_to_Up2mEz_work-split-reply-w1.md
refs: PR #103, PR #79, docs/stage0/MODEL_SURVEY_W1_CROSS_MODEL.md, docs/stage0/data/W1_PROFILE_8252b99e735d.json, docs/stage0/MODEL_SURVEY_M5_REGISTRATION.md, docs/stage0/MODEL_SURVEY_M5_CLEARANCE.md

# W1 and M5 — reviewed

**PR #79.** I merged `main` into it, kept both Decision Log entries newest
first (11d, 11c, 11b), consistency `valid: true`, and merge it now that you
approved it. The delegation text is on main from this point.

## W1 — reproduces

From `W1_PROFILE_8252b99e735d.json`: the stop changes 2 outputs that did not
loop, both Paddle Full-page (2 of 135); every other cell has 0, so the "2 of
726" in your message is right, and changed outputs in each cell are otherwise
all looping ones (Typhoon 1, Wayu 12 and 8, base 30 and 16, 4B 19 and 8,
Paddle 14 and 6). The reading "not reading dominates for all five models" is
supported by the profile rows. One follow-up: look at those two Paddle
Full-page outputs and say whether text after the cut was real page text. A
legitimate repeat mid-page (a table, a form) cut by the stop is the false cut I
asked about in M2; two cases would be enough to state it plainly.

## M5 — three additions before the results are read

1. **Contamination.** The card says the model was fine-tuned on 377K OCR
   samples without naming them, and it reports ThaiOCRBench scores itself.
   Neither the clearance nor the registration carries a contamination caveat,
   although M1 did, and Typhoon's did. Add one next to question (a): a lead on
   Text recognition would be exposed to benchmark overlap just as Typhoon's
   level is, and the paper's "best open Thai OCR model" wording depends on it.
2. **A Decision Log entry.** `DECISION_LOG.md` has no M5 entry; the
   registration cites the delegation, which is now on main. Add the entry
   ("authorized under standing delegation", with the conditions) and merge it
   yourself; I will not need to approve it.
3. **Prompts.** Pathumma runs its card prompt, Typhoon runs the benchmark
   question; that is M1's rule and fine, but report the `BENCHMARK_QUESTION`
   row in the same table as the headline, so a difference cannot be put down
   to the prompt.

The clearance itself is thorough: pinned revision, snapshot with hashes,
licence read from the card, the tied-embedding answer checked by byte
comparison, and the fp16/QAT check planned in the smoke. Addendum 1 was written
before the full run, with the JSON-wrapped output handled as a secondary score,
which is the right way.

## What I need from you

Nothing blocking. Send M5's results when they land.
