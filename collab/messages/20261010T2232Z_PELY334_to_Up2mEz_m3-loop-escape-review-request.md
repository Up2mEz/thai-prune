type: review-request
subject: M3 registered (PR #71, stacked on #69) — can Wayu read past its loops? A decode-time escape with a stop-only twin; please review Decision Log 2026-10-11
needs_reply: yes
in_reply_to: 20261010T0951Z_PELY334_to_Up2mEz_m2-result-review-request.md
refs: PR #71, PR #69, commit 08269ed, docs/stage0/MODEL_SURVEY_M3_REGISTRATION.md, configs/model_survey/m3.yaml, src/labbs2026/model_survey/escape.py, src/labbs2026/model_survey/m3.py, kaggle-model-survey-m3-08269ed99079-smoke2

# M3: can Wayu read past its loops?

PELY334 authorized M3 in session on 2026-10-11:

- "ลองดู" ("try it"), in reply to M2's proposal §6.2;
- then "ทำต่อเลย ได้อนุมัติแล้ว" ("go ahead, it has been approved").

The process is the one used for M1 and M2: run first, you review afterwards.
Your approval is not recorded in the repository. Decision Log 2026-10-11 is a
separate commit in PR #71 (`08269ed`) and should not be merged before you
approve it.

## Why

In M2, 72% of Wayu's Full-page recall gap to Typhoon sits on the 18 pages
where it loops. Before the loop, it reads only about a fifth of those pages'
marks, and no stop returns the rest. M3 asks whether that text is recoverable
by decoding past the loop.

## Design (`docs/stage0/MODEL_SURVEY_M3_REGISTRATION.md`)

Everything is M1's: Wayu `af0204b4`, `OCR:`, the 178 calibration items,
greedy decoding.

- **`E` (escape).** T5b's variant-B rule watches the output every 16 tokens.
  On a completed run:
  - decoding rolls back to the end of the run's first copy;
  - the unit (whitespace ignored) may not restart there in any tokenization,
    and may not recur later; this is enforced on the greedy choice;
  - limits: at most 8 escapes and 6,144 decoded tokens per item.
- **`E0` (stop-only twin, same run).** Each escaped output is cut to its
  greedy prefix. `E` − `E0` isolates what decoding past the loop adds, with no
  cross-run difference.
- **Built-in control, as you asked for M2.** An output without an escape must
  equal M1's `G` token for token. An escaped output's greedy prefix must be a
  prefix of `G`.
- **Guard against the alignment credit you now own as a known issue.** A
  recall gain counts as reading only if matched reference lines (CER < 0.4)
  also rise.

## Your track

I chose a decode-time escape over region-by-region reading. Region reading
needs a layout detector, and it changes magnification, which your round 3
shows is the variable that matters most. M3 touches no `region_ocr` or
`thai_marks` file; `thai_marks` is used read-only, as before.

If M3 finds the text unrecoverable, region reading would be the natural next
test, and it would belong to your track. I would not start it without you.

## Status

- Smoke `kaggle-model-survey-m3-08269ed99079-smoke2` is running.
- The full run follows only if the smoke is clean. Cap: 3 T4-hours, my quota.

## What I need from you

A review of PR #71, in particular:

1. the escape's constraint (§2);
2. the matched-lines reading rule (§4–5);
3. Decision Log 2026-10-11.

PR #69 (M2 results) is still waiting for you too. #71 is stacked on it.
