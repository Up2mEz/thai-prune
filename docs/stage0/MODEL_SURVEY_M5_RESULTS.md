# MODEL_SURVEY_M5 — results: Pathumma Vision 3.0.0-Re

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** Calibration split
only. One run, read against the patterns `MODEL_SURVEY_M5_REGISTRATION.md`
§3 fixed before any full-run output existed. Up2mEz's review comes after
(standing delegation, PR #79).

| | |
|---|---|
| run | `kaggle-model-survey-m5-8252b99e735d`; 2 shards on 2×T4, both finished; checksums verified; 356 records (178 items × 2 prompts); no fp32 fallback |
| model | `nectec/Pathumma-llm-vision-3.0.0-re@08bb11dcabf509ac3fa3ac0014ecd44eadb9729b` |
| compute | about 2.0 GPU-hours of generation (1.07 h `CARD_PROMPT`, 0.97 h `BENCHMARK_QUESTION`); cap 6 |
| primary scores | `docs/stage0/data/M5_SCORES_8252b99e735d.json` (`scripts/model_survey_analyze.py --config configs/model_survey/m5.yaml`) |
| Addendum 1 secondary | `docs/stage0/data/M5_SCORES_UNWRAPPED_8252b99e735d.json` (`--unwrap-natural-text`) |
| other secondaries, audit | `docs/stage0/data/M5_EXTRA_4a0f5bbf1bec.json` (`scripts/model_survey_m5_extra.py`) |
| W1 stop and attribution | `docs/stage0/data/M5_W1_PROFILE_23b701e974f2.json` (`scripts/model_survey_w1.py --config configs/model_survey/m5.yaml`) |
| outputs | `docs/stage0/data/M5_OUTPUTS_8252b99e735d.json.gz` (no reference text, no images) |

Typhoon OCR 1.5 and base Qwen3-VL-2B are T1's archived outputs on the same
178 items (`BENCHMARK_QUESTION`), as registered.

## 1. Primary: order-free v2 mark F1 (%), paired against Typhoon and the base

The primary row is Pathumma at its card prompt `อ่านข้อความในภาพนี้`. The
`BENCHMARK_QUESTION` row is the registered secondary: the same prompt that
Typhoon and the base ran. It sits in the same table so that a difference
cannot be put down to the prompt, as Up2mEz asked. Differences are Pathumma
minus the other model on the same items, with a 95% item bootstrap (2,000
resamples, seed 20261010).

| task | Pathumma prompt | Pathumma F1 (R / P) | Typhoon F1 (R / P) | base F1 | Δ vs Typhoon [95%] | Δ vs base [95%] |
|---|---|---|---|---|---|---|
| Full-page (69) | **card (primary)** | 89.8 (89.9 / 89.7) | 94.9 (96.1 / 93.7) | 41.0 | −5.1 [−14.3, +1.6] | **+48.9** [+38.5, +58.6] |
| | `BENCHMARK_QUESTION` | 91.5 (90.2 / 93.0) | | | −3.3 [−9.5, +1.8] | **+50.6** [+41.6, +59.1] |
| Text recognition (109) | **card (primary)** | 77.6 (97.2 / 64.6) | 81.7 (82.9 / 80.6) | 24.3 | −4.1 [−15.1, +8.0] | **+53.3** [+41.1, +63.3] |
| | `BENCHMARK_QUESTION` | 69.1 (95.2 / 54.2) | | | −12.6 [−31.4, +5.8] | **+44.8** [+28.7, +60.6] |

The recall and precision parts of the difference to Typhoon (card prompt;
`BENCHMARK_QUESTION` in §2):

| task | Δ recall [95%] | Δ precision [95%] |
|---|---|---|
| Full-page | **−6.2** [−12.0, −1.2] | −3.9 [−19.2, +8.2] |
| Text recognition | **+14.3** [+5.4, +26.0] | −16.0 [−31.4, +0.6] |

Read against the registered patterns (§3):

- **Against Typhoon: comparable, not shown better or worse.** Both intervals
  include 0, which is the registered pattern "no difference shown on that
  task; comparable, not better". The card's Text recognition lead (0.674 vs
  0.592, metric unstated) does not show under this metric. The point
  estimate is below Typhoon's, but Typhoon is not shown better either.
  - Under the registered reading, the paper does **not** call Typhoon the
    best open Thai OCR model.
  - **"Comparable" is not "equivalent"** (Up2mEz's review, 2026-10-12).
    Nothing here shows the two are equal; it only fails to show a
    difference. The Text recognition interval cannot rule out that Typhoon is
    15 points better, and Full-page's lower end is −14.3. Wording for the
    paper: "no difference shown at n = 69/109, with intervals about ±10
    points wide; Typhoon's point estimates are higher".
  - **Contamination applies to both models** (registration Addendum 2).
    Typhoon comes from ThaiOCRBench's group. Pathumma's card says it was
    fine-tuned on 377K OCR samples without naming them, and the card reports
    ThaiOCRBench scores itself. Overlap with the benchmark cannot be ruled out
    for either model, so neither level, and no lead between them, is clean
    of it.
  - **The two may share training signal.** Pathumma writes Typhoon OCR's
    output format: HTML tables, `<figure>` descriptions, headings and, on
    five outputs, Typhoon's `{"natural_text": …}` wrapper (§4). That suggests
    its training targets came from a Typhoon-style pipeline. This is an
    inference, not shown. If so, the two models' scores may not be
    independent of each other either.
- **Against the base: well above, on both tasks.** The intervals are far
  from 0, so a second Thai fine-tune of Qwen3-VL-2B gains marks over the
  base. RQ-C has two specialized-vs-base pairs (Typhoon and Pathumma), with
  the same base and the same items.
- **Text recognition: the two models fail differently.**
  - Pathumma finds more of the asked-for marks than Typhoon (recall +14.3,
    interval above 0).
  - It also writes more than was asked. The card prompt says "read the text
    in this image", and Pathumma often transcribes the whole image, not just
    the span the question names; the reference holds only that span. Of 109
    outputs, 46 carry surplus marks, and the largest surplus comes from
    whole-image transcriptions (checked by reading the three largest).
    Example: a reference of 10 characters against an output of 1,283
    characters that reads the full slide.
  - Its precision is therefore lower. The F1 difference is the net of the
    two and is not a difference in reading marks.
  - **Do not quote the recall lead alone.** Order-free recall credits marks
    anywhere in the output, so most of the +14.3 comes from the
    whole-image habit. It is always given next to the precision drop.

## 2. Secondaries

**Secondary prompt (`BENCHMARK_QUESTION`; rows in §1's table).**

- **Same reading as the primary.** Pathumma is comparable to Typhoon on both
  tasks and well above the base.
- **The question does not narrow the scope.** On Text recognition, asking the
  benchmark's question lowers precision further (54.2%), so Pathumma reads
  the whole image even when asked for one span. Recall stays above Typhoon's
  (+12.3 [+2.1, +24.7]); precision is below it (−26.3 [−47.6, −1.7]).
- **On Full-page,** the recall gap is the same with either prompt (−6.0
  [−11.5, −1.2]).

**Repeat-aware variant (PR #85).** Pathumma's greedy F1 is 88.9 on Full-page
(v2 89.8) and 77.7 on Text recognition (v2 77.6). The loop credit that v2
gives is small, because few outputs loop (§3).

**T1 scoring v2** (CER, consonant error and tone-error rates, with
intervals) per cell is in the scores file (`models.pathumma.t1_v2`). It is
not read here.

**Addendum 1, JSON-unwrapped.** The secondary score equals the primary in
every cell (`M5_SCORES_UNWRAPPED_8252b99e735d.json`), for two reasons:

- the looping wrapped output (`0159AF30`) has the same marks after
  unwrapping;
- the other wrapped outputs are not valid JSON, and the registered decoder
  stops where the scoring already stops (§4).

## 3. W1 on Pathumma: the stop and where the marks go

The same code and rules as `MODEL_SURVEY_W1_CROSS_MODEL.md`, primary prompt.

| task | loops / items | F1 greedy → + stop | Δ F1, all items [95%] | non-looping changed | loop share of surplus |
|---|---|---|---|---|---|
| Full-page | 4 / 69 | 89.8 → 92.8 | +3.0 [0.0, +8.9] | 0 / 65 | 76% |
| Text recognition | 2 / 109 | 77.6 → 77.7 | +0.1 [0.0, +0.2] | 1 / 107 | 1% |

- **Pathumma rarely loops** (6 of 178 outputs at the limit; the base: 46).
  Like Typhoon, it gains little from the stop.
- **The stop is safe here too.** It changed 1 of 172 ended outputs, on Text
  recognition. The F1 change on the ended outputs is +0.02. Across W1's ten
  cells and these two, it changed 3 of 898 ended outputs.
- **Text recognition's surplus is not loops.** Only 1% of its surplus marks
  are in outputs the stop cuts. The rest is the whole-image transcription of
  §1.

**Attribution, Full-page, stopped outputs (share of all 16,266 reference
marks, %).**

| model | correct | read in another order | **whole line absent** | span missing | misread, base right | misread with base |
|---|---|---|---|---|---|---|
| Pathumma | 87.7 | 0.9 | **6.9** | 2.4 | 0.8 | 1.3 |
| Typhoon (W1) | 93.8 | 1.6 | **2.7** | 0.5 | 0.4 | 0.9 |
| base (W1) | 53.8 | 0.2 | **33.4** | 5.0 | 3.4 | 4.2 |

- **Not reading again dominates.** Line absent plus span missing is 9.3% of
  marks. A wrong mark on a correctly read base is 0.8%, about 12 times less.
- **Claim (2) extends to a third Thai model.** This is the registered
  pattern: Pathumma's loss is mostly whole lines absent.
  - Unlike the base, few of these come after a loop: the raw-output column
    already has 6.0% line absent.
  - Up to 1.3 of those points are the two pages in §4.
- **Where it trails Typhoon on Full-page:** the recall gap (−6.2) sits in
  lines absent (6.9 vs 2.7) and spans missing (2.4 vs 0.5). Misread marks
  differ by 0.4 and 0.4 points.

## 4. Markup audit (checked on the raw outputs before scoring)

Addendum 1 said there was no HTML. That was true of the smoke's four
outputs, not of the full run:

| cell | JSON-wrapped | at token limit | with `<figure>` | unclosed `<figure>` |
|---|---|---|---|---|
| `CARD_PROMPT`, Full-page | 3 (`0159AF30`, `C065E1E9`, `DF82A0C7`) | 4 | 13 | 4 |
| `BENCHMARK_QUESTION`, Full-page | 2 (`C065E1E9`, `DF82A0C7`) | 2 | 9 | 2 |
| `CARD_PROMPT`, Text recognition | 0 | 2 | 7 | 0 |
| `BENCHMARK_QUESTION`, Text recognition | 0 | 2 | 4 | 0 |

**What Pathumma writes.** Typhoon OCR's output format:

- HTML tables (`<table>`, `<tr>`, `<td>`);
- `<figure>` blocks that describe images in Thai (for example a bank logo or
  a QR code);
- Markdown headings;
- on five outputs, Typhoon's `{"natural_text": ...}` JSON wrapper.

The reference holds none of this.

**How scoring treats it.** M1's scoring (structure-aware extraction v2,
`thai_marks.extract`) removes tags, headings and figure content before
counting marks, as it did for Typhoon. Markup therefore does not enter the
counts, and figure descriptions are not charged as surplus.

**Two kinds of unclosed `<figure>`:**

- **Looping inside a figure.** `A3407ABE` and `5300A462` loop inside a
  figure to the token limit. Dropping the figure drops the loop as well.
- **Malformed tag, text dropped.** The two JSON-wrapped pages `C065E1E9` and
  `DF82A0C7` (both prompts) contain a malformed tag such as `<figure 8=""
  9="">`, which is never closed.
  - The scoring treats what follows as figure content and drops it, so these
    outputs keep 25–102 of about 600–1,000 characters.
  - The quotes in the tag are unescaped, so the JSON is invalid. Addendum 1's
    decoder stops at the first such quote, which is why the unwrapped score
    equals the primary.
  - The two pages hold 211 reference marks (1.3% of Full-page).

**Diagnostic, not registered: an upper bound for those two pages.** Credit
both pages with a perfect read. The card-prompt F1 becomes 90.5 and Δ vs
Typhoon −4.4 [−13.4, +2.2]; `BENCHMARK_QUESTION` gives −2.7 [−8.7, +2.4].
The reading of §1 does not change.

**This is a scoring defect, not only a property of the data** (Up2mEz's
review, 2026-10-12). Extraction v2 lets a stray or malformed opening tag
swallow the rest of the text. The same behaviour was found in a review of the
T1 scoring branch (`extract_text('a x<y b z')`). It sits in `thai_marks`,
Up2mEz's namespace, and is passed on there; this track does not change it.
Until it is fixed, every model that writes figure markup gets the upper bound
reported beside the registered score.

## 5. What this supports (proposal; claims are Up2mEz's to word)

- **Typhoon is not "the best open Thai OCR model".** On our metric, no
  difference between Pathumma and Typhoon is shown on either task. The
  intervals include 0 and are about ±10 points wide, and Typhoon's point
  estimates are higher. This is not equivalence. Both carry the contamination
  caveat of §6. The wording that fits is "the
  strongest of the models we measured, comparable to Pathumma", not "best".
- **RQ-C: two Thai fine-tunes of the same base both gain about 50 F1
  points** on the same items, with the same base outputs, as two independent
  pairs.
- **Claim (2), not reading over misreading:** six models now (W1's five and
  Pathumma), with W1's alignment caveat.
- **Claim (3), the stop leaves ended outputs alone:** 3 of 898 ended outputs
  changed across twelve cells.
- **Not shown:**
  - anything on the locked split (W4);
  - that the Text recognition scope behaviour comes from training, not from
    the prompt (both prompts show it);
  - any statement about `3.0.0-preview`, or about the card's own metric.

## 6. Limits

- One run, greedy, calibration split; `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.
- Up2mEz's review is pending.
- Typhoon and the base run `BENCHMARK_QUESTION`; Pathumma's primary is its
  card prompt, as M1's rule says. The same-prompt rows in §1 give the same
  reading.
- **Contamination.**
  - Typhoon comes from ThaiOCRBench's group.
  - Pathumma's 377K fine-tuning samples are not named, and its card reports
    ThaiOCRBench scores.
  - The base's (Qwen3-VL's) training data are unknown in this respect.
  - Benchmark overlap cannot be ruled out for any of the three (Addendum 2).
- The fp16 run of a QAT/bf16 checkpoint showed no overflow or garbage, but
  bf16 was not run as a check.
