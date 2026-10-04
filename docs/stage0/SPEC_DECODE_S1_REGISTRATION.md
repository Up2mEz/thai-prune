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

---

## Addendum 2, 2026-09-28 — written before the full run was submitted

No full-run output exists when this is written; the only S1 outputs are the
engineering smoke `kaggle-spec-decode-s1-be7333b19b85-smoke2` (2 timed items
per model, reported to Up2mEz).

**1. §7 budget input.** T1 has not posted. As proposed by Up2mEz in
`collab/messages/20260928T0221Z_Up2mEz_to_PELY334_spec-decode-full-run-no-t1-wait.md`,
"T1's measured mean seconds per item" is replaced, for this run only, by the
same quantity measured in the smoke under the identical condition (`REF`,
`TYPHOON_CARD`, same 2×T4 harness), timed items only, slower model:

| model | REF seconds per timed item | mean |
|---|---|---|
| base | 6.55, 111.21 | 58.88 |
| typhoon | 113.96, 61.42 | **87.69** |

Estimate = 178 × 87.69 × 3 ÷ 2 ÷ 3600 = **6.50 T4-hours ≤ 12** → all three arms
run; `PLD10` is not dropped. The formula and the 12-hour cap are unchanged.
§6's cross-check against T1's outputs is done later, once T1 posts.

**2. Added sensitivity analysis for §5 (headline population).** T1's
repetition rule (a 20-character substring three times in the last 200
characters) misses loops whose period exceeds 200 characters; a smoke output
repeated a whole paragraph to `max_new_tokens` without being flagged
(`docs/stage0/OUTPUT_DIAGNOSTICS_NOTES.md`, F4). The headline population stays
exactly as registered. In addition, and reported next to it, a **sensitivity
headline** further excludes items whose `REF` output has a trailing loop by
`labbs2026.output_diagnostics.structure.loop_period` (default arguments:
period 20–4000 characters, at least two back-to-back copies). If the two
headlines disagree on whether the interval lies above 1.0, both are reported
and the registered one is not preferred silently.

**3. Worker.** `infra/kaggle/spec_decode_worker.py` now writes each model's
process output to its log file instead of a pipe (the fix Up2mEz made to the
`thai_marks` worker in PR #16), so the two GPUs cannot silently serialize. No
change to what is computed.

---

## Addendum 3, 2026-10-04 — diagnostic for the one large-margin mismatch

Written after the full run (`kaggle-spec-decode-s1-46e16782627b`) and before
any diagnostic output. The registered analysis found, for the base model and
`PLD10`, one mismatch above the §4 near-tie line: item `149C5D04`, first
divergence at generated token 205, `REF` margin **0.125 logit** (all other 66
mismatches across both models and arms have margins ≤ 0.047). §4 says the speed
result is withheld until such a mismatch is explained; this addendum registers
how it is explained, nothing else.

What is already known from the records: `PLD5` on the same item is identical
to `REF`; the teacher-forced argmax at the divergence equals `REF`'s token;
every observed margin is a multiple of 2⁻⁷ or 2⁻⁶, i.e. fp16's resolution at
logits of magnitude 16–64, so 0.125 is 8 such steps.

**Diagnostic.** The same item alone (`--diagnostic-ids`, first rotation
entry `REF, PLD5, PLD10`, one warm-up item as registered), both models, twice:
(1) fp16 again — does the divergence reproduce at the same position; (2) fp32
(`--dtype float32`) — does it disappear.

**Reading, stated in advance.** Reproduces in fp16 and vanishes in fp32 → an
fp16 batched-verification effect; the §4 classification is reported as "1
mismatch at 0.125 logit, explained as fp16 numerics", base `PLD10` speed is
reported, and "identical except at N positions" stays the claim. Persists in
fp32 → treated as a pipeline bug; base `PLD10` speed stays withheld and the
cause is investigated before any further S1 claim. Does not reproduce in fp16
→ reported as nondeterministic fp16 kernels, base `PLD10` speed reported with
that caveat.
