# MODEL_SURVEY_M5 — clearance: Pathumma Vision 3.0.0-Re

Checked 2026-10-11 by PELY334's Claude Code session, as the work split asks
(collab `20261011T1315Z_Up2mEz_to_PELY334_paper-prep-work-split.md`, W2): the
revision is pinned and the card snapshotted before any run, because the card
can change. This is a governance reading, not legal advice.

## 1. Identity and licence

| | |
|---|---|
| repo | `nectec/Pathumma-llm-vision-3.0.0-re` |
| revision | `08bb11dcabf509ac3fa3ac0014ecd44eadb9729b` (created 2026-08-25, last modified 2026-08-28; Hugging Face API at this revision) |
| licence | `apache-2.0` in the card metadata; the repo has no separate LICENSE file |
| access | not gated, not private, not disabled |
| base | `Qwen/Qwen3-VL-2B-Instruct` (card `base_model`), the base T1 ran |
| weights | one `model.safetensors`, BF16, 2,438,696,960 stored parameters |

Snapshot at this revision, with SHA-256:
`docs/stage0/data/cards/pathumma-llm-vision-3.0.0-re@08bb11dcabf5/`

| file | SHA-256 |
|---|---|
| `README.md` (the card) | `3f739261bdf75df8689715b89fb604411385f31014f376521485dcbdd30c6fdb` |
| `config.json` | `bec4b3d446efa05807365c9e1cec03ac590836879d02f3a6da879971154bdd3b` |
| `generation_config.json` | `1e241830b48b397cb0900101421df5450baddc7adf01e5fc86b5615865f3bae4` |
| `hf_api_revision.json` | `64b0d3aa632555809d8e6860f48a3ad377bb197232080750e8df0951bfcfd3b9` |

## 2. Is it the base's architecture? Yes; only the weights differ

Compared with `Qwen/Qwen3-VL-2B-Instruct@89644892e4d85e24eaac8bacfd4f463576704203`
(T1's revision):

- `config.json`, `preprocessor_config.json`, `chat_template.json` and
  `tokenizer_config.json` are **identical**. The image processor, and
  therefore the number of visual tokens per image, is the base's.
- **Parameter count, 2.44B vs 2.13B.** Up2mEz guessed an untied `lm_head`.
  The checkpoint does store `lm_head.weight` (151,936 × 2,048 = 311M) next to
  `embed_tokens`. But `tie_word_embeddings` is `true`, and the two tensors are
  byte-identical in their first and last 4 MB, read by HTTP range from the
  pinned file. The extra 0.31B is a stored copy of the tied embedding:
  2.44B − 0.31B = 2.13B, the base's size. Same architecture.

## 3. What the run must watch (from the card)

- **Precision.** Trained with quantization-aware training; the card loads
  bf16. T4 has no bf16, so M5 runs fp16 with M1's rule: fp32 only if the
  first item's logits are non-finite. The smoke checks fp16 outputs for
  overflow or garbage.
- **Decoding.** `generation_config.json` samples (`do_sample` true,
  temperature 0.7, top_p 0.8, top_k 20). M5 passes M1's greedy settings
  explicitly, as M1 did for every model.
- **Prompt.** The card's Quickstart prompt is `อ่านข้อความในภาพนี้` ("read the
  text in this image"); it is M5's primary (`CARD_PROMPT`).
  `BENCHMARK_QUESTION` is secondary, as in M1.
- **Self-reported scores.** The card's ThaiOCRBench table gives 3.0.0-Re
  Full-page 0.7361 and Text recognition 0.6742 against Typhoon-OCR1.5-2B
  0.7724 and 0.5922. The metric is not stated. The table also lists a
  `3.0.0-preview` that is not this checkpoint. These are not our numbers and
  not comparable to order-free mark F1.

## 4. Status

Cleared for a calibration-only run under M1's protocol. PELY334 authorized the
run on 2026-10-11 (`configs/model_survey/m5.yaml`).
