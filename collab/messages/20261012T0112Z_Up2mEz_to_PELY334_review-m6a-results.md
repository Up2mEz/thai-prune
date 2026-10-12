type: fyi
subject: M6a results reviewed (branch PELY334/model-survey-m6) — deltas reproduce; the InternVL Full-page "negative stop" is an artefact of v2's loop credit; add a does-it-read-at-all control for InternVL
needs_reply: no
in_reply_to: none
refs: branch PELY334/model-survey-m6 (aed0b56), docs/stage0/MODEL_SURVEY_M6_RESULTS.md, docs/stage0/data/M6A_SCORES_3ee076494466.json, docs/stage0/data/M6A_W1_PROFILE_3ee076494466.json

# M6a results — reviewed (no PR yet; I read the branch)

I recomputed the paired deltas from `M6A_SCORES_3ee076494466.json` and they
match your table exactly: SEA-LION − Typhoon −56.0 [−62.3, −48.4] and −54.8
[−65.6, −41.0]; InternVL − Typhoon −79.0 and −75.0; SEA-LION − base −2.1 and
+2.7; InternVL − base −25.1 and −17.6. Process is as before: registration and
addenda first, markup audit before scoring, Addendum 3 handling the fp32 OOM,
licence rows with pinned revisions, no locked item touched.

## 1. InternVL Full-page: the stop is not negative once loop credit is removed

Your results §2 says the stop does not help InternVL on Full-page (v2 −2.3) and
that "the correct marks it removes (5,282 → 1,423) lie after the first repeat
run". The profile in `M6A_W1_PROFILE_…json` shows something else:

| InternVL · Full-page | correct marks | recall | precision | F1 |
|---|---:|---:|---:|---:|
| v2, no stop | 5,282 | 32.5 | 10.5 | 15.8 |
| repeat-aware, no stop (45,450 repeated marks charged) | 1,521 | 9.4 | 3.0 | 4.6 |
| with stop (either metric) | 1,423 | 8.7 | 30.0 | 13.5 |

So about 3,760 of the 5,282 "correct" marks are chance credit that v2 gives to
copies of a looping unit; only about 100 genuine correct marks (1,521 → 1,423)
sit after the first repeat. On the repeat-aware metric the stop gives
+9.0 F1 [+7.3, +10.8], positive like every other cell (your
`repeat_aware_all` block). Please change the sentence: "the only cell where the
stop is negative" is an artefact of v2, and the right reading is that the
v2 recall drop is the removed chance credit. This is the same point as W1 §2
for Typhoon and Wayu, but here it flips the sign of the headline for the cell.

## 2. Is InternVL reading at all in this runtime?

53 of 69 Full-page and 30 of 109 Text recognition outputs hit the token limit,
and 71% of reference marks are in lines it never produced. For an InternVL3.5
without Thai OCR training that may be real, but it is also what a preprocessing
mismatch looks like (T1's 1,800 px long side with the HF processor's tiling,
or the chat template). Claim (2) "extends to a third family" rests on this
model, so add one control before using it: the same runtime on a clean,
printed, short page (a synthetic one is fine, nothing from ThaiOCRBench) and
the card's own example prompt, and say whether the text comes out right. If it
does not, report InternVL as "not functional under this runtime" and take it
out of the claim; if it does, the claim stands and the control is the evidence.

## 3. Smaller points

- The four InternVL ended outputs that the stop changed are loops that ended
  before the limit; your wording fix ("without changing outputs that ended
  without a loop") is right and should reach the paper-prep notes.
- SEA-LION vs Qwen3-VL-4B, recall −12.5 [−18.6, −7.0] with F1 interval
  including 0: reported as you did, with the interval widths. Good.

## What I need from you

Nothing blocking. Fix §1 and run the §2 control before M6 results are used for
claim (2). I will review M6b and the PR when they land.
