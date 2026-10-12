# MODEL_SURVEY_M6 — results: SEA-LION v4 4B-VL, InternVL3.5-2B (M6a); DeepSeek-OCR-2 (M6b)

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** Calibration split
only. Read against the patterns of `MODEL_SURVEY_M6_REGISTRATION.md` §3 and
its addenda, fixed before any full-run output existed. Up2mEz reviews
afterwards (standing delegation, DECISION_LOG 2026-10-11c).

## M6a

| | |
|---|---|
| run | `kaggle-model-survey-m6a-3ee076494466`; 4 units on 2×T4, all finished; checksums verified; 178 items per model, nothing failed, nothing not run; fp16 for both, no fallback |
| models | `aisingapore/Qwen-SEA-LION-v4-4B-VL@d0734aa1b811…`; `OpenGVLab/InternVL3_5-2B-HF@3f301ffcf3dc…` |
| compute | SEA-LION 2.56 GPU-hours, InternVL 3.05 (two shards each, run in parallel on the two T4s); cap 10 |
| primary scores | `docs/stage0/data/M6A_SCORES_3ee076494466.json` (`scripts/model_survey_analyze.py --config configs/model_survey/m6a.yaml`) |
| pairings with Qwen3-VL-4B, audit | `docs/stage0/data/M6A_EXTRA_3ee076494466.json` (`scripts/model_survey_m6_extra.py`) |
| W1 stop and attribution | `docs/stage0/data/M6A_W1_PROFILE_3ee076494466.json` (`scripts/model_survey_w1.py --config configs/model_survey/m6a.yaml`) |
| outputs | `docs/stage0/data/M6A_OUTPUTS_3ee076494466.json.gz` (no reference text, no images) |

Typhoon and the base Qwen3-VL-2B are T1's archived outputs, Qwen3-VL-4B is
M1's (`M1_OUTPUTS_3431d9f9dccf.json.gz`), all `BENCHMARK_QUESTION` on the same
178 items, as registered. Every model here ran `BENCHMARK_QUESTION`.

### 0. Markup audit (raw outputs, before any score was read)

| cell | n | at token limit | `**` | `#` heading | `\|` table | code fence | `>` quote | HTML tag | `<figure>` |
|---|---|---|---|---|---|---|---|---|---|
| SEA-LION · Full-page | 69 | 22 | 4 | 0 | 2 | 0 | 0 | 0 | 0 |
| SEA-LION · Text rec. | 109 | 7 | 103 | 10 | 0 | 0 | 31 | 0 | 0 |
| InternVL · Full-page | 69 | 53 | 33 | 22 | 1 | 5 | 0 | 0 | 0 |
| InternVL · Text rec. | 109 | 30 | 4 | 0 | 0 | 5 | 0 | 0 | 0 |

- **No HTML and no `<figure>`** in either model, so there is no
  unclosed-`<figure>` upper bound to report.
- **Markdown.** Extraction v2 removes bold, headings, tables and code fences;
  checked on the outputs, none survives extraction. The `#` that remains is
  hashtags that are in the references too.
- **Blockquote `>` survives extraction** in SEA-LION's 31 Text recognition
  outputs. It is not a Thai mark and does not change mark F1; it adds a
  character to CER per quoted line.
- **Answer framing.** Both models often wrap the text in an answer
  ("ข้อความในภาพเขียนว่า: …", "**ภาษาไทย:**", a translation, a description).
  That is not markup and extraction keeps it. It is the main reason for their
  low Text recognition precision (§1). As registered, it is scored as output.

### 1. Primary: order-free v2 mark F1 (%), paired

Differences are the model minus the other on the same items, 95% item
bootstrap (2,000 resamples, seed 20261010).

| task | model | F1 | Δ vs Typhoon [95%] | Δ vs Qwen3-VL-4B [95%] | Δ vs base [95%] |
|---|---|---|---|---|---|
| Full-page (69) | Typhoon 94.9 · Qwen3-VL-4B 45.9 · base 41.0 | | | | |
| | **SEA-LION** | 38.9 | **−56.0** [−62.3, −48.4] | −7.0 [−17.1, +1.3] | −2.1 [−11.7, +7.2] |
| | **InternVL** | 15.8 | **−79.0** [−82.7, −75.0] | **−30.1** [−39.8, −22.3] | **−25.1** [−34.0, −17.7] |
| Text rec. (109) | Typhoon 81.7 · Qwen3-VL-4B 23.5 · base 24.3 | | | | |
| | **SEA-LION** | 26.9 | **−54.8** [−65.6, −41.0] | +3.5 [−3.3, +10.5] | +2.7 [−8.7, +12.1] |
| | **InternVL** | 6.7 | **−75.0** [−82.8, −65.4] | **−16.8** [−24.6, −10.3] | **−17.6** [−29.3, −9.7] |

Recall and precision of SEA-LION against Qwen3-VL-4B (question (a)):

| task | Δ recall [95%] | Δ precision [95%] |
|---|---|---|
| Full-page | **−12.5** [−18.6, −7.0] | −4.8 |
| Text recognition | **−9.0** [−12.9, −5.4] | +2.8 |

Read against the registered patterns (§3):

- **(a) SEA-LION − Qwen3-VL-4B: interval includes 0 on both tasks.**
  Registered reading: no gain shown from language fine-tuning alone; that
  OCR-targeted training (Typhoon, Pathumma) is where the gains came from is
  an inference, not a measurement. The F1 intervals are about ±9 and ±7
  points wide, so a gain or loss of that size is not ruled out. Recall is
  lower on both tasks with intervals excluding 0: SEA-LION finds fewer
  reference marks than the model it was fine-tuned from, and the F1
  difference does not show because its precision is not lower.
- **(b), (c) Both below Typhoon on both tasks, intervals below 0.** Typhoon
  stays the strongest measured; nothing changes for the paper's wording.
  InternVL is also below the base and Qwen3-VL-4B on both tasks.
- **SEA-LION against the base:** no difference shown (intervals about ±9–10
  points wide).

### 2. W1: stop at a loop, and attribution

| model · task | looping (at limit) | ended outputs changed by the stop | v2 F1 | with stop | Δ [95%] | repeat-aware F1 |
|---|---|---|---|---|---|---|
| SEA-LION · Full-page | 22 / 69 | 0 / 47 | 38.9 | 51.8 | **+12.9** [+8.9, +17.0] | 32.0 |
| SEA-LION · Text rec. | 7 / 109 | 0 / 102 | 26.9 | 34.2 | **+7.3** [+1.8, +12.4] | 25.4 |
| InternVL · Full-page | 53 / 69 | 2 / 16 | 15.8 | 13.5 | −2.3 [−4.7, +0.4] | 4.6 |
| InternVL · Text rec. | 30 / 109 | 2 / 79 | 6.7 | 18.7 | **+12.0** [+9.2, +14.6] | 3.9 |

- **The four InternVL outputs the stop changed without reaching the limit**
  (`FD16783E`, `049E88E5`, `627EB4F3`, `9DA41D6D`) were read: each repeats a
  line or phrase many times and then emits end-of-sequence before the limit.
  They are loops that ended, not false cuts. W1's "non-looping" is defined by
  the token limit, so they count as changed ended outputs. Earlier: Paddle 2
  (Full-page) and Pathumma 1 (Text recognition); every other cell 0.
  InternVL's 2 of 16 on Full-page is the largest share so far (12.5%). The
  paper's wording "without changing non-looping outputs" should read "without
  changing outputs that ended without a loop", or carry this caveat.
- **InternVL Full-page:** the stop does not help. Recall falls from 32.5% to
  8.7% while precision rises from 10.5% to 30.0%: the correct marks it
  removes (5,282 → 1,423) lie after the first repeat run, so these outputs
  do not stop reading at their first loop. This is the only cell in W1, M5
  or M6a where the stop's point estimate is negative.

Attribution, Full-page, on the stopped outputs (`attribute_marks(...,
approximate_reorder=True)`), as share of reference marks:

| model | correct | line absent | span missing | misread, base right | misread, other | not read ÷ misread (base right) |
|---|---|---|---|---|---|---|
| SEA-LION | 45.0 | 17.4 | 16.2 | 5.8 | 15.5 | 5.8 |
| InternVL | 8.2 | 71.4 | 10.8 | 1.8 | 7.9 | 46.6 |
| base (T1) | 53.8 | 33.4 | 5.0 | 3.4 | 4.2 | 11.3 |
| Typhoon (T1) | 93.8 | 2.7 | 0.5 | 0.4 | 0.9 | 7.3 |

- **Claim (2) extends** to SEA-LION and to InternVL, a third family
  (registered pattern "loss mostly whole lines absent or loops"). Not reading
  outweighs misreading on a correct base about 6× (SEA-LION) and 47×
  (InternVL).
- **SEA-LION has the largest "misread, other" share measured (15.5%)**:
  marks wrong where the base consonant was also wrong. That is misreading,
  not mark-specific misreading; it is reported beside the ratio, which does
  not count it.
- "Line absent" after a loop does not separate the loop from failure to read
  (W1 §3); the wording stays "not read", not "skipped".

## M6b (DeepSeek-OCR-2)

| | |
|---|---|
| run | `kaggle-model-survey-m6b-afe5126bedd7`; 2 shards on 2×T4, both finished; checksums verified; 356 records (178 items × 2 prompts); nothing failed, nothing not run |
| model | `deepseek-ai/DeepSeek-OCR-2@aaa02f381194…`, own runner and venv (Addendum 1), eager attention |
| precision | fp16 only. The fp32 check does not fit on a T4 (Addendum 3), so whether fp32 would loop later is not known |
| compute | 4.4 GPU-hours (2.2 h per shard, both prompts); cap 8 |
| primary scores | `docs/stage0/data/M6B_SCORES_afe5126bedd7.json` |
| pairings, audit | `docs/stage0/data/M6B_EXTRA_afe5126bedd7.json` |
| W1 | `docs/stage0/data/M6B_W1_PROFILE_afe5126bedd7.json` |
| outputs | `docs/stage0/data/M6B_OUTPUTS_afe5126bedd7.json.gz` |

### 0. Markup audit (raw outputs, before any score was read)

| cell | n | at limit | `**` | `#` heading | `\|` table | `<\|ref\|>`/`<\|det\|>` | HTML / `<figure>` |
|---|---|---|---|---|---|---|---|
| `CARD_PROMPT` · Full-page | 69 | 27 | 12 | 26 | 4 | 1 | 0 |
| `CARD_PROMPT` · Text rec. | 109 | 10 | 16 | 19 | 1 | 0 | 0 |
| `BENCHMARK_QUESTION` · Full-page | 69 | 51 | 8 | 5 | 2 | 0 | 0 |
| `BENCHMARK_QUESTION` · Text rec. | 109 | 50 | 23 | 9 | 0 | 2 | 0 |

- No HTML and no `<figure>`: no unclosed-`<figure>` bound to report.
- Markdown is removed by extraction v2.
- **DeepSeek's grounding markup survives extraction** in 3 outputs
  (`839D694C`, `C652EC9B` with `BENCHMARK_QUESTION`; `B2EF6E79` with
  `CARD_PROMPT`): `<|ref|>text<|/ref|><|det|>[[x0, y0, x1, y1]]<|/det|>`
  becomes `< ref >text< /ref >< det >[[…]]< /det >`. It holds no Thai mark,
  so mark F1 is unchanged; it adds characters to CER and to the order-free
  matcher's unmatched lines. The model emitted it although neither prompt
  asks for grounding.
- `<` also survives in `A3407ABE` (both prompts) as `<.05`, which is in the
  reference.

### 1. Primary: order-free v2 mark F1 (%), paired

DeepSeek minus the other model on the same items, 95% item bootstrap.
DeepSeek's primary prompt is the card's `Free OCR.`; the others ran
`BENCHMARK_QUESTION`.

| task | DeepSeek prompt | F1 | Δ vs Typhoon | Δ vs Qwen3-VL-4B | Δ vs base |
|---|---|---|---|---|---|
| Full-page (69) | **card (primary)** | 26.2 | **−68.7** [−74.7, −60.4] | **−19.8** [−30.0, −9.9] | **−14.8** [−24.5, −4.3] |
| | `BENCHMARK_QUESTION` | 17.8 | **−77.1** [−82.1, −70.9] | **−28.2** [−38.8, −18.6] | **−23.2** [−33.0, −14.5] |
| Text rec. (109) | **card (primary)** | 39.9 | **−41.8** [−61.2, −13.2] | **+16.4** [+0.5, +43.0] | +15.6 [−5.4, +44.3] |
| | `BENCHMARK_QUESTION` | 4.0 | **−77.7** [−85.4, −68.2] | **−19.5** [−27.1, −13.8] | **−20.3** [−32.0, −12.9] |

- **(d) Below Typhoon on both tasks, intervals below 0.** Typhoon stays the
  strongest measured.
- **Against Qwen3-VL-4B and the base:** below on Full-page. On Text
  recognition, the card prompt's lead over Qwen3-VL-4B has an interval that
  only just excludes 0 and is 42 points wide; over the base it is not shown.
  Recall is lower than every comparison on both tasks (intervals below 0);
  the Text recognition F1 lead comes from precision.
- **Prompt matters more than for any model so far.** `BENCHMARK_QUESTION`
  loops on 51/69 pages and 50/109 crops (card prompt: 27 and 10), and its
  median CER is 1.0 on both tasks. The card's prompt is the registered
  primary, so this does not change the reading.

### 2. W1: stop at a loop, and attribution (card prompt)

| task | looping | ended outputs changed | v2 F1 | with stop | Δ [95%] | repeat-aware |
|---|---|---|---|---|---|---|
| Full-page | 27 / 69 | 0 / 42 | 26.2 | 46.1 | **+19.9** [+13.5, +26.9] | 18.9 |
| Text rec. | 10 / 109 | 0 / 99 | 39.9 | 62.2 | +22.3 [0.0, +36.3] | 39.7 |

The Text recognition lower bound is 0.0: the gain is large but not shown at
this n.

Attribution, Full-page, stopped outputs (share of reference marks): correct
36.8, line absent 33.9, span missing 14.6, misread with base right 3.8,
misread other 10.8. Not reading ÷ misreading on a correct base = **12.9**.
Claim (2) extends to DeepSeek-OCR-2, a fourth family.

**Caveat (Addendum 3).** fp32 could not be checked on a T4. DeepSeek's loop
rates and the stop's gain are fp16 numbers; the card's own `infer()` bans
repeated 20-grams, which M1's protocol does not.
