# MODEL_SURVEY_M3 — registration (Track E: can Wayu read past its loops?)

**Status: `APPROVED` by PELY334.** In session on 2026-10-11, PELY334 replied
"ลองดู" ("try it") to the proposal in `MODEL_SURVEY_M2_RESULTS.md` §6.2. They
then replied "ทำต่อเลย ได้อนุมัติแล้ว" ("go ahead, it has been approved").
Up2mEz's approval is not yet recorded in the repository. As for M1 and M2, the
Decision Log entry (2026-10-11) stays unmerged until Up2mEz approves it.

This registration was written before any M3 output on ThaiOCRBench existed. The
only outputs so far are local engineering checks on synthetic images (§8).
Parameters: `configs/model_survey/m3.yaml`. Claim level of every result:
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

**Question.** M2 found that T5b's stop recovers most of what Wayu's loops
cost. But 72% of Wayu's Full-page recall gap to Typhoon sits on the 18 pages
where greedy Wayu loops: before the loop starts, it reads only about a fifth
of those pages' marks.

Is the rest of those pages recoverable by decoding past the loop, with the
image, prompt and decoding unchanged? Or does a loop mark the point where Wayu
stops being able to read the page?

**Why a decode-time escape, not region-by-region reading.** Reading region by
region has two problems here:

- It needs a layout detector, and this repository has none.
- It changes the image each region is read at, that is, its magnification.
  That is the variable Up2mEz's region-OCR rounds show matters most: round 3
  found a U-curve with its minimum near 2.4× area upsample.

An escape changes nothing except what happens after a loop, so its effect can
be attributed. Region reading stays a proposal, and it belongs to Up2mEz's
track.

## 1. Fixed inputs (M1's for Wayu; tested equal to `configs/model_survey/m1.yaml`)

| input | value |
|---|---|
| model | `wayu-ai/wayu-paxa-ocr-zero@af0204b4f334a6d5068b6bac2b3738932d6e289b` |
| prompt | `OCR:` |
| items | T1's 178 calibration items |
| image policy | T1's |
| decoding | greedy, `repetition_penalty=1.0` |
| `max_new_tokens` | 3072; here it caps the output that is kept |
| precision | fp16, with fp32 fallback |
| attention | `sdpa` |
| `use_cache` | true |
| hardware | Kaggle 2×T4 |

The locked split is never touched, and images are never written.

## 2. Arms

**`E`, the escape (`model_survey.escape`).** Decoding is greedy, as in M1.
Every 16 tokens, T5b's variant-B rule (k = 8 / 6; Decision Log 2026-10-03e)
checks the output. When a run completes its 8th copy (6th for long units),
three things happen:

1. **Roll back.** Decoding rolls back to the first token boundary at or after
   the end of the run's first copy. This is the point where the model chose to
   start a second copy.
2. **Constrain.** From that point on, the run's unit (compared without
   whitespace) may not be started again right there, in any tokenization. Nor
   may it be completed again anywhere later.
   - The constraint acts on the greedy choice. Candidates are taken in score
     order; the first 64 are checked, and each one that breaks it is set to
     −inf.
3. **Continue.** Decoding resumes from the rolled-back output.

Limits:

- After 8 escapes, the next run is cut at its first copy, as in B.
- Each item may decode at most 6,144 tokens (2 × 3072), discarded ones
  included.

**Derived arms (no extra run):**

- **`E0`, the stop-only twin (`m3.stop_only`).** Each escaped output is cut to
  its greedy prefix, up to the first rollback. That is what stopping at the
  loop yields in the same run. `E` − `E0` isolates what decoding past the loop
  adds, with no cross-run difference.
- **`G` and `G+B`.** M1's greedy outputs, without and with B (M2's reference
  arm). M2's control reproduced `G` token for token.

**Built-in control (`m3.control`).**

- An output without an escape must equal `G`'s, token for token.
- An escaped output's greedy prefix must be a prefix of `G`'s output.
- **Pass:** every item.
- **On a failure:** `E` − `E0` is still read, because it is within the run.
  Nothing against `G` or `G+B` is read, and the failing items are listed.

## 3. Scoring and cost

Scoring is M1's and M2's:

- T1 scoring v2 and the order-free v2 mark metric (`max_cer` 0.4, residual);
- base and Typhoon from T1's archive;
- every arm scored against this run's references;
- item bootstrap, 2,000 resamples, seed 20261011.

Cost is reported per task: kept tokens, decoded tokens (discarded ones
included), generation seconds, escapes, final cuts and step-cap hits.

## 4. Primary outcome

Per task, `E` − `E0` on the same items:

- paired differences in order-free mark F1, recall and precision, each with a
  95% item-bootstrap interval;
- the paired difference in **matched reference lines**, lines located in the
  output at CER < 0.4 (order-free metric, `matched_lines`).

Full-page OCR is the primary task. The same contrasts are also reported on the
escaped items alone, as a description.

**Secondary:**

- `E` − Typhoon;
- `E` − `G+B`;
- `E0` − `G+B`, which should be about 0, since the twin reproduces M2's stop;
- cost and escape diagnostics;
- Text recognition.

**Why matched lines.** M2 §4b found that the residual alignment credits
repeated text by alignment alone. A recall gain is therefore read as reading
only if matched lines also rise. A whole reference line located at CER < 0.4
is not a chance alignment.

## 5. What each pattern would mean, stated in advance (Full-page)

| pattern | reading |
|---|---|
| recall and matched lines rise, and F1 rises | the text after a loop is recoverable by decoding past it; the escape is worth keeping for Wayu |
| recall rises but matched lines do not | the gain is alignment credit for junk, not reading |
| recall and matched lines rise, but F1 does not (precision falls) | the escape reads some of the rest but adds junk; a filter would be needed before any use |
| recall does not rise | decoding cannot recover the text after a loop. A loop marks where Wayu stops reading the page, and only an input-side change (regions) could test more |
| `E` − Typhoon still entirely below 0 | even with the escape, Wayu stays below Typhoon |

"Rise" and "fall" are read on the paired intervals and reported with them, as
in M2. The comparison is descriptive; there is no gate.

## 6. Budget, smoke, stopping

**Expected cost.**

- In M1, greedy decoding of the 178 items took about 1.0 GPU-hour of
  generation.
- About 20 items have a B-run in `G`. The escape can add at most 3,072
  decoded tokens to each, about 22 minutes in the worst case, plus the
  watch's checks.
- With two position shards, one per T4, each shard should take about 45 to
  60 minutes.

**Stopping rules.**

- Each unit stops starting items after **1.5 h**; skipped items are recorded
  as `not_run`.
- **Cap: 3 T4-hours** of session time, on PELY334's own quota.

**Smoke first:** `--smoke 2`, the first two calibration items in Id order.
`G` has a B-run on 0159AF30 and none on 038EB8BB, so the smoke exercises both
the escape and the control.

## 7. Not in scope

- other models;
- Wayu's `BENCHMARK_QUESTION`;
- other decoding;
- region and layout pipelines;
- Typhoon with the escape;
- any change to the order-free metric (M2 §6.3 leaves that to Up2mEz);
- the locked split.

## 8. Engineering checks before this registration was frozen (synthetic images; not results)

The checks ran locally on an RTX 3060 with transformers 5.12.0 and torch 2.11
(Kaggle uses 2.14), on rendered Thai pages:

- **No repeated text.** On a page without repeats, `E` equals greedy token for
  token (172 tokens, one `generate` call).
- **Continuing from a kept prefix.** Continuing from 10, 40 and 80 tokens
  reproduced greedy's continuation exactly. Rolling back by re-reading the
  prefix does not change decoding.
- **A legitimate repeat.** On a page of 14 identical lines:
  - greedy runs past the 14 lines to the token limit;
  - `E`'s watch fires at the 8th copy;
  - the escapes push the model into variants of the line
    (`…58 บาทย่อดยรมหัง…`), and the step cap ends it.

  With nothing else to read on the page, the escape produces junk instead of
  repeats. That is the failure mode the matched-lines check (§4) is there to
  catch.
- **A first version was too weak.** It banned only the single token at the
  rollback point, and the model re-entered the loop through another
  tokenization (`ทย` → `ท` + `ย`). The constraint in §2 replaced it.
- **Cost of the watch.** Variant B's check takes at most about 65 ms on a
  4,000-character window. The watch uses 2,600 characters, enough to hold a
  completed run of the longest unit.
