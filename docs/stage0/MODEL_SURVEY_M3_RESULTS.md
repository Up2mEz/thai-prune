# MODEL_SURVEY_M3 — results (Track E: can Wayu read past its loops?)

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** Calibration split only,
one run. **Authorized by PELY334; Up2mEz's review was pending when these
results were produced** (PR #71; Decision Log 2026-10-11 not merged).
Registration: `MODEL_SURVEY_M3_REGISTRATION.md`, with Addendum 1 (written after
the first smoke and before the full run).

| | |
|---|---|
| run | `kaggle-model-survey-m3-e970f61dc74c` (git `e970f61`), Kaggle 2×T4, fp16, torch `2.14.0+cu130`, transformers `5.12.0`, `use_cache` true: M1's and M2's environment |
| units | two position shards of 89 items each (0.52 h and 0.45 h); 0 failures; `not_run` empty. Greedy decoding with penalty 1.0, resolved as registered |
| session time | smoke 1: 0.09 h; smoke 2: 0.06 h; full run: 0.56 h. ≈ 0.7 h in all, within the 3-hour cap |
| scores | `docs/stage0/data/M3_SCORES_e970f61dc74c.json` (`scripts/model_survey_m3_analyze.py`, git `8ddd61b`, clean). It is identical to an earlier pass at `e970f61`, before the per-item list was added |
| outputs | `docs/stage0/data/M3_OUTPUTS_e970f61dc74c.json.gz`: `E`'s outputs with their escape records. No reference text, no image |

## 1. Checks before reading

- **Built-in control: passed.**
  - **No escape:** 158 outputs had none, and every one equals M1's `G`, text
    and token count.
  - **Escaped:** 20 outputs had escapes. In every one, the greedy prefix is a
    prefix of `G`'s output.
  - **The twin is M2's stop.** `E0` gives `G+B`'s numbers exactly, in every
    cell, with a paired difference of 0.0.
- **Output-format audit, done before reading the numbers.**
  - No HTML tag appears in any output of `E` (or `G`), and the Markdown is
    `G`'s.
  - The text written after the escapes, on 20 items, holds no tag and no
    Markdown.
  - `extract_text` removes at most 12 non-space characters from any output.
- **What changed after the smoke (Addendum 1).** The first smoke showed the
  model evading the escape by numbering its copies (`5) …`, `6) …`). The
  post-escape watch was then made to collapse digit runs. That change was
  made before the full run; nothing else changed.

## 2. Primary outcome (§4)

All figures are percentages, except matched lines: reference lines located at
CER < 0.4, a count. Typhoon and base are T1's `BENCHMARK_QUESTION` outputs;
every Wayu arm uses `OCR:`.

### Full-page OCR (69 items)

| arm | mark F1 | recall | precision | matched lines | median CER | tone error | truncated | repetitive | s/token |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Typhoon OCR 1.5 (T1) | **94.9** | 96.1 | 93.7 | 938 | 2.8 | 0.65 | 2.9 | 1.4 | 0.042 |
| base Qwen3-VL-2B (T1) | 41.0 | 65.0 | 29.9 | 565 | 27.1 | 9.41 | 43.5 | 36.2 | 0.041 |
| `G` (M1, greedy) | 65.2 | 69.0 | 61.8 | 653 | 13.0 | 5.27 | 26.1 | 24.6 | 0.021 |
| `G+B` (M2's stop) | 76.0 | 65.7 | 90.1 | 653 | 13.0 | 4.89 | 8.7 | 7.2 | 0.021 |
| `E0` (stop-only twin) | 76.0 | 65.7 | 90.1 | 653 | 13.0 | 4.89 | 8.7 | 7.2 | 0.022 |
| **`E` (escape)** | **76.5** | 68.0 | 87.6 | **676** | 11.5 | 5.96 | 13.0 | 17.4 | 0.022 |

### Text recognition (109 items)

| arm | mark F1 | recall | precision | matched lines | median CER | tone error | truncated | repetitive | s/token |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Typhoon OCR 1.5 (T1) | **81.7** | 82.9 | 80.6 | 223 | 5.0 | 0.60 | 0.9 | 0.9 | 0.065 |
| base Qwen3-VL-2B (T1) | 24.3 | 83.6 | 14.2 | 208 | 24.1 | 4.91 | 14.7 | 16.5 | 0.057 |
| `G` (M1, greedy) | 46.0 | 83.8 | 31.7 | 221 | 8.5 | 2.63 | 20.2 | 20.2 | 0.024 |
| `G+B` / `E0` | 70.4 | 83.0 | 61.1 | 221 | 8.5 | 2.63 | 12.8 | 12.8 | 0.024 |
| **`E` (escape)** | 68.4 | 83.9 | 57.8 | 222 | 8.5 | 2.71 | 12.8 | 16.5 | 0.025 |

### `E` − `E0` (paired, 95% item bootstrap, 2,000 resamples)

| task | items | Δ F1 | Δ recall | Δ precision | Δ matched lines |
|---|---|---|---|---|---|
| **Full-page** | all 69 | +0.5 [−0.6, +2.0] | **+2.3 [+0.7, +4.2]** | **−2.6 [−5.6, −0.5]** | **+23 [+5, +47]** |
| Full-page | 12 escaped | **+9.8 [+2.8, +20.4]** | +9.9 [+4.5, +18.2] | −15.3 [−30.7, −1.3] | +23 [+7, +44] |
| Text recognition | all 109 | **−2.0 [−4.3, −0.4]** | +0.9 [+0.2, +2.0] | −3.3 [−7.4, −0.7] | +1 [+0, +3] |
| Text recognition | 8 escaped | −0.1 [−7.9, +10.0] | +28.8 [+12.8, +47.8] | −18.5 [−31.9, −9.1] | +1 [+0, +3] |

### Secondary: against Typhoon

| task | `E` − Typhoon | `E0` − Typhoon |
|---|---|---|
| Full-page | −18.3 [−26.1, −11.6] | −18.8 [−27.3, −11.7] |
| Text recognition | −13.3 [−23.8, −2.2] | −11.3 [−21.9, −0.7] |

### Cost and escapes

| | Full-page | Text recognition |
|---|---|---|
| items escaped | 12 of 69 | 8 of 109 |
| escapes in all | 61 | 44 |
| final cuts (escapes used up) | 6 | 5 |
| step-cap hits | 0 | 0 |
| `E`: decoded tokens (kept) | 81,347 (74,067) | 70,418 (61,421) |
| `G`: tokens | 97,152 | 84,158 |
| `G+B` at detection (M2) | 64,511 | 60,725 |
| generation seconds, `E` / `G` | 1,842 / 1,966 | 1,602 / 1,752 |

The escape costs less than plain greedy decoding, which loops on to the token
limit, and 16–26% more than stopping.

## 3. Reading against the registered patterns (§5)

- **Full-page: "recall and matched lines rise, but F1 does not (precision
  falls)" — this row holds.**
  - Recall rises by +2.3 [+0.7, +4.2], which is about 370 of the 16,266
    reference marks.
  - Matched lines rise by +23 [+5, +47].
  - F1 does not move: +0.5 [−0.6, +2.0]. Precision falls by −2.6
    [−5.6, −0.5].
  - **Reading:** the escape reads some of what the loop left unread, but it
    also adds text that is not on the page. A filter would be needed before any
    use.
- **"`E` − Typhoon still entirely below 0" — holds.** `E` − Typhoon is −18.3
  [−26.1, −11.6], against −18.8 for the stop alone. Even with the escape, Wayu
  stays below Typhoon on full pages.
- **Text recognition (secondary): the escape costs F1,** −2.0 [−4.3, −0.4].
  It adds 1 matched line in total; the rest is surplus text.

**In one sentence:** decoding past a loop does recover real text on some pages.
On full pages it located 23 more reference lines, and on one page all of them.
On other pages the model writes fluent Thai that is not on the page. So mark F1
does not move, and Wayu stays 18 points below Typhoon.

## 4. Item by item (descriptive; `escaped_item_details` in the scores file)

The 12 Full-page pages with escapes:

| page | escapes | final cut | matched lines `E0` → `E` | correct marks `E0` → `E` | output marks `E0` → `E` |
|---|---:|---|---|---|---|
| F096D392 | 4 | no | **0 → 9 of 9** | **0 → 103 of 104** | 0 → 104 |
| AF432B6A | 2 | no (token limit) | 0 → 5 of 29 | 20 → 54 of 453 | 29 → 192 |
| 0159AF30 | 8 | yes | 8 → 11 of 90 | 115 → 136 of 509 | 141 → 286 |
| 5300A462 | 8 | yes | 3 → 6 of 37 | 85 → 97 of 164 | 85 → 115 |
| 85252C85 | 4 | no | 2 → 3 of 3 | 158 → 222 of 345 | 204 → 312 |
| 8F33EBB9 | 1 | no (token limit) | 13 → 14 of 32 | 134 → 134 of 275 | 147 → 156 |
| A2A35822 | 8 | yes | 0 → 1 of 29 | 1 → 86 of 610 | 1 → 116 |
| 33067A35 | 8 | yes | 2 → 2 of 11 | 5 → 26 of 413 | 6 → 28 |
| BEA7A53F | 8 | yes | 0 → 0 of 21 | 15 → 31 of 215 | 17 → 68 |
| 9BBB9DB3 | 8 | yes | 0 → 0 of 48 | 1 → 14 of 491 | 1 → 23 |
| 28987CC6 | 1 | no (token limit) | 1 → 1 of 3 | 1 → 1 of 2 | 1 → 1 |
| B2DEDBA0 | 1 | no | 13 → 13 of 21 | 98 → 97 of 140 | 169 → 169 |

**Real reading on 7 of the 12 pages.**

- Each of the top seven pages gained at least one reference line.
- **F096D392 is the clear case.** Greedy decoding looped from the first
  characters (`Q DMG Q DMG …`). After four escapes, Wayu read the whole page:
  9 of 9 lines, and 103 of 104 marks correct.
- A line located at CER < 0.4 is not a chance match. Lines this long sit at a
  median CER of 0.63–0.74 against other pages' outputs
  (`ORDER_FREE_MARK_METRIC_DRAFT.md` §2).

**No reading on the other 5.**

- 33067A35 repeats near-copies of a date (`วันที่ ๒ ๕ ธันวรรค ๒๕๕๔ …`).
- BEA7A53F and 9BBB9DB3 write fluent or near-copied text that is not on the
  page. These pages gain mark credit (+21, +16, +13) with no line. That is the
  alignment credit M2 §4b described, and the matched-lines check separates it
  out.
- Two pages that ran to the token limit after escaping looped on a run with
  no letter (`๒ ๒ ๒ …`, `3 3 3 …`). Variant B never cuts such runs (to protect
  dotted leaders), and they add no Thai marks.

**The added text is mostly not on the page.** On the 12 pages, the escape
added 769 output marks and 368 correct ones. Its text is right about half
the time (48%), against 79% for what greedy wrote before the loop. On Text
recognition, 30 of 323 added marks are correct (9%). There Wayu already
transcribes whole images, so text after a loop is surplus either way.

## 5. Limits

- **Review and claim level.** Up2mEz's review was pending at the time of
  writing. This is one run, on the calibration split only, at
  `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.
- **Addendum 1 came after a smoke.** It changed the post-escape watch after
  one calibration item (0159AF30) had been seen in the smoke. It did not change
  the first detection, the arms or the reading rules.
- **One escape design.** This escape is lexical: a looped unit may not recur.
  A different escape, such as one that bans by meaning or restarts from the
  image, might read more or less.
- **Loops without a letter are never cut,** here or in B.
- **Tone error has per-arm figures only.** It is higher with the escape on
  Full-page (5.96% against 4.89%), and no paired interval was registered.
- Only Wayu is tested. No claim is made beyond this checkpoint.

## 6. What this suggests (proposals only; none is authorized)

1. **Do not adopt the escape as it is.** It reads more, but it writes as much
   that is not on the page. Net F1 is unchanged on full pages and lower on
   text recognition.
2. **The missing piece is telling read text from invented text.**
   - **Candidate signal:** Wayu's own confidence on the text it writes after
     an escape. E1 found that Typhoon's confidence locates its mark errors.
   - **Data:** this run already holds labelled cases: 23 located lines and
     several invented passages.
   - **Test:** can be done offline, by teacher-forced scoring of `E`'s
     outputs with no new generation.
   - **Validity:** it needs a registration, and a held-out check before any
     claim, because the calibration items were used to find it.
3. **Track E's original question is answered for these checkpoints.**
   - Typhoon OCR 1.5 stays the best reader of Thai marks.
   - Wayu, with its loops stopped or escaped, stays about 18 points below it
     on full pages.
   - Further Wayu work makes sense only if the filter in item 2 works.
4. **Region-by-region reading** remains the input-side alternative, and it
   belongs to Up2mEz's region-OCR track.
