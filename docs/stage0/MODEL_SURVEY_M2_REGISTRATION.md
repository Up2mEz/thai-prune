# MODEL_SURVEY_M2 — registration (Track E: Wayu's loops)

**Status: `APPROVED` by PELY334, then by Up2mEz** (collab
`20261010T0925Z_Up2mEz_to_PELY334_review-track-e-m1-m2-approved.md`, after the
full run had finished; the review's requests are Addendum 1). PELY334 replied
"go" on 2026-10-10 to the proposed next step (`MODEL_SURVEY_M1_RESULTS.md` §7),
under M1's process: run first, Up2mEz reviews afterwards. Sections 1–8 were
written before any M2 output existed; the only output then was a local
engineering check on a synthetic image (§8).
Parameters: `configs/model_survey/m2.yaml`. Claim level of every result:
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

**Question.** In M1, Wayu (the best of the three new models) loses most of what
it reads to repetition loops: under T1's greedy decoding 26% of its Full-page
and 20% of its Text recognition outputs reach `max_new_tokens`. Two things are
open:

- How much of its mark deficit do the loops explain?
- Do the decoding its model card recommends, or T5b's decode-time stop, remove
  the loops without costing Thai marks?

The second is not a formality. T5 found that a vendor repetition penalty (1.1)
costs Typhoon marks (Decision Log 2026-10-03d: F1 −1.1 to −1.3, Text
recognition tone error 17.1% → 22.6%). A penalty can suppress the tone-mark
tokens that Thai text repeats legitimately.

## 1. Fixed inputs (M1's for Wayu; tested equal to `configs/model_survey/m1.yaml`)

`wayu-ai/wayu-paxa-ocr-zero@af0204b4f334a6d5068b6bac2b3738932d6e289b`, prompt
`OCR:` (its primary in M1), T1's 178 calibration items, T1's image policy,
`max_new_tokens=3072`, fp16 with fp32 fallback, `sdpa`, `use_cache=true`, Kaggle
2×T4. The locked split is never touched; images are never written.

## 2. Arms

| arm | decoding | source |
|---|---|---|
| `G` | greedy, `repetition_penalty=1.0` (T1's) | M1's outputs (`kaggle-model-survey-m1-3431d9f9dccf`), not rerun |
| `R105` | greedy, `repetition_penalty=1.05` | run |
| `CARD` | the card's GPU recipe: `do_sample=true`, `temperature=0.1`, `top_p=0.7`, `repetition_penalty=1.05`; `top_k` resolves to the library default 50 (the card does not set it; recorded); one seed per item, `item_seed(20261010, Id)` | run |
| `G+B`, `R105+B`, `CARD+B` | T5b variant B (`thai_marks.loop_cut.variant_b`, Decision Log 2026-10-03e): stop where an exact repeat completes its 8th copy (6th for units of 50+ characters) | offline |

Decoding never revisits earlier tokens, with or without sampling at a fixed
seed. So cutting a finished output at the onset is what stopping decoding there
would have produced, for every arm. A cut output counts as not having reached
`max_new_tokens`. The tokens and seconds it saves are scaled by characters, an
approximation as in T5b.

## 3. Scoring and cost

Scoring is M1's: T1 scoring v2 and the order-free v2 mark metric, with base
and Typhoon from T1's archive, all against this run's references.

Cost is reported per arm and task: generated tokens, generation seconds, and
outputs reaching `max_new_tokens`.

## 4. Primary outcome

Per task, for each arm against `G` on the same items:

- the paired difference in order-free mark F1, recall and precision, with a 95%
  item-bootstrap interval (2,000 resamples, seed 20261010);
- the tone error given a correct consonant;
- the truncation rate.

Secondary:

- each arm against Typhoon (T1, `BENCHMARK_QUESTION`);
- cost;
- M1's exploratory Text recognition split by output length, per arm
  (exploratory, as M1 §4).

## 5. What each pattern would mean, stated in advance

| pattern | reading |
|---|---|
| `R105` or `CARD`: truncation falls and F1 rises, recall not lower and tone error not higher than `G` | the card's decoding fixes Wayu's loops without costing marks; use it for Wayu in any follow-up |
| truncation falls but recall falls or tone error rises (as T5 found for Typhoon at 1.1) | the penalty buys loop control with marks; prefer the stop (`+B`) |
| `CARD` ≈ `R105` | sampling at temperature 0.1 adds nothing over the penalty alone |
| `G+B` raises precision and F1, recall ≈ `G` | what loops cost Wayu is surplus text; what they leave unread is recall that no stop returns |
| the best arm's interval against Typhoon still entirely below 0 on both tasks | loops do not explain Wayu's gap to Typhoon |

The words "rises", "falls", "higher" and "lower" are read on the paired
intervals and reported with them. The comparison is descriptive; there is no
gate.

## 6. Budget, smoke, stopping

In M1, Wayu's `OCR:` cells took 1.04 GPU-hours with loops, so each run arm
should take at most about 1 hour. The two arms run on the two T4s in parallel,
about 1.3 hours of session time.

- Each unit stops starting items after **1.5 h** (`not_run` recorded).
- **Cap: 3 T4-hours** of session time, on PELY334's own quota.
- Smoke first: `--smoke 2`.

## 7. Not in scope

Other models, Wayu's `BENCHMARK_QUESTION` cells, other penalties or
temperatures, layout pipelines, Typhoon with `B` (T5b did that), any remedy,
and the locked split.

## 8. Engineering check before this registration was frozen (synthetic image; not results)

Local RTX 3060, `transformers 5.12.0`, a rendered two-line Thai image:

- both run arms generate through `thai_marks.runtime`;
- the resolved settings are as in §2 (`CARD`: `do_sample` true, temperature 0.1,
  top_p 0.7, top_k 50, penalty 1.05; `use_cache` true);
- `CARD` with the same item seed gave the identical output twice, and `R105`
  is deterministic.

## Addendum 1, 2026-10-10 — Up2mEz's review; written before the control runs

Up2mEz approved M2 (Decision Log 2026-10-10b; collab
`20261010T0925Z_Up2mEz_to_PELY334_review-track-e-m1-m2-approved.md`) and asked
for four things before M2 is read.

**Timing, stated plainly.** The review arrived after the full run
(`kaggle-model-survey-m2-edb6ce636dbd`) had finished and after its registered
scores had been computed and seen. The control below therefore runs after the
M2 numbers are known. Its pass rule is fixed here and concerns reproduction
only, so it cannot be tuned to them.

1. **Control for `G`.** `G` is M1's output from another run. A control arm
   `G0` decodes exactly as T1 and M1 (penalty 1.0, greedy; `m2.validate`
   refuses anything else). It runs with M2's code and environment on the first
   20 calibration items in Id order (`control.items` in
   `configs/model_survey/m2.yaml`; the smoke's two items are the first two).
   These are 8 Full-page and 12 Text recognition items; 5 of them reached
   `max_new_tokens` in M1.
   - **Pass:** every item's output equals M1's `G` token for token, read as
     the same text and the same generated-token count
     (`m2.reproduces`; `scripts/model_survey_m2_control.py`).
   - **If every item passes,** the comparisons against `G` are read as
     registered.
   - **If any item differs,** no arm effect against `G` is read. `G0` then runs
     on all 178 items in one further run and replaces `G`. That run is about
     1 hour; with the M2 run (≈ 1.0 h) and this control (≈ 0.3 h) it stays
     within the 3-hour cap.
2. **False cuts by `+B`.** Variant B fires on any output, not only on runaway
   ones. A legitimate eightfold repeat (form lines, table cells) would lose
   all the text after it. For every cut item the results report:
   - whether the output had reached `max_new_tokens`;
   - whether the run is a runaway to the end of the output, with less than
     one unit of text after its last copy;
   - the reference marks credited inside the removed text;
   - whether the repeated unit occurs in the reference at all.

   These come from `m2_exploratory.stop_effect`. Cuts of outputs that ended
   normally, and cuts of runs followed by more text, are the ones that can
   drop real reading. The registered reading "recall ≈ `G`" is judged with
   this split beside it.
3. **Cost is an upper bound.** The `+B` arms' tokens and seconds are scaled
   to the first copy, but a decode-time stop can only fire when the 8th copy
   completes (6th for long units). The saving reported for `+B` is therefore an
   upper bound. The tokens to the point of detection are reported beside it
   (`m2_exploratory.stop_effect`).
4. **One draw.** `CARD` uses one seed per item. "`CARD` is better than `R105`"
   is said only after two more seeds. Any other reading of `CARD` carries the
   one-draw caveat.

The exploratory readings (`scripts/model_survey_m2_exploratory.py`) also give
the symmetric Text recognition subset the review asked for: Wayu and Typhoon
both well-behaved, beside M1's one-sided split.
