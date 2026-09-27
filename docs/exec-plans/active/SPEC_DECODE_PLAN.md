# Track A — speed without changing output (speculative decoding)

**Status: `PLAN_APPROVED_REGISTRATION_PENDING`.** Owner `PELY334`. Track agreed
in `collab/messages/20260927T1633Z_Up2mEz_to_PELY334_approve-track-a-defer-bcd.md`.
Authorizes no run: `SPEC_DECODE_S1` still needs its registration and a
human-approved `docs/DECISION_LOG.md` entry (`ONBOARDING.md` §6.2).

| | |
|---|---|
| package | `src/labbs2026/spec_decode/` |
| configs | `configs/spec_decode/` |
| scripts | `scripts/spec_decode_*.py` |
| worker | `infra/kaggle/spec_decode_worker.py` |
| registration | `docs/stage0/SPEC_DECODE_S1_REGISTRATION.md` (`DRAFT_FOR_REVIEW`) |
| branch | `PELY334/spec-decode` |

## 1. Question

RQ-B, latency half: can exact-verification speculative decoding reduce the
wall-clock of page OCR for `Qwen/Qwen3-VL-2B-Instruct@89644892e4d85e24eaac8bacfd4f463576704203`
and `typhoon-ai/typhoon-ocr1.5-2b@9c8a8fa14905041d793f1e4e922312147956dcc0` on a
Kaggle T4, **with greedy output byte-identical to plain greedy decoding**?

Why this and not pruning: at batch 1 on T4 decode dominates cost, ~10× its
memory-bandwidth floor (`docs/stage0/THAI_MARK_FAILURE_MODES.md` §8), and
post-encoder pruning shortened only prefill
(`docs/stage0/REGION_OCR_ROUND3_RESULTS.md`). A lossless speed lever composes
with any accuracy remedy from the plan's §4 or tracks B/D, because it leaves
the output unchanged.

## 2. What is already known (CPU, random weights, no benchmark data)

Checked against the locked `transformers==5.12.0`:

- `Qwen3VLForConditionalGeneration` is not a stateful model, so
  `generate(..., prompt_lookup_num_tokens=k)` reaches `_assisted_decoding`
  without error.
- On a 4-layer random-weight Qwen3-VL with DeepStack and interleaved M-RoPE and
  an image in the prompt, in fp32, prompt-lookup output matched plain greedy on
  6/6 seeded trials over 80 new tokens, with 19–59 target forward passes
  against 80 — drafts were genuinely accepted, not all rejected. Kept as
  `tests/test_spec_decode_identity.py`.
- Assisted decoding can return **one token past `max_new_tokens`**. Outputs are
  truncated to the budget before comparison
  (`labbs2026.spec_decode.identity.truncate_new_tokens`).

**Not known, and the main risk.** On T4 in fp16, verifying k draft tokens in
one forward pass runs different kernels from k single-token steps. Where the
top-2 logits are nearly tied, argmax can flip, and the outputs diverge.
"Byte-identical" is therefore the primary *measured* outcome of S1, not an
assumption. The CPU result above does not transfer to fp16 on GPU.

## 3. Drafters, in order

1. **Prompt lookup / n-gram, no extra model.** Page OCR repeats little of its
   prompt, so drafts come mostly from the model's own earlier output (repeated
   words, headers, numbers, form labels). The cheapest possible drafter; it
   sets the floor. → `SPEC_DECODE_S1`.
2. **HSD-style classical-OCR drafts** (arXiv:2602.12957, search-level only —
   not verified): run a classical Thai OCR engine on the same page and use its
   text as the draft source. Needs a licence check on the engine and its Thai
   model before registration. → a later test, only if S1 shows the pipeline is
   exact but slow to accept.

## 4. `SPEC_DECODE_S1` — summary (full text: `docs/stage0/SPEC_DECODE_S1_REGISTRATION.md`)

- **Inputs:** `typhoon-ai/ThaiOCRBench@ca610d1ab330`, Full-page OCR and Text
  recognition, **calibration split only**, reusing the seeded `thai_marks`
  split read-only (`labbs2026.thai_marks.split`). Locked split stays closed.
- **Prompt:** `TYPHOON_CARD` for both models, as T2 (registration §1 says why
  this replaces "T1's pinned prompt").
- **Arms:** plain greedy `REF` vs prompt lookup `PLD5` and `PLD10`; every arm
  run and reported, nothing chosen from data.
- **Primary outcome:** fraction of items whose output token ids equal the
  reference after budget truncation. Every mismatch is logged with position,
  dtype and the reference's top-2 logit margin there, and reported
  individually — as a bug or a numerical tie, never averaged away.
- **Secondary:** wall-clock per item, decode ms/token, acceptance rate, target
  forward passes. Both arms in the same kernel session, arm order alternated
  per item, a warm-up item discarded.
- **Recorded per run:** config, seed, model revisions, git SHA, environment,
  dtype actually used (fp16 with fp32 fallback, as T1), actual token counts
  (`AGENTS.md`).
- **Out of scope:** any accuracy claim (output is unchanged by design),
  sampling, batch > 1, GPUs other than T4, other models.
- **Claim level:** `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

## 5. GPU estimate

Rough, to be replaced by T1's measured seconds per item: three greedy passes
per item per model on the calibration items of two tasks, ≈ 6–12 T4-hours,
capped at 12 by registration §7, within PELY334's own 30 h/week.

## 6. Waiting on

1. Up2mEz's review of `docs/stage0/SPEC_DECODE_S1_REGISTRATION.md` (drafted;
   fixes `TYPHOON_CARD` as the prompt so it no longer waits on T1's choice).
2. A human-approved Decision Log entry for S1.
3. T1's measured seconds per item, only for the pre-registered budget rule
   (registration §7) — not for any design choice.
