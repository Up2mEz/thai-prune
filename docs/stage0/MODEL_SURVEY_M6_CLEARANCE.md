# MODEL_SURVEY_M6 — clearance: SEA-LION v4 4B-VL, InternVL3.5-2B, DeepSeek-OCR-2

Checked 2026-10-12 by PELY334's Claude Code session, as the work split asks
(collab `20261011T1315Z_Up2mEz_to_PELY334_paper-prep-work-split.md`, W2, M6):
revisions pinned and cards snapshotted before any run, because cards can
change. This is a governance reading, not legal advice. Every revision below
was also the repo's head on 2026-10-12.

## 1. Identity and licence

| model | repo @ revision | licence | access | stored parameters (BF16) | base |
|---|---|---|---|---|---|
| SEA-LION | `aisingapore/Qwen-SEA-LION-v4-4B-VL` @ `d0734aa1b8113fce90997a83c1e4afe2c37c6205` | MIT (card metadata and `LICENSE`, "Copyright 2023 AI Singapore") | not gated, not private | 4,437,815,808 | `Qwen/Qwen3-VL-4B-Instruct` |
| InternVL | `OpenGVLab/InternVL3_5-2B-HF` @ `3f301ffcf3dcbb47893afae6650ea3e78d96fb6d` (§3) | Apache-2.0 (card metadata; the card's License section: Apache-2.0, with Qwen3 Apache-2.0) | not gated, not private | 2,348,347,392 | InternViT-300M + Qwen3-1.7B |
| DeepSeek-OCR-2 | `deepseek-ai/DeepSeek-OCR-2` @ `aaa02f3811945a91062062994c5c4a3f4c0af2b0` | Apache-2.0 (card metadata and `LICENSE.txt`) | not gated, not private | 3,389,119,360 | own (SAM-ViT-B and a Qwen2-style encoder; DeepSeek-V2-style decoder, per its code) |

Snapshots with SHA-256 are in `docs/stage0/data/cards/`:

- **`qwen-sea-lion-v4-4b-vl@d0734aa1b811/`.** `README.md` `8f3d9e00…`,
  `LICENSE` `151a5477…`, `config.json` `edac7703…`,
  `generation_config.json` `8469742d…`, `preprocessor_config.json`
  `27225450…`, `chat_template.json` `6f8a6a55…`, `hf_api_revision.json`
  `f4fc0ee4…`.
- **`internvl3_5-2b-hf@3f301ffcf3dc/`.** `README.md` `1c469775…`,
  `config.json` `7a441427…`, `generation_config.json` `b17e2c68…`,
  `preprocessor_config.json` `af09ffbe…`, `processor_config.json`
  `3511f4ae…`, `chat_template.jinja` `b3e3fa7c…`, `hf_api_revision.json`
  `53cd09e0…`.
- **`internvl3_5-2b@7d7bd7bcc35b/`** (the GitHub-format repo the work split
  named). `README.md` `ffdba847…`, `config.json` `a67c8ed5…`,
  `hf_api_revision.json` `553017d6…`.
- **`deepseek-ocr-2@aaa02f381194/`.** `README.md` `507812c8…`,
  `LICENSE.txt` `9debfe04…`, `config.json` `e2bb23b4…`,
  `processor_config.json` `0fe7ba9a…`, `hf_api_revision.json` `6ff1d85a…`.

Full hashes: `sha256sum docs/stage0/data/cards/*/*`.

## 2. SEA-LION: Qwen3-VL-4B's architecture, only the weights differ

At M1's revision of `Qwen/Qwen3-VL-4B-Instruct`
(`ebb281ec70b05090aa6165b016eac8ec08e71b17`):

- `config.json`, `preprocessor_config.json` and `chat_template.json` are
  **byte-identical**;
- the stored parameter count is identical (4,437,815,808).

SEA-LION therefore runs on M1's runtime unchanged, with the same visual
tokens per image as Qwen3-VL-4B. It gives the cleanest pair in the survey:
the same base, revision, processor and prompt, so a difference is the
fine-tune's. The fine-tune is described as about 9M instruction pairs in
English and seven SEA languages including Thai. OCR is not named as a
target.

What the run must watch:

- **Decoding.** `generation_config.json` samples (temperature 0.7, top_p
  0.8, top_k 20). M6 passes M1's greedy settings explicitly.
- **Prompt.** The card's quick-start uses a system message "You are a
  helpful assistant." and no OCR prompt. M6 keeps M1's setting for
  Qwen3-VL-4B: no system message, `BENCHMARK_QUESTION` only. That keeps the
  pair clean.

## 3. InternVL3.5-2B: the HF-format checkpoint, not the GitHub-format repo

The work split names `OpenGVLab/InternVL3_5-2B@7d7bd7bc`. That repo is the
GitHub format: `InternVLChatModel` via `trust_remote_code`, with its own
`chat()` API. M1's runtime (`AutoModelForImageTextToText` plus the
processor's chat template, transformers 5.12) cannot load it without remote
code.

OpenGVLab publishes both formats of every InternVL3.5 checkpoint. The card
says the HF format is "aligned with the official Transformers standard",
gives conversion scripts both ways, and lists `InternVL3.5-2B-HF` with
2.3B parameters. M6 uses the HF format:

- **Architecture.** `InternVLForConditionalGeneration`, native in
  transformers, no remote code.
- **Same model.** The stored parameter count is identical (2,348,347,392).
  The language config equals the GitHub repo's `llm_config` on every size
  field (hidden 2048, 28 layers, 16/8 heads, intermediate 6144, vocab
  151,936, `Qwen3ForCausalLM`). The vision tower is equal on hidden size
  1024, 24 layers, 448 px and patch 14. Downsample is 0.5 in both.
- **Image tiling as the original.** Checked locally with the pinned
  processor. A 1272 × 1800 page gives 7 tiles of 448 × 448 (6 crops plus a
  thumbnail), i.e. 1,792 visual tokens. Tiling is on by default, at most 12
  crops plus the thumbnail, as the GitHub format's `max_dynamic_patch: 12`
  and `use_thumbnail: true`.
- **One difference.** The GitHub format's `internvl2_5` template carries a
  default Chinese system message. The HF chat template has none
  (`<|im_start|>user\n<IMG_CONTEXT>…`). M6 runs the HF template as shipped.
- The HF card's `base_model` metadata reads `InternVL3_5-4B-MPO`. The config
  and parameter count are the 2B model's, so this looks like a metadata
  slip. It is recorded, not relied on.

Thai is not declared. Generation config sets only BOS/EOS. Greedy is M1's.

## 4. DeepSeek-OCR-2: cleared on licence; needs its own runtime path (M6b)

- **Licence and access.** Apache-2.0, not gated.
- **Runtime.** The card's tested setup is transformers 4.46.3,
  `trust_remote_code`, `flash_attention_2` and bf16. Inference goes through
  `model.infer(tokenizer, prompt, image_file=…)`, which:
  - reads the image from a **file path**;
  - autocasts to **bf16**;
  - decodes with `no_repeat_ngram_size` 20 or 35 and `max_new_tokens` 8192.
- **What a T4 cannot do, and what M1's protocol forbids:**
  - T4 has neither flash-attention 2 nor native bf16;
  - M1's protocol is greedy without an n-gram ban, at 3072 tokens;
  - ThaiOCRBench images must never be written to disk in outputs.
- **What M6b therefore needs:**
  - its own runner, in a separate environment pinned to the card's
    transformers;
  - remote code read before it runs, at the pinned revision;
  - preprocessing fed a PIL image in memory;
  - fp16, eager or sdpa attention, and M1's greedy decoding.

  This is engineering, and it gets its own smoke. If a faithful run is not
  possible on a T4, M6b reports that and does not run a modified model.
- **Prompts.** The card's are `<image>\nFree OCR.` (plain text) and
  `<image>\n<|grounding|>Convert the document to markdown.`. Thai is not
  declared.

## 5. Status

SEA-LION and InternVL3.5-2B (HF format) are cleared for a calibration-only
run under M1's protocol (`configs/model_survey/m6a.yaml`). DeepSeek-OCR-2 is
cleared on licence; its run waits on M6b's runtime and smoke. PELY334
authorized M6 in session on 2026-10-12 ("ทำทุกอันเลย", "do all of them").
