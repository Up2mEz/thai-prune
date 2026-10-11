# MODEL_SURVEY_M4 — results (Track E: does Wayu know when it is reading?)

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** Calibration split only,
one scoring pass. **Authorized by PELY334; Up2mEz's review was pending when
these results were produced** (PR #74; Decision Log 2026-10-11b not merged).
Registration: `MODEL_SURVEY_M4_REGISTRATION.md`.

| | |
|---|---|
| run | `kaggle-model-survey-m4-a9aad7aa31d8` (git `a9aad7a`), Kaggle 2×T4, fp16, torch `2.14.0+cu130`, transformers `5.12.0`. A teacher-forced scoring pass over M3's 178 outputs, taken from the committed archive (`M3_OUTPUTS_e970f61dc74c.json.gz`, hash checked by the worker). Nothing is generated |
| units | two position shards of 89 items (104 s and 106 s); 0 failures |
| session time | smoke 0.04 h, full pass 0.06 h, within the 1-hour cap |
| scores | `docs/stage0/data/M4_SCORES_a9aad7aa31d8.json` (`scripts/model_survey_m4_analyze.py`, git `a9aad7a`, clean): no reference text, and no output text beyond counts |

## 1. Checks before reading

- **The scoring path holds.** On ordinary text (138 outputs with no escape that
  ended before the token limit, 58,264 tokens), the teacher-forced argmax
  equals the output token at **99.7%** of positions; the registered floor was
  98%. All 178 outputs re-tokenize to exactly their text.
- **The threshold was fixed without labels.** τ = −0.183 is the 10th
  percentile of `s_mean` over the 2,601 windows of ordinary text. The analysis
  computes it from those windows alone, before any label is used.
- **Markup.** M4 writes no text. Its windows are M3's `E` outputs, which M3
  audited: no HTML anywhere, and no Markdown in the text written after an
  escape.

## 2. Primary outcome (§4)

### Does confidence separate read from invented text? (Full-page)

The windows are those written after an escape, labelled against the reference.
There are 130 of them on 10 pages: 46 `read` and 84 `invented`. The other 168
windows are letterless and unlabelled; two escaped pages have only such
windows.

| score | AUROC, 95% interval from resampling pages |
|---|---|
| **`s_mean`** (primary) | **0.92 [0.81, 0.98]** |
| `s_min` (E1's) | 0.92 [0.82, 0.99] |
| `s_ent` | 0.84 [0.60, 0.94] |

### What the filter keeps (τ from ordinary text)

| window label | windows | kept |
|---|---:|---:|
| `read` | 46 | **32 (70%)** |
| `invented` | 84 | **6 (7%)** |
| no letter | 168 | 166 (99%) |

### Effect on the registered metrics (paired, 95% item bootstrap)

| task, items | pair | Δ F1 | Δ recall | Δ precision | Δ matched lines |
|---|---|---|---|---|---|
| **Full-page, all 69** | **`E_F` − `E0`** | **+0.5 [−0.3, +1.6]** | +1.0 [−0.1, +2.6] | −0.4 [−1.1, +0.0] | +9 [+0, +26] |
| Full-page, all 69 | `E_F` − `E` | −0.1 [−0.7, +0.4] | −1.3 [−2.4, −0.4] | +2.1 [+0.5, +4.6] | −14 [−28, −3] |
| Full-page, all 69 | `E` − `E0` (M3) | +0.5 [−0.6, +2.0] | +2.3 [+0.7, +4.2] | −2.6 [−5.6, −0.5] | +23 [+5, +47] |
| Full-page, 12 escaped | `E_F` − `E0` | +5.2 [−1.0, +14.8] | +4.2 [−0.4, +12.5] | −2.7 [−10.8, +5.1] | +9 [+0, +26] |
| Text recognition, all 109 | `E_F` − `E0` | −0.5 [−1.2, +0.0] | +0.1 [+0.0, +0.4] | −0.8 [−2.1, +0.0] | +0 [+0, +0] |
| Text recognition, all 109 | `E_F` − `E` | +1.5 [+0.3, +3.2] | −0.8 [−1.7, −0.2] | +2.6 [+0.5, +5.6] | −1 [−3, +0] |

**Against Typhoon (Full-page):** `E_F` is −18.4 [−26.5, −11.4], against −18.8
for the stop alone.

**Mark accounting (Full-page).**

- Without the filter, the escape added 769 output marks to the stop-only
  output, of which 368 were correct (48%).
- After the filter it adds 231, of which 155 are correct (67%).

**Mark accounting (Text recognition).** Without the filter, the escape added
323 output marks, 30 of them correct. After the filter it adds 66, of which
4 are correct.

### Page by page (Full-page, escaped; descriptive)

| page | matched lines `E0` / `E` / `E_F` | correct marks `E0` / `E` / `E_F` | read windows kept | invented windows kept |
|---|---|---|---|---|
| F096D392 | 0 / 9 / **8** | 0 / 103 / **95** | 17 of 17 | 0 of 1 |
| 85252C85 | 2 / 3 / 3 | 158 / 222 / 212 | 9 of 11 | 0 of 1 |
| AF432B6A | 0 / 5 / 0 | 20 / 54 / 5 | 2 of 9 | 0 of 25 |
| 0159AF30 | 8 / 11 / 8 | 115 / 136 / 112 | 3 of 6 | 3 of 23 |
| 5300A462 | 3 / 6 / 3 | 85 / 97 / 85 | — | 0 of 6 |
| A2A35822 | 0 / 1 / 0 | 1 / 86 / 22 | 1 of 2 | 2 of 12 |
| 8F33EBB9 | 13 / 14 / 13 | 134 / 134 / 129 | 0 of 1 | 0 of 1 |
| 33067A35 | 2 / 2 / 2 | 5 / 26 / 13 | — | 1 of 4 |
| BEA7A53F | 0 / 0 / 0 | 15 / 31 / 15 | — | 0 of 6 |
| 9BBB9DB3 | 0 / 0 / 0 | 1 / 14 / 1 | — | 0 of 5 |
| 28987CC6, B2DEDBA0 | unchanged | unchanged | letterless windows only | — |

On 5300A462, `E` gained three lines although each of its six windows is
labelled `invented`: a reference line can be located across window boundaries.
The window labels are an approximation of reading.

## 3. Reading against the registered patterns (§5)

- **Registered row 2 applies.** The AUROC interval is above 0.5, but the
  `E_F` − `E0` F1 interval includes 0. The row reads "the signal exists but is
  too weak for this filter."
- **Only half of that wording fits:**
  - **The signal is not weak.** The AUROC is 0.92.
  - **The filter does what it was built to do.** It drops 93% of invented
    windows and keeps 70% of read ones.
    - The escape's precision cost almost disappears on Full-page: −2.6
      becomes −0.4.
    - On Text recognition, −2.0 F1 becomes −0.5.
  - **What is small is the reading there was to recover.**
    - The escape added +2.3 recall across 69 pages, and the filter keeps less
      than half of it (+1.0).
    - What it keeps is mostly the one page read in full: F096D392, 8 of 9
      lines.
- **The best arm against Typhoon** is still entirely below 0 (−18.4).

**In one sentence:** Wayu knows when it is inventing. Its own confidence
separates invented from read text after an escape (AUROC 0.92), and a filter
built on it removes almost all of the escape's damage. But the escape recovers
so little reading that, filtered or not, it does not move Wayu's mark F1
measurably, and Wayu stays 18 points below Typhoon.

## 4. Limits

- **The run, and the review.** One pass, on the calibration split only.
  Up2mEz's review was pending at the time of writing.
- **Few pages carry the labels.**
  - 10 pages carry them, and five dominate: AF432B6A (34 windows), 0159AF30
    (29), F096D392 (18), A2A35822 (14) and 85252C85 (12).
  - The interval resamples pages, not windows.
- **Labels are approximate.**
  - A 20-character window located at CER < 0.4 can match by chance; one
    `read` window in 0159AF30 sits at CER 0.38.
  - Chance matches would, if anything, lower the AUROC.
- **Calibration data only.** The threshold was fixed without labels, but M3
  and M4 were designed on the calibration items. A claim would need data not
  used here, and the locked split is a decision for both researchers.
- **Letterless windows (digit loops) are confident and kept.** They cost no
  marks, but they add surplus text.

## 5. What this suggests (proposals only; none is authorized)

1. **The finding: M4 extends E1 to a second model and a second kind of
   error.** A model's own confidence flags its unreliable text: Typhoon's mark
   errors (E1, AUROC 0.94–0.95) and Wayu's invented text after an escape
   (AUROC 0.92).
2. **The loop line ends here for Wayu.** On this data, stop, escape and
   filter together do not change Wayu's mark F1. Its gap to Typhoon (about 18
   points on full pages) is in reading, not in loops. No further Wayu decoding
   work is proposed.
3. **Where the signal could be used.** It is where E1 already pointed for
   Typhoon: flagging text for a second reading. Any held-out test needs both
   researchers, because the locked split is closed.
