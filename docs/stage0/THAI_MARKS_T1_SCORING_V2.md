# T1 scoring version 2

**Status:** written 2026-09-28, **after** T1 output of run
`kaggle-thai-marks-t1-t2-a44199c29759` had been seen, and before any version-2
number was computed. It is a post-hoc correction of the measurement, not a
pre-registered rule; the claim level of every result stays
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE` (calibration split only), and the locked
split remains closed for confirmation. Version 1 (`normalize.normalize_text` +
global alignment, as registered in `THAI_MARKS_T1_T2_REGISTRATION.md` §4) is
kept in code unchanged and still reported, for continuity. Decision record:
`docs/DECISION_LOG.md` 2026-09-28b.

## 1. Why version 1 cannot measure reading

Model output and ThaiOCRBench references are not in the same format, and
version 1 compared them after regex clean-up designed before any output
existed. Census of the 2026-09-27 run (calibration, 178 items per model):

| model | prompt | task | outputs with `<figure>` | with `<table>` | output / reference length, median |
|---|---|---|---|---|---|
| base | BENCHMARK_QUESTION | Full-page OCR | 0/69 | 0 | 1.03 |
| base | BENCHMARK_QUESTION | Text recognition | 0/109 | 0 | 1.51 |
| base | TYPHOON_CARD | Full-page OCR | 63/69 | 32 | 2.90 |
| base | TYPHOON_CARD | Text recognition | 95/109 | 78 | 6.95 |
| typhoon | BENCHMARK_QUESTION | Full-page OCR | 0/69 | 3 | 1.00 |
| typhoon | BENCHMARK_QUESTION | Text recognition | 0/109 | 0 | 1.01 |
| typhoon | TYPHOON_CARD | Full-page OCR | 48/69 | 8 | 1.20 |
| typhoon | TYPHOON_CARD | Text recognition | 77/109 | 3 | 4.67 |

Three distinct problems follow:

1. **Scope.** A Text recognition reference is one region of the image
   (median 101 characters). `TYPHOON_CARD` asks for *all* text on the page, so
   both models transcribe the whole image. Global alignment then charges every
   correctly read character outside the region as an insertion — the source of
   macro CER above 100% (base, `TYPHOON_CARD`, Text recognition: 1577.5%).
2. **Format contract.** `TYPHOON_CARD` defines `<figure>` as an image
   *description* in Thai. Base often wraps its transcription in `<figure>`
   instead (e.g. item `A4862002`: 2,007 characters, normalized by version 1 to
   the single word `markdown`), and 66 of base's 68 unclosed `<figure>` blocks
   are runaway table repetitions cut off at `max_new_tokens` (typhoon: 2/2).
   For base, this cell measures format-following, not reading.
3. **Pooling.** Version 1 summarized each prompt over both tasks, averaging
   references of median 101 and 1,388 characters.

## 2. Extraction (`src/labbs2026/thai_marks/extract.py`)

Applied identically to reference and hypothesis; never alters a Thai character:
code-fence lines removed; HTML parsed with a real parser (`html.parser`),
tags removed with their text kept, entities decoded, word boundaries kept at
cell/row/block boundaries; `<figure>` content removed **by the prompt's own
contract** — an unclosed `<figure>` runs to the end of the text, which is what
the markup says and, per §1, is truncation in practice; Markdown heading
markers, `**`, `__`, backticks and `$` removed with content kept; `|` to space;
whitespace collapsed. No Unicode normalization.

Transcription placed inside `<figure>` is **not** scored as reading. It is
measured as its own outcome, `ref_in_figure_share`: the share of reference
characters read correctly only when figure content is kept.

## 3. Reference-anchored alignment (`decompose.align_anchored`)

Every reference character is aligned; hypothesis text before and after the
best-matching window is free. Within the window, errors count as usual, so the
anchored distance is at most the reference length and CER ≤ 100%. Text outside
the window is reported separately as **over-generation** (surplus characters
per reference character), together with truncation and repetition rates. The
mark decomposition and the lexical classification use the same alignment.

## 4. Located rule — no credit for chance matches

Freeing the ends lets a *wrong* answer match reference characters by chance
(item `A4862002`, `BENCHMARK_QUESTION`: the model answered a different line and
reached anchored CER 0.6 on a 10-character reference). The chance level is
measured, not assumed: in each (model, prompt, task) cell, every reference is
aligned against another item's hypothesis from the same cell (seeded
derangement, seed 20260928). An output is **located** if its anchored CER is
below the 5th percentile of that null; otherwise it is scored as reading
nothing (CER 100%, every reference character deleted, no mark credited), and
`cer_raw` keeps the unthresholded value.

| model | prompt | task | null 5th pct | null median | located |
|---|---|---|---|---|---|
| base | BENCHMARK_QUESTION | Full-page OCR | 0.794 | 0.837 | 63/69 |
| base | BENCHMARK_QUESTION | Text recognition | 0.714 | 0.824 | 95/109 |
| base | TYPHOON_CARD | Full-page OCR | 0.807 | 1.000 | 18/69 |
| base | TYPHOON_CARD | Text recognition | 0.778 | 1.000 | 17/109 |
| typhoon | BENCHMARK_QUESTION | Full-page OCR | 0.803 | 0.831 | 69/69 |
| typhoon | BENCHMARK_QUESTION | Text recognition | 0.733 | 0.840 | 99/109 |
| typhoon | TYPHOON_CARD | Full-page OCR | 0.802 | 0.831 | 67/69 |
| typhoon | TYPHOON_CARD | Text recognition | 0.700 | 0.825 | 107/109 |

A fixed ANLS-style threshold of 0.5 (Biten et al., ST-VQA) was considered and
not used: for base, Full-page OCR, it would discard 19 genuine but error-laden
readings that are well below chance (44 below 0.5 versus 63 below the null).

## 5. Cells and the primary prompt

Results are always reported per (model, task, prompt) and never pooled across
task or prompt.

- **Text recognition — primary `BENCHMARK_QUESTION`**: the researcher's
  decision, 2026-09-28. It is the benchmark's own question for that region.
- **Full-page OCR — primary `BENCHMARK_QUESTION`**: confirmed by the researcher 2026-09-28; proposed by Claude Code's
  recommendation. It is the
  benchmark's own prompt and asks for plain text
  (`THAIOCRBENCH_TASK_SELECTION.md`); outputs carry no figure markup for either
  model; and base under `TYPHOON_CARD` fails the format contract on 63/69
  items. `TYPHOON_CARD` stays the secondary cell for both tasks — it is
  Typhoon's native prompt and the T2 prompt — reported with the contract
  diagnostic, never as the reading measurement for base.

T2's greedy comparison keeps the registered `TYPHOON_CARD` source (T2
teacher-forces that prompt) and uses the same extraction, anchored alignment
and located threshold of the matching T1 cell; T2 is also split by task.

## 6. Decoding parameters

Both checkpoints' `generation_config.json` default to sampling (`do_sample`
true, temperature 0.7, top_p 0.8, top_k 20). The 2026-09-27 run passed
`do_sample=False, num_beams=1`, which transformers 5.12 applies over those
defaults; its temperature/top-k/top-p warpers are added only when `do_sample`
is true, and `repetition_penalty` is 1.0 for both checkpoints, so that run was
deterministic greedy decoding. This is established from code and the pinned
configs, **not** from a runtime record, because the resolved configuration
was not logged. From now on the values are pinned in `t1.generation` of
`configs/thai_marks/t1_t2.yaml`, validated by `generation.generation_kwargs`,
and the resolved configuration is written to every T1 manifest.

## 7. T2 findings made while re-scoring — not fixed, block T2-based routing

Found on the complete Typhoon T2 leg (178 items); base T2 did not finish.

1. **Defect: zero-token windows.** On 10 sites (6 tone, 4 upper vowel) one
   variant's scoring window has 0 tokens, so its summed log-probability is 0,
   the maximum possible, and it wins on all 10. A registered score cannot
   compare an empty window with a non-empty one; the fix belongs in
   `runtime.score_item` and needs its own amendment.
2. **Tone-mark oracle accuracy depends on the scoring convention.** With the
   registered summed log-probability (zero-token variants excluded) tone
   oracle accuracy is 92.6%; with per-token mean log-probability it is 88.9%;
   restricted to variants with the reference's token count it is 96.3%. Upper
   and lower vowels and tone-absent sites stay at 97.6-100% under all three.
   Of the 193 wrong tone winners, 139 are ๊ or ๋ replacing ้ or ่, 47 are
   "no mark", and 139 of 193 winners have *more* tokens than the reference,
   so a short-window penalty does not explain them. Greedy tone accuracy (Text recognition
   95.6%, Full-page OCR 92.2%) is at or above oracle, which a genuine oracle
   should not be.

Until (1) is fixed and (2) is understood, T2's tone-mark headroom
(oracle − greedy) must not be used to route a remedy under
`T1_T2_CONTINGENT_REMEDY_PLAN.md`. This is an observation with a hypothesis
(the window cut 8 characters past the site makes tokenizations of the rare
marks incomparable), not an established cause.

## 8. Known limitations

- Reading order inside the matched window still counts; a model that reads a
  full page in a different order is penalized for order, not only for reading.
- Chance thresholds are per cell (0.70–0.81), so they differ slightly between
  models; they are calibrated to each cell's own output lengths.
- A located output may still contain a chance-matched stretch at its edges;
  the threshold removes whole outputs, not local spans.
- `BENCHMARK_QUESTION` wording varies per item (85 and 242 phrasings); some
  Text recognition questions point to one line, and answering another line is
  scored as not located, which is a question-following failure, not reading.
