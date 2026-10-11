# MODEL_SURVEY_M2 — results (Track E: Wayu's loops)

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** Calibration split only,
one run. Authorized by PELY334; approved by Up2mEz (Decision Log 2026-10-10b;
collab `20261010T0925Z_Up2mEz_to_PELY334_review-track-e-m1-m2-approved.md`).
That review arrived after the full run had finished and been scored. Its four
requests are the registration's Addendum 1, and §1 reports them.
Registration: `MODEL_SURVEY_M2_REGISTRATION.md` (with Addendum 1).

| | |
|---|---|
| run | `kaggle-model-survey-m2-edb6ce636dbd` (git `edb6ce6`). Kaggle 2×T4, fp16, torch `2.14.0+cu130`, transformers `5.12.0`, `use_cache` true: the same environment as M1's run |
| units | `R105` 178 items (0.90 h) and `CARD` 178 items (0.96 h), one T4 each; 0 failures; `not_run` empty. Resolved settings as registered: `CARD` has `do_sample` true, temperature 0.1, top_p 0.7, top_k 50, penalty 1.05, one seed per item |
| control | `kaggle-model-survey-m2-61c813afe487-control20` (git `61c813a`): `G0` on the first 20 calibration items. Result: `docs/stage0/data/M2_CONTROL_61c813afe487.json` (`scripts/model_survey_m2_control.py`) |
| session time | smoke 0.07 h, full run 0.99 h, control 0.16 h: ≈ 1.2 h in all, within the 3-hour cap |
| scores | `docs/stage0/data/M2_SCORES_edb6ce636dbd.json` (`scripts/model_survey_m2_analyze.py`, git `edb6ce6`, clean) |
| outputs | `docs/stage0/data/M2_OUTPUTS_edb6ce636dbd.json.gz`: `R105` and `CARD` outputs. No reference text, no image. `G` is in M1's archive |
| exploratory | `docs/stage0/data/M2_EXPLORATORY_edb6ce636dbd.json` (`scripts/model_survey_m2_exploratory.py`, git `0bcbd8f`, clean) |

## 1. Checks before reading

- **`G` reproduces M1.** Scored by the same code against this run's
  references:
  - `G` gives M1's Wayu cells exactly (mark F1 65.2 Full-page, 46.0 Text
    recognition);
  - Typhoon and base give T1's (94.9 / 81.7 and 41.0 / 24.3).
- **Control for `G` (Addendum 1 §1): passed.**
  - `G0` (penalty 1.0, run with M2's code) reproduced M1's `G` on 20 of 20
    items: 8 Full-page and 12 Text recognition. Text and generated-token count
    were the same on every item, including the 5 outputs that run to 3,072
    tokens.
  - So nothing in the code path or environment differs between the two runs
    in a way that changes an output on these items. The arm effects against
    `G` are read as registered.
- **Timing.** The scores below were computed, and seen, before Up2mEz's review
  arrived. The control's pass rule was written into Addendum 1 before the
  control ran.
- **Output-format audit (before the numbers were read).**
  - No HTML tag appears in any output of `R105`, `CARD` or `G`.
  - Each arm has one `GLYPH<…>` placeholder per task, as M1 found for Wayu.
  - Markdown is rare: per arm, `**bold**` in 5 Text recognition outputs and
    1 Full-page output, and one numbered list. `CARD` has one `$…$` span.
  - `extract_text` removes at most 12 non-space characters from any output
    (at most 55 per cell). Markup moves no number below.
  - Two Text recognition references contain tag-like printed text
    (`<Jonetz>`, `<heart>`). `extract_text` removes it from both sides, as
    in M1.

## 2. Primary outcome (§4)

Order-free v2 mark F1, recall and precision, and T1 scoring v2. All figures
are percentages. Typhoon and base are T1's `BENCHMARK_QUESTION` outputs; every
Wayu arm uses `OCR:`.

### Full-page OCR (69 items)

| arm | decoding | mark F1 | recall | precision | median CER | located | tone error¹ | truncated | repetitive | s/token |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Typhoon OCR 1.5 (T1) | greedy | **94.9** | 96.1 | 93.7 | 2.8 | 100 | 0.65 | 2.9 | 1.4 | 0.042 |
| base Qwen3-VL-2B (T1) | greedy | 41.0 | 65.0 | 29.9 | 27.1 | 91 | 9.41 | 43.5 | 36.2 | 0.041 |
| `G` (M1) | greedy, penalty 1.0 | 65.2 | 69.0 | 61.8 | 13.0 | 86 | 5.27 | 26.1 | 24.6 | 0.021 |
| `R105` | greedy, penalty 1.05 | 68.1 | 71.4 | 65.0 | 14.2 | 87 | 6.37 | 23.2 | 23.2 | 0.021 |
| `CARD` | the card's sampling | 65.2 | 71.3 | 60.1 | 14.6 | 88 | 6.50 | 23.2 | 23.2 | 0.022 |
| `G+B` | `G`, then T5b's stop | 76.0 | 65.7 | 90.1 | 13.0 | 86 | 4.89 | 8.7 | 7.2 | 0.021 |
| `R105+B` | `R105`, then the stop | **77.0** | 68.2 | 88.3 | 14.2 | 86 | 5.40 | 7.2 | 8.7 | 0.021 |
| `CARD+B` | `CARD`, then the stop | 76.9 | 67.8 | 88.9 | 14.6 | 84 | 4.14 | 5.8 | 5.8 | 0.022 |

### Text recognition (109 items)

| arm | decoding | mark F1 | recall | precision | median CER | located | tone error¹ | truncated | repetitive | s/token |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Typhoon OCR 1.5 (T1) | greedy | **81.7** | 82.9 | 80.6 | 5.0 | 91 | 0.60 | 0.9 | 0.9 | 0.065 |
| base Qwen3-VL-2B (T1) | greedy | 24.3 | 83.6 | 14.2 | 24.1 | 87 | 4.91 | 14.7 | 16.5 | 0.057 |
| `G` (M1) | greedy, penalty 1.0 | 46.0 | 83.8 | 31.7 | 8.5 | 83 | 2.63 | 20.2 | 20.2 | 0.024 |
| `R105` | greedy, penalty 1.05 | 34.7 | 86.0 | 21.8 | 8.1 | 86 | 2.58 | 12.8 | 13.8 | 0.024 |
| `CARD` | the card's sampling | 35.3 | 85.8 | 22.2 | 8.6 | 84 | 2.56 | 13.8 | 13.8 | 0.025 |
| `G+B` | `G`, then T5b's stop | **70.4** | 83.0 | 61.1 | 8.5 | 83 | 2.63 | 12.8 | 12.8 | 0.024 |
| `R105+B` | `R105`, then the stop | 70.3 | 85.0 | 60.0 | 8.1 | 86 | 2.58 | 5.5 | 6.4 | 0.024 |
| `CARD+B` | `CARD`, then the stop | 69.7 | 84.9 | 59.1 | 8.6 | 84 | 2.56 | 7.3 | 8.3 | 0.025 |

¹ Tone-mark error given a correctly read base consonant. Each arm's 95%
interval is in the scores file:

| arm | Full-page | Text recognition |
|---|---|---|
| `G` | 5.3 [3.1, 8.0] | 2.6 [1.3, 4.4] |
| `R105` | 6.4 [3.9, 9.4] | 2.6 [1.4, 4.2] |
| `CARD` | 6.5 [3.7, 10.3] | 2.6 [1.4, 4.2] |

No paired interval was registered for it.

### Paired differences against `G` (points, 95% item bootstrap, 2,000 resamples)

**Full-page OCR (69 items)**

| arm | Δ F1 | Δ recall | Δ precision |
|---|---|---|---|
| `R105` | +2.8 [−3.6, +9.6] | +2.4 [−3.2, +8.7] | +3.2 [−6.7, +15.4] |
| `CARD` | −0.0 [−10.7, +10.3] | +2.3 [−2.3, +7.6] | −1.7 [−20.0, +16.5] |
| `G+B` | **+10.8 [+5.3, +16.1]** | −3.3 [−6.6, −0.8] | **+28.3 [+14.0, +40.9]** |
| `R105+B` | **+11.8 [+4.6, +18.6]** | −0.8 [−7.2, +5.5] | **+26.5 [+12.5, +38.4]** |
| `CARD+B` | **+11.7 [+4.6, +18.6]** | −1.2 [−6.8, +4.9] | **+27.1 [+12.9, +39.1]** |

**Text recognition (109 items)**

| arm | Δ F1 | Δ recall | Δ precision |
|---|---|---|---|
| `R105` | −11.3 [−22.5, +4.5] | +2.2 [−0.3, +6.5] | −9.9 [−21.1, +4.1] |
| `CARD` | −10.7 [−22.1, +7.5] | +2.0 [−2.3, +7.1] | −9.5 [−20.1, +7.2] |
| `G+B` | **+24.4 [+10.7, +35.7]** | −0.8 [−1.9, −0.1] | **+29.4 [+13.8, +42.6]** |
| `R105+B` | **+24.3 [+10.7, +35.7]** | +1.2 [−1.6, +5.7] | **+28.3 [+13.2, +40.7]** |
| `CARD+B` | **+23.7 [+10.0, +34.9]** | +1.1 [−3.4, +6.4] | **+27.4 [+12.2, +39.4]** |

### Cost

- **Generated tokens and generation seconds** are summed over the task's
  items.
- **For `+B`, two estimates are given** (Addendum 1 §3):
  - **first copy**: scaled to the first copy the cut keeps. This is what the
    scores file reports; it is an upper bound on the saving.
  - **at detection**: scaled to the point where the 8th copy (6th for long
    units) completes, the earliest point a decode-time stop could fire.

| arm | Full-page tokens | seconds | reached max | Text rec. tokens | seconds | reached max |
|---|---:|---:|---:|---:|---:|---:|
| `G` | 97,152 | 1,966 | 18 | 84,158 | 1,752 | 22 |
| `R105` | 93,167 | 1,918 | 16 | 60,372 | 1,287 | 14 |
| `CARD` | 93,853 | 2,008 | 16 | 63,328 | 1,395 | 15 |
| `G+B`, first copy / at detection | 63,861 / 64,511 | 1,303 | 6 | 59,857 / 60,725 | 1,263 | 14 |
| `R105+B`, first copy / at detection | 63,511 / 64,561 | 1,318 | 5 | 36,534 / 37,389 | 806 | 6 |
| `CARD+B`, first copy / at detection | 59,951 / 60,951 | 1,295 | 4 | 42,441 / 43,329 | 956 | 8 |

The stop's saving on `G` is 34% of Full-page tokens and 29% of Text
recognition tokens as reported. At detection it is 34% and 28%.

## 3. Reading against the registered patterns (§5)

- **"`R105` or `CARD`: truncation falls and F1 rises, recall not lower, tone
  error not higher" — does not hold.**
  - Full-page: truncation hardly moves (18 → 16 of 69 outputs), and F1 does
    not rise: +2.8 [−3.6, +9.6] for `R105`, −0.0 [−10.7, +10.3] for `CARD`.
  - Text recognition: truncation falls (22 → 14 and 15 of 109), but F1 does
    not rise either. Its point estimate falls by 11 points, with intervals
    that include 0 (§4a says why).
  - So the card's decoding does not fix Wayu's loops.
- **"Truncation falls but recall falls or tone error rises" — not supported
  either.**
  - Recall does not fall: +2.0 to +2.4 points, every interval including 0.
  - The tone error is unchanged on Text recognition (2.6%). On Full-page it is
    1.1 to 1.2 points higher (5.3% → 6.4% and 6.5%), but the arms' intervals
    overlap almost entirely and no paired interval was registered.
  - Unlike T5's penalty of 1.1 on Typhoon, 1.05 shows no measurable mark cost
    here. It also buys little loop control.
- **"`CARD` ≈ `R105`" — holds, on one draw.**
  - Against `G`, the two differ by at most 3 points on either task.
  - Paired directly, `CARD` − `R105` is −2.8 [−13.2, +7.1] on Full-page and
    +0.6 [−10.6, +14.3] on Text recognition. With the stop it is −0.1
    [−3.0, +2.5] and −0.6 [−2.5, +0.9] (exploratory, §4c).
  - `CARD` does not look better than `R105`, so no further seeds were run
    (Addendum 1 §4). Sampling at temperature 0.1 adds nothing over the penalty
    alone.
- **"`G+B` raises precision and F1, recall ≈ `G`" — F1 and precision rise; the
  recall clause holds only once a metric artefact is set aside.**
  - F1 rises by +10.8 (Full-page) and +24.4 (Text recognition), precision by
    +28 to +29; every interval excludes 0.
  - On the registered numbers, recall is 3.3 points lower on Full-page
    [−6.6, −0.8] and 0.8 points lower on Text recognition [−1.9, −0.1].
  - §4b shows why. That recall is credit the metric gave to repeated copies
    of a unit that never occurs in the reference, inside outputs that had
    run to `max_new_tokens`. The stop removes those repeats, and with them
    the credit. No cut fell on an output that had ended normally.
  - With that accounted for, the registered reading stands: what loops cost
    Wayu is surplus text. What they leave unread is recall that no stop
    returns (§4d).
- **"The best arm still entirely below Typhoon on both tasks" — holds: loops
  do not explain Wayu's gap to Typhoon.**
  - Full-page: the best arm, `R105+B`, is −17.9 [−25.0, −11.0] below
    Typhoon.
  - Text recognition: the best arm, `G+B`, is −11.3 [−21.3, −1.2].
  - The stop closes about 11 of the 30 F1 points on Full-page and 24 of the
    36 on Text recognition. The rest remains.

**In one sentence:** the decoding Wayu's model card recommends does not fix
its loops. A decode-time stop recovers most of what they cost: +11 mark F1 on
full pages and +24 on text recognition. It also saves about a third of the
tokens on full pages and over a quarter on text recognition. Even so, Wayu
stays clearly below Typhoon.

## 4. Exploratory readings (not registered; `M2_EXPLORATORY_edb6ce636dbd.json`)

### 4a. Why the penalty cuts Text recognition loops but lowers precision

Under the penalty, the loops that remain repeat Thai words rather than
digits:

| outputs reaching `max_new_tokens` | `G` | `R105` | `CARD` |
|---|---:|---:|---:|
| number (Text recognition) | 22 | 14 | 15 |
| of which an exact repeat of a unit with letters (T5b's rule) | 8 | 8 | 7 |
| output marks they carry | 4,633 | 8,886 | 8,545 |
| share of all output marks | 51% | 65% | 64% |

Here are two of the five items that drive the change.

- **829EE6D4:**
  - Under `G` it loops on `100-0900`, which carries no marks.
  - Under `R105` it loops on a Thai phrase, `…การทำงานที่ทำให้เกิดขึ้นใน…`:
    output marks 14 → 1,781.
- **1B33F2CB:**
  - Under `G` it ends normally.
  - Under `R105` it runs to `max_new_tokens`.

A loop of digits costs mark precision nothing, while a loop of Thai words costs
it heavily. The pooled precision therefore falls although fewer outputs loop.

The mechanism is an inference, not tested here. `transformers`' repetition
penalty acts once per distinct token already generated. Once a loop is under
way, every token in it is already penalized, so the penalty can change which
loop starts but does not end one.

### 4b. What the stop removes (Addendum 1 §2): no false cut

| | `G+B` | `R105+B` | `CARD+B` |
|---|---:|---:|---:|
| cuts, Full-page / Text recognition | 12 / 8 | 11 / 8 | 12 / 7 |
| … on an output that had ended normally | 0 / 0 | 0 / 0 | 0 / 0 |
| … whose run is not a runaway to the end | 0 / 0 | 0 / 0 | 1 / 0 |
| … whose repeated unit occurs in the reference | 0 / 0 | 0 / 0 | 0 / 0 |
| reference marks credited inside the removed text, Full-page / Text rec. | 538 / 27 | 515 / 35 | 567 / 30 |

- **Every cut is on an output that had reached `max_new_tokens`.** Every
  cut item is listed in the file (`cut_items`). In 57 of the 58 cuts the run
  continues to the end of the output.
- **The one exception (`CARD`, 39311352) drops no reading.**
  - It repeats `Lotus's 2007` 161 times, then drifts by one letter to
    `Locus's 2007` and repeats that to the end.
  - The text after the run is that second loop. It holds no Thai mark, and no
    mark credit is lost.
- **Removed credit equals the recall drop.** The credited marks removed are
  exactly the recall `G+B` loses: 538 of 16,266 Full-page reference marks
  (3.3 points) and 27 of 3,447 Text recognition marks (0.8 points).
- **That credit is for repeats, not reading.** None of the repeated units
  occurs in the reference. An example is 33067A35, where `" วันที่ ๒"`
  appears 434 times.
  - The order-free metric's residual global alignment lines the copies up
    with the same syllables across the reference: `ที่` and `วัน` occur
    everywhere.
  - That gives 207 of 413 reference marks on 33067A35 to text the model only
    repeated.
- **This is a property of the metric, and it reaches beyond M2.** It
  inflates the recall of any output that loops on common syllables. That
  includes T1's base and M1's new models. It is not corrected anywhere in
  these results, which are as registered.

### 4c. Does the penalty, or sampling, add anything once loops are stopped? No

| pair | Full-page Δ F1 | Text recognition Δ F1 |
|---|---|---|
| `R105+B` − `G+B` | +1.0 [−2.7, +5.1] | −0.1 [−1.9, +2.4] |
| `CARD+B` − `G+B` | +0.9 [−1.9, +4.8] | −0.7 [−3.3, +2.2] |
| `CARD+B` − `R105+B` | −0.1 [−3.0, +2.5] | −0.6 [−2.5, +0.9] |

Greedy decoding with the stop is as good as either of the card's settings with
the stop.

### 4d. What the stop cannot return: pages Wayu never finished reading

On Full-page, `G+B` against Typhoon, split by whether `G` had looped:

| pages | n | share of reference marks | Typhoon recall | `G+B` recall | `G+B` F1 vs Typhoon |
|---|---:|---:|---:|---:|---|
| `G` looped | 18 | 30% | 92.7 | **19.2** | 31.1 vs 87.6, −56.5 [−76.7, −35.2] |
| `G` did not loop | 51 | 70% | 97.6 | 85.5 | 88.1 vs 98.2, −10.0 [−16.0, −4.7] |

- **Most of the gap sits on the looped pages.** On the 18 pages where it
  loops, Wayu reads about a fifth of the marks before the loop starts.
  Those pages hold 72% of its Full-page recall gap to Typhoon: 3,566 of
  4,942 marks.
- **Where it does not loop, Wayu is still behind.** Typhoon is 10 points
  ahead on F1, as in M1 §4.
- `R105+B` and `CARD+B` give the same picture: about 68% and 70% of the gap
  sits on the pages they looped on.

### 4e. Text recognition: the symmetric subset (the review's request)

| subset, Wayu − Typhoon | n | Typhoon F1 | Wayu F1 | Δ F1 | Δ precision |
|---|---:|---:|---:|---|---|
| M1's one-sided split, `G` (Wayu ≈ reference length, no loop on either side) | 59 | 94.5 | 94.9 | +0.4 [−1.6, +3.0] | — |
| **symmetric**: both ≈ reference length, neither loops, `G` | 55 | 96.0 | 95.1 | −0.9 [−2.5, +0.7] | −3.0 [−5.2, −1.2] |
| symmetric, `R105` | 58 | 96.1 | 95.0 | −1.1 [−2.5, +0.4] | −2.8 [−4.7, −1.1] |
| symmetric, `CARD` | 57 | 96.3 | 95.4 | −0.9 [−2.3, +0.8] | −2.6 [−4.6, −0.9] |
| symmetric, `G+B` | 63 | 95.0 | 92.6 | −2.4 [−4.8, −0.2] | −3.3 [−5.9, −1.1] |

- **On the symmetric subset, Wayu reads Text recognition marks about one point
  below Typhoon**, not equal to it. Its precision is about 3 points lower.
- **The `+B` rows are lower still.** A cut output that stops short of
  1.5 × the reference length enters the subset with only its first copy.
- The registered secondary split by length (`text_recognition_by_length` in
  the scores file) gives the one-sided picture, per arm, as in M1.

## 5. Limits

- **The run, and its claim level.** One run, on the calibration split only;
  `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.
- **The review came late.** It arrived after the scores were computed. The
  control was run afterwards, with its pass rule fixed first.
- **The control is partial.** It checks 20 of the 178 items. `G` is still
  M1's output.
- **One sampling draw.** `CARD` has one seed per item, so its readings carry
  the one-draw caveat.
- **`+B` is estimated, not run.** It is an offline cut, and its tokens and
  seconds are scaled by characters. The reported saving is an upper bound;
  the at-detection estimate is beside it.
- **Tone error has per-arm intervals only.** No paired interval was
  registered for it.
- **The metric credits repeats.** The order-free metric gives recall credit
  to repeated copies of a loop's unit (§4b). Every recall figure for a
  looping output is a little high, for every model. The F1 is less affected,
  because precision charges the repeats.
- **Out of scope here:** Wayu's `BENCHMARK_QUESTION`, other penalties or
  temperatures, and layout pipelines.

## 6. What this suggests (proposals only; none is authorized)

1. **For any further Wayu work, use greedy decoding with T5b's stop.** The
   card's decoding does not end its loops, and it adds nothing once they are
   stopped.
2. **The Full-page gap is now mostly unread text on pages where Wayu loops.**
   Returning that text needs reading past the loop, for instance by
   continuing region by region after a stop. A better stop will not do it.
   - The region-OCR rounds that would hold this are Up2mEz's.
   - Any such test is a new registration.
3. **A note for the order-free metric's owner.** The residual alignment
   credits repeated copies of a looping unit (§4b).
   - Scoring every model's outputs after T5b's stop would remove that credit.
   - Whether to do so is the metric owner's decision.
4. **The re-reader idea (plan step 5) is not strengthened.** On the symmetric
   subset Wayu reads about one point below Typhoon (§4e). A re-reader has to
   be right where Typhoon is wrong. That needs its own test, registered on
   held-out items, as Up2mEz asked.
