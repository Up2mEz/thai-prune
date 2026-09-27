# SPEC_DECODE_S1 — registration

**Status: `APPROVED`**, `docs/DECISION_LOG.md` entry 2026-09-28. Track A, owner `PELY334`
(`docs/exec-plans/active/SPEC_DECODE_PLAN.md`). Written before any S1 output
exists. Authorized by that entry for the calibration split only.
Claim level of every result: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`
(calibration split only).

**Question.** Does prompt-lookup speculative decoding, verified exactly by the
target model, make page OCR faster on a Kaggle T4 while the greedy output stays
token-for-token identical?

## 1. Fixed inputs

Identical to T1 (`docs/stage0/THAI_MARKS_T1_T2_REGISTRATION.md` §1) except
where stated, so S1's reference arm reproduces T1's `TYPHOON_CARD` condition.

| | |
|---|---|
| base model | `Qwen/Qwen3-VL-2B-Instruct@89644892e4d85e24eaac8bacfd4f463576704203` |
| specialist | `typhoon-ai/typhoon-ocr1.5-2b@9c8a8fa14905041d793f1e4e922312147956dcc0` |
| benchmark | `typhoon-ai/ThaiOCRBench@ca610d1ab330`, CC-BY-SA-4.0 |
| tasks | `Full-page OCR`, `Text recognition` |
| split | T1's calibration split, reused read-only (`labbs2026.thai_marks.split`, seed 20260927); locked split not touched |
| prompt | `TYPHOON_CARD` only, SHA-256 `0e6c57af282f83f3dfdfa30e33bb8e74e0e1addd974f6ee111c1c22b3d47594d`, both models |
| image policy | T1's (`typhoon_card`: long side to 1,800 px if either side > 300 px, then `smart_resize`) |
| hardware | Kaggle 2×T4, one model per GPU, as the `thai_marks` worker |
| attention | `sdpa` |
| precision | fp16; fp32 only if the first item yields non-finite logits; recorded per run, never changed afterwards |
| decoding | greedy, `num_beams=1`, `max_new_tokens=3072`, batch 1 |
| library | `transformers==5.12.0` as locked in `uv.lock` |

**Why `TYPHOON_CARD` and not "T1's pinned prompt".** The identity question does
not depend on which prompt wins T1; `TYPHOON_CARD` is already the prompt T2 uses
for both models, and Typhoon's card states the model is meant to be used with
it. Fixing it now lets S1 be registered before T1 lands. If T1 leads the owner
to pin `BENCHMARK_QUESTION`, S1 is not re-run under it without a new
registration.

## 2. Arms

Every item is decoded under every arm, **in the same kernel session, on the
same GPU, from the same loaded model**.

| arm | `generate` arguments beyond §1 |
|---|---|
| `REF` | none — plain greedy |
| `PLD5` | `prompt_lookup_num_tokens=5`, `max_matching_ngram_size=2` |
| `PLD10` | `prompt_lookup_num_tokens=10`, `max_matching_ngram_size=2` |

No setting is chosen from data: every arm is run and reported. Arm order is
rotated per item (`REF,PLD5,PLD10` → `PLD5,PLD10,REF` → `PLD10,REF,PLD5`) by the
item's position in hash order, so no arm systematically runs on a warmer GPU.
One warm-up item (the first in hash order, excluded from every analysis)
precedes the timed items.

## 3. Recorded per item × arm

Output token ids and text; prompt length; generated tokens; whether
`max_new_tokens` was reached; wall-clock of `generate` (CUDA-synchronised
before and after); number of target language-model forward passes (counted by
a forward hook); peak allocated memory; dtype.

For `REF` only: seconds to first token, measured by a separate
`max_new_tokens=1` call, so decode time can be separated from prefill.

Also recorded per run: config and its SHA-256, seed, model revisions, git
commit, `uv.lock` hash, `torch`/`transformers`/CUDA versions, GPU name.

## 4. Primary outcome — output identity

For each item and each speculative arm, both outputs are cut to
`max_new_tokens` generated tokens (`labbs2026.spec_decode.identity.truncate_new_tokens`;
assisted decoding can overshoot by one) and compared token by token
(`compare_outputs`).

- **Identity rate** per model × arm = share of items identical to `REF`.
- **Every mismatch is reported individually**: item, first divergent position,
  the two tokens, and `REF`'s top-1 minus top-2 logit margin at that position,
  obtained by one teacher-forced forward over `REF`'s own output. Mismatches
  are not averaged into a rate and forgotten.

**What it means, stated in advance.**

- Identity rate 1.0 → exact verification holds on this stack in practice.
- Mismatches all at small `REF` margins (≤ 0.1 logit) → numerical near-ties from
  batched-verification kernels in fp16, not a logic error. Reported as such,
  with their count; the speed result still stands but "byte-identical" is not
  claimed — "identical except at N near-tie positions" is.
- Any mismatch at a large margin (> 0.1 logit) → treated as a bug in the
  pipeline. The speed result is withheld until it is explained.

The 0.1-logit line is descriptive, chosen before any output, and mirrors T2's
fp16 consistency tolerance order of magnitude; it is not a significance test.

## 5. Secondary outcomes — speed

Per item: **speedup** = `REF` wall-clock ÷ arm wall-clock; **acceptance** =
generated tokens ÷ target forward passes (1.0 means no draft was ever
accepted); decode ms/token.

Reported per model × arm: geometric-mean speedup and median acceptance, each
with an item-level bootstrap 95% interval (10,000 resamples, seed 20260927,
stratum proportions kept, as T1/T2 §6).

**Pre-registered sub-populations**, because repetition inflates prompt lookup:
a degenerate output that loops is exactly what n-gram drafting accepts best.

1. all timed items;
2. items where `REF` did **not** reach `max_new_tokens` and is **not**
   repetitive by T1's rule (last 200 characters contain a 20-character
   substring three or more times) — **the headline population**;
3. the complement of (2), reported separately and never pooled into the
   headline.

**What it means, stated in advance.**

- Headline speedup interval above 1.0 with identity as in §4 → prompt lookup
  is a free speed lever for Thai page OCR on this pair; it composes with any
  accuracy remedy.
- Headline interval covering or below 1.0 → n-gram drafting does not pay for
  its verification overhead on non-degenerate Thai OCR output; a drafter with
  real content (HSD-style, plan §3) is the next test, not a larger k.
- Speedup confined to population (3) → the gain comes from degenerate outputs,
  and is reported as that, not as a speed-up of OCR.

## 6. Cross-check against T1

`REF` repeats T1's `TYPHOON_CARD` condition. Where T1's raw output for the same
item and model is available, the share of `REF` outputs textually identical to
it is reported. Disagreement is expected to be small but non-zero (a different
session, possibly a different dtype outcome); it is a reproducibility
observation, not a gate.

## 7. Budget and stopping

Before submission, estimated T4-hours = (calibration items) × (T1's measured
mean seconds per item for `TYPHOON_CARD`, larger of the two models) × 3 arms,
divided by 2 because the two models run in parallel. If that exceeds **12
hours**, `PLD10` is dropped — decided from T1's timings, before any S1 output
— and the drop is recorded in the run spec. No other change is permitted
without an addendum.

The run fails closed (`FAILURE.json`, no analysis) on: a non-finite logit after
the dtype decision; any exception inside `generate`; a `REF` output whose token
count differs between the timed call and the margin forward pass.

## 8. Not in scope

Any accuracy or CER claim (outputs are identical by design); sampling;
batch > 1; GPUs other than T4; `BENCHMARK_QUESTION`; Fine-grained and
Handwritten tasks; the locked split; any drafter other than prompt lookup;
any claim about VLMs beyond these two checkpoints of one architecture family.

## 9. Known engineering facts this relies on

- `Qwen3VLForConditionalGeneration` is not stateful, so `transformers` allows
  assisted decoding on it.
- Qwen3-VL caches `rope_deltas` on the model (ONBOARDING §9). Each `generate`
  call starts from an empty cache, which recomputes it from the item's own
  image grid; the arms therefore cannot inherit each other's offsets. Checked
  on a random-weight model in `tests/test_spec_decode_identity.py`.
- The CPU fp32 check says nothing about fp16 on T4; that is what §4 measures.

---

## Addendum, 2026-09-28 — written before any S1 output existed

The first smoke that reached inference (`kaggle-spec-decode-s1-86cf28ec3e85-smoke2`,
both models) failed inside the first `PLD10` `generate` with
`Image features and image tokens do not match, tokens: 2361, features: 2352`.
No record was written.

**Cause.** `transformers`' `PromptLookupCandidateGenerator` searches the whole
sequence, image placeholders included. Qwen's chat template puts `"\n"` just
before `<|vision_start|>` and ends the prompt with `"\n"`, so the one-token
match proposes `<|vision_start|>` followed by nine `<|image_pad|>` as the
draft; verifying it presents more image tokens than image features.
Reproduced on a random-weight model in
`tests/test_spec_decode_runtime.py::test_unfiltered_prompt_lookup_drafts_image_tokens_and_crashes`.

**Change.** In the `PLD*` arms every draft is cut at its first image/video
placeholder or delimiter token (`labbs2026.spec_decode.runtime.drafts_without`,
ids from the model config). A draft cut to zero length means no draft at that
step, i.e. an ordinary greedy step.

**What it does not change.** The target model's inputs, logits and greedy choice;
`REF` (no drafting) and the registered parameters `prompt_lookup_num_tokens`,
`max_matching_ngram_size`. Every §4–§7 rule stands. The only possible effect is
on acceptance and speed: drafts that would have started at a placeholder are
not tried, which could only be rejected anyway because a greedy OCR output
never emits image placeholders.
