# MODEL_SURVEY_M6 — registration (Track E: SEA-LION v4 4B-VL, InternVL3.5-2B; DeepSeek-OCR-2 as M6b)

**Status: `APPROVED` by PELY334 in session on 2026-10-12** ("ทำทุกอันเลย", "do
all of them"). Written before any M6 output existed. Up2mEz's work split
(collab `20261011T1315Z_Up2mEz_to_PELY334_paper-prep-work-split.md`, W2, M6)
lists these models after M5. Calibration only, PELY334's quota, own
namespace; under the standing delegation (DECISION_LOG 2026-10-11c) Up2mEz
reviews afterwards. Clearance: `MODEL_SURVEY_M6_CLEARANCE.md`. Claim level of
every result: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

M6 has two runs:

- **M6a** (this registration, `configs/model_survey/m6a.yaml`): SEA-LION and
  InternVL3.5-2B on M1's runtime unchanged.
- **M6b**: DeepSeek-OCR-2, which needs its own runtime path (clearance §4).
  It gets its own addendum, written before its smoke.

**Questions.**

- **(a) SEA-LION against Qwen3-VL-4B.** SEA-LION is a SEA-language
  fine-tune, including Thai, of exactly M1's Qwen3-VL-4B: the same config,
  processor and chat template (clearance §2). Does a general multilingual
  fine-tune that is not aimed at OCR change how Thai marks are read? This is
  a third specialized-vs-base pair for RQ-C, of a different kind: language
  fine-tune, not OCR fine-tune.
- **(b) InternVL3.5-2B.** A different vision encoder (InternViT) and image
  tiling, with Thai not declared, at the size of the Thai models. Does a
  third family show the same failure profile (claim (2))?
- **(c) Against Typhoon.** Both, on the same items, so the paper's
  "strongest measured here" stays checked against every model run.

## 1. Fixed inputs: M1's, unchanged

- **Models.**
  - `aisingapore/Qwen-SEA-LION-v4-4B-VL@d0734aa1b8113fce90997a83c1e4afe2c37c6205`.
  - `OpenGVLab/InternVL3_5-2B-HF@3f301ffcf3dcbb47893afae6650ea3e78d96fb6d`.
    This is the HF-format checkpoint of the work split's
    `OpenGVLab/InternVL3_5-2B`; clearance §3 gives the reasons and the
    equivalence checks.
- **Everything else is M1's,** tested equal to `configs/model_survey/m1.yaml`
  (`tests/test_model_survey_m6.py`):
  - data: T1's 178 calibration items, T1's image policy, then the model's
    own processor;
  - decoding: greedy, `max_new_tokens=3072`, `use_cache=true`;
  - runtime: fp16 with fp32 fallback, `sdpa`;
  - scoring: M1's;
  - comparison outputs: T1's archived Typhoon and base outputs.
- **Prompt.** `BENCHMARK_QUESTION` only, for both. Neither card gives an OCR
  prompt, and Qwen3-VL-4B ran this prompt in M1. No system message: the chat
  templates as shipped, as M1 ran Qwen3-VL-4B.
- **Code.** M1's, unchanged:
  - `scripts/model_survey_kaggle.py --config configs/model_survey/m6a.yaml`;
  - `scripts/model_survey_analyze.py --config …`;
  - `scripts/model_survey_w1.py --config …`.

  Comparisons to M1's Qwen3-VL-4B use its archived outputs
  (`M1_OUTPUTS_3431d9f9dccf.json.gz`).

## 2. Outcomes

- **Primary.** For each model and task, order-free v2 mark F1 (with recall
  and precision), paired against Typhoon (`BENCHMARK_QUESTION`) on the same
  items. 95% item bootstrap, 2,000 resamples, seed 20261010.
- **Primary for (a).** SEA-LION minus Qwen3-VL-4B, paired on the same items
  and the same prompt.
- **Secondary.**
  - differences to the base Qwen3-VL-2B;
  - the repeat-aware variant (PR #85) beside v2;
  - T1 scoring v2 per cell;
  - W1's stop and attribution (`scripts/model_survey_w1.py`), as for the
    other models.
- **Reported with every result (Up2mEz's M5 review):**
  - the markup audit, done on the raw outputs before scoring;
  - the unclosed-`<figure>` upper bound for any model that writes figure
    markup;
  - "comparable" never as "equivalent": an interval that includes 0 is read
    as "no difference shown at n = 69/109", with its width stated.

## 3. What each pattern would mean, stated in advance

| pattern | reading |
|---|---|
| SEA-LION − Qwen3-VL-4B above 0 on a task, interval excluding 0 | a general SEA-language fine-tune gains Thai marks without OCR training; RQ-C gets a third pair of a different kind |
| that interval including 0 | no gain shown from language fine-tuning alone; OCR-targeted training (Typhoon, Pathumma) is where the gains in M5 and T1 came from, as an inference |
| SEA-LION or InternVL below Typhoon, interval below 0, on both tasks | Typhoon stays the strongest measured; nothing changes for the paper's wording |
| either model's interval to Typhoon including 0 on a task | "no difference shown" on that task, reported with the interval width |
| loss mostly whole lines absent or loops (W1 attribution) | claim (2) extends to the model; for InternVL, to a third family |
| loss mostly misreads on correctly read bases | claim (2) does not hold for that model; reported as a counter-example |

Nothing here is a gate.

## 4. Budget, smoke, stopping

- **Estimate.** In M1, Qwen3-VL-4B took 2.6 GPU-hours for 178 items. SEA-LION
  is the same architecture, so a similar time, less if it loops less.
  InternVL is half the size: about 1 to 1.5 hours.
- **Queues.** One shard of each model per T4, about 2 to 3 hours per GPU.
  Deadlines: SEA-LION 3.0 h per unit, InternVL 2.0 h per unit, so no item
  starts later.
- **Cap: 10 T4-hours** of session time.
- **Smoke first: `--smoke 2`.** It checks:
  - dtype and finiteness, plus garbage or overflow in fp16 output (both
    checkpoints are bf16; InternViT in fp16 is the main risk);
  - `use_cache` and seconds per token;
  - the number of visual tokens per image (InternVL's tiling as in clearance
    §3);
  - that no image is written.

  If fp16 output is degenerate where fp32 is not, M6a stops and an addendum
  is written before any full run.

## 5. Not in scope

M6b's run (its own addendum), the locked split, any remedy, sampling, the
GitHub-format InternVL code path, and any claim beyond these checkpoints.

## Addendum 1, 2026-10-12 — M6b (DeepSeek-OCR-2), written before its smoke

No M6b output exists. Parameters: `configs/model_survey/m6b.yaml`. Clearance §4
gives the reasons for a separate runner.

**Question (d).** A third model family, built for OCR, with a different visual
encoding: about 256 tokens for a 1024 px global view plus 144 per 768 px crop,
up to 6 crops. Thai is not declared. Where does it fall against Typhoon, and
is its failure profile the same (claim (2))?

**What is M1's and what is not.**

| | M6b | M1 |
|---|---|---|
| items, split, image policy, scoring, comparison | M1's | |
| decoding | greedy, `max_new_tokens` 3072, `use_cache`, no n-gram ban | same |
| precision | fp16, fp32 fallback on non-finite first logits | same |
| attention | **eager** (the remote code offers eager or flash-attention 2; T4 has no FA2) | sdpa |
| environment | **own venv**: torch 2.6.0, transformers 4.46.3, tokenizers 0.20.3, as the card tested; `pip freeze` in each manifest | repository `uv.lock` |
| inputs | **`remote_m6b.prepare_inputs`**: infer()'s own steps (template `plain`, crop mode, base 1024, crops 768, BOS 0, image token 128815), using the model's own helpers, on the in-memory image | the processor's chat template |

What infer() does and M6b does not: reading the image from a file, bf16
autocast, `no_repeat_ngram_size` 20, `max_new_tokens` 8192. The n-gram ban is a
decoding remedy (T5 tested DeepSeek's processor as an arm); M1's protocol has
none, for any model.

**Prompts.**

- **Primary:** `CARD_PROMPT` = `Free OCR.`, the card's plain-text prompt
  ("without layouts"). The other card prompt, the grounding markdown one,
  emits `<|ref|>`/`<|det|>` box markup that extraction v2 does not handle.
- **Secondary:** `BENCHMARK_QUESTION`.
- Both are sent after DeepSeek's `<image>` placeholder and a newline.

**Outcomes and patterns.** As §2 and §3 for InternVL (question (b)): paired
against Typhoon, the base and Qwen3-VL-4B; the repeat-aware variant; W1's stop
and attribution; the markup audit.

**Smoke first: `--smoke 2`.** It checks:

- that the environment builds, the remote code loads at the pinned revision,
  and the visual token count matches the card's formula;
- fp16 finiteness, and fp16 output against the fp32 check of `--smoke-dtype
  float32` if fp16 looks degenerate;
- seconds per token;
- that no image is written.

**If a faithful run is not possible on a T4,** for example fp16 and fp32 both
degenerate, or the remote code failing in this environment, M6b reports that
and does not run a modified model.

**Budget.** Cap 8 T4-hours; 3.5 h deadline per shard, including about 5
minutes to build the environment.
