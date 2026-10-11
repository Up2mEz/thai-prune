# MODEL_SURVEY_M4 — registration (Track E: does Wayu know when it is reading?)

**Status: `APPROVED` by PELY334.** In session on 2026-10-11, PELY334 replied
"ได้ลองทำเลย" ("go ahead and try it") to the proposal in
`MODEL_SURVEY_M3_RESULTS.md` §6.2.

- **Process.** The same as M1–M3: run first, Up2mEz reviews afterwards. The
  Decision Log entry (2026-10-11b) stays unmerged until Up2mEz approves it.
- **No outputs yet.** This registration was written before any M4 score
  existed. The only outputs so far are local engineering checks on synthetic
  images (§8).
- **Parameters:** `configs/model_survey/m4.yaml`.
- **Claim level of every result:** `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

**Question.** M3's loop escape reads some of what Wayu's loops left unread. On
Full-page it gained 23 matched reference lines, and one page was read in full.
But it also writes fluent text that is not on the page, so mark F1 does not
move.

Can Wayu's own confidence in the text it wrote after an escape tell the two
apart? If it can, a filter keeps the reading and drops the invention. If it
cannot, invented text is as confident as read text, and no decode-time remedy
built on Wayu's own signals will fix its loops.

## 1. Inputs

- **Text.** M3's `E` outputs, all 178 calibration items, from the committed
  archive `docs/stage0/data/M3_OUTPUTS_e970f61dc74c.json.gz`. The worker
  checks its hash.
- **Model.** The same model, prompt, image policy and runtime as M1–M3: Wayu
  `af0204b4`, `OCR:`, fp16 with fp32 fallback, `sdpa`, Kaggle T4.
- **No new text.** Nothing is generated. The locked split is never touched,
  and images are never written.

## 2. Scores (`model_survey.remote_m4`)

For each item there is one forward pass over prompt, image, and `E`'s output
re-tokenized (canonical tokenization, with character offsets). Per token:

- the log-probability of the output token;
- the entropy of the distribution, from an fp32 log-softmax;
- whether the token is the argmax.

**Check before any reading.** On ordinary outputs, the argmax must agree with
the output token at ≥ 98% of tokens. Ordinary outputs are those with no
escape that ended before `max_new_tokens`; they are greedy's own text. If the
agreement is lower, the scoring path is investigated before anything is read.

## 3. Units, labels, filter (`model_survey.m4`, offline)

**Windows.** Wayu's outputs have no line breaks. So whitespace-separated
phrases are merged left to right into windows of at least 20 non-space
characters. A short remainder joins the window before it.

A window has three scores, taken over the tokens that overlap it:

- `s_mean`, the mean log-probability (the primary score);
- `s_min`, the lowest log-probability (E1's score);
- `s_ent`, the mean entropy.

**Labels (Full-page only).** A window with a letter is `read` if its text can
be located in the page's reference at CER < 0.4: the window is aligned whole
against the reference's best-matching stretch. Otherwise it is `invented`.

Text recognition is not labelled. There the reference is often one part of an
image that Wayu transcribes whole, so text missing from the reference need not
be invented.

**Filter, fixed without labels.**

- **Threshold.** τ is the 10th percentile of `s_mean` over the windows of
  ordinary outputs: the bottom tenth of Wayu's ordinary text.
- **Rule.** In an escaped output, every window after the greedy prefix that
  scores below τ is dropped. The greedy prefix is never changed.
- **Result.** This gives the arm `E_F`.

## 4. Outcomes

**Primary (Full-page).**

- **Signal.** The AUROC of `s_mean` for `read` against `invented` windows
  written after an escape, with a 95% interval from 2,000 resamples of items
  (seed 20261011).
- **Effect.** `E_F` − `E0` and `E_F` − `E`: paired differences in mark F1,
  recall, precision and matched reference lines. These are reported on all
  items and on the escaped items, scored as in M1–M3.

**Secondary.**

- the AUROC of `s_min` and of `s_ent` (lower entropy counts as more
  confident);
- the filter's keep rates for `read` and `invented` windows;
- the same effects on Text recognition, unlabelled;
- `E_F` − Typhoon.

## 5. What each pattern would mean, stated in advance (Full-page)

| pattern | reading |
|---|---|
| AUROC interval above 0.5, and `E_F` − `E0` F1 interval above 0 | Wayu's confidence separates read from invented text after an escape. A confidence-filtered escape keeps reading and drops most invention. It becomes a candidate for a held-out test, which needs both researchers, since the locked split is closed |
| AUROC interval above 0.5, but `E_F` − `E0` F1 interval includes 0 | the signal exists but is too weak for this filter |
| AUROC interval includes 0.5 | invented text is as confident as read text. Wayu's own signals cannot clean up its escapes |

The comparison is descriptive; there is no gate. With only 12 escaped
Full-page items, the intervals will be wide, and the results say so.

## 6. Budget, smoke

- **Cost.** One forward pass per item, about 1 to 12 seconds each on a T4.
  With two position shards, each takes a few minutes.
- **Cap:** 1 T4-hour, PELY334's quota.
- **Smoke first:** `--smoke 2`.

## 7. Not in scope

- new generation, or any new escape;
- any change to the threshold rule after scores exist;
- other models;
- the locked split;
- any change to the order-free metric.

## 8. Engineering checks before this registration was frozen (synthetic images; not results)

Local RTX 3060, transformers 5.12.0:

- **Tokenizer.** Wayu's tokenizer is a fast `LlamaTokenizer` with character
  offsets. Re-tokenizing a greedy output reproduced its 600 generated ids
  exactly.
- **Teacher-forced scoring.** A forward pass with the output appended
  (`model_survey.escape.extend_inputs`) gives an argmax equal to the
  generated token at 600 of 600 positions.
- **A long, looping output.** On a 3,072-token output,
  `remote_m4.teacher_forced` agrees at every token and takes 11.5 s, with a
  peak of 4.6 GiB.
- **An early warning.** On that looping synthetic page, the repeated text
  scores about −0.002 per token: Wayu is most confident while looping.
  Whether invented text after an escape is as confident is the question M4
  asks.
