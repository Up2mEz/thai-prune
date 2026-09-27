# T1 and T2 — registration

**Status: `APPROVED`**, `docs/DECISION_LOG.md` entry 2026-09-27c. Written before
any output of either test exists. Claim level of every result:
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE` (calibration split only).

## 1. Fixed inputs

| | |
|---|---|
| base model | `Qwen/Qwen3-VL-2B-Instruct@89644892e4d85e24eaac8bacfd4f463576704203` |
| specialist | `typhoon-ai/typhoon-ocr1.5-2b@9c8a8fa14905041d793f1e4e922312147956dcc0` |
| benchmark | `typhoon-ai/ThaiOCRBench@ca610d1ab330`, CC-BY-SA-4.0 |
| tasks | `Full-page OCR`, `Text recognition` |
| hardware | Kaggle Tesla T4 |
| attention | `sdpa` |
| decoding | greedy, `num_beams=1`, `max_new_tokens=3072` |

**Precision.** T4 has no native bf16. Each run loads fp16 and checks, on its
first item, that every logit is finite; if not, it reloads in fp32. The dtype
actually used is recorded per run and is not changed afterwards.

**Image policy, both models, both tests.** Typhoon OCR 1.5's card policy: if
either side exceeds 300 px, resize (LANCZOS) so the long side is 1,800 px; then
the processor's own `smart_resize` (factor 32, floor 65,536 px). Applied to the
base as well, so both models receive identical visual tokens; without it the
base would receive ~12,000 tokens for a 12 MP photograph.

## 2. Split

Seeded, stratified by (`Task`, `category`). Within each stratum items are
ordered by `sha256("20260927:" + Id)` and the first `ceil(0.30 × n)` form the
**calibration** split; the rest are **locked**. The split is computed and
written to the artifacts before any inference. Only calibration items are run.

## 3. Prompts

- `TYPHOON_CARD` — the prompt block from the pinned model card, 991 characters,
  SHA-256 `0e6c57af282f83f3dfdfa30e33bb8e74e0e1addd974f6ee111c1c22b3d47594d`.
- `BENCHMARK_QUESTION` — the item's own `question` field.

## 4. T1 — FULL baseline

**Runs:** 2 models × 2 prompts × every calibration item.

**Recorded per observation:** raw output; generated tokens; whether
`max_new_tokens` was reached; visual tokens; image sizes before and after
resizing; seconds for processing, prefill-inclusive generation and decode;
peak allocated memory.

**Analysed offline, rules fixed here:**

1. *Normalization*, applied identically to reference and hypothesis: remove
   `<figure>…</figure>` blocks; replace `<page_number>X</page_number>` with X;
   `<br>` to space, all other HTML tags removed keeping their text; remove
   line-initial Markdown heading markers, `**`, `__` and backticks; remove
   LaTeX `$` delimiters keeping content; replace `|` with space; collapse all
   whitespace to single spaces and strip. No Unicode normalization; NFC is a
   sensitivity analysis only.
2. *CER*, macro and micro, on normalized strings.
3. *Component decomposition*: per reference tone mark, upper vowel and lower
   vowel — correct, deleted, replaced by the same class, replaced by another
   character — by codepoint Levenshtein backtrace.
4. *Mark-specific error*: error of a mark whose base consonant was read
   correctly, as in `THAI_MARK_FAILURE_MODES.md` §7.
5. *Generation health*: truncation rate and a repetition rate (share of outputs
   whose last 200 characters contain any 20-character substring three or more
   times).
6. *Speed*: seconds per generated token.

Deferred, with reason: the non-word / real-word split needs a Thai lexicon
whose licence is not yet checked; outputs are saved so it can be computed later
without re-running. The benchmark's BMFL score is computed only if its scorer
can be obtained under compatible terms.

## 5. T2 — oracle mark-variant scoring

No generation. Prompt `TYPHOON_CARD` for both models.

**Sites**, from each calibration reference (after collapsing whitespace only):

| class | site | variants |
|---|---|---|
| `TONE` | a reference tone mark | none, ่, ้, ๊, ๋ |
| `UPPER` | a reference upper vowel | none, ั, ิ, ี, ึ, ื, ็ |
| `LOWER` | a reference lower vowel | none, ุ, ู |
| `TONE_ABSENT` | a consonant with no mark after it, followed by a non-mark character | none, ่, ้, ๊, ๋ (reference = none) |

Per item at most 24 `TONE`, 12 `UPPER`, 8 `LOWER` and 12 `TONE_ABSENT` sites,
drawn by `random.Random("20260927:" + Id)`. Consonants are never altered.

**Scoring.** The reference is teacher-forced after the prompt. For each site,
let *b* be the start of the reference token containing it. Each variant's
*window* is the reference text from *b* to eight characters past the site with
only the site's mark changed. Its score is the summed log-probability of the
window's tokens given the prompt and the reference tokens before *b* — computed
twice, **with the image** and **without it**. Every variant of a site is scored
under the same scheme, so tokenization differences affect all alike.

Positions are passed explicitly: the prefix's M-RoPE positions come from the
processor's `get_rope_index`, and continuation tokens take the next positions.
The model's cached `rope_deltas` is never relied on.

**Consistency guard, fail-closed.** On the first site of every item, the cached
continuation score of the reference window is recomputed by a fresh, uncached
forward over the same tokens. The run stops if any per-token log-probability
differs by more than 0.1 nats (fp16) or 0.001 (fp32).

**Recorded per site:** item, class, character index, reference variant, every
variant's two scores and token count.

**Analysed offline:**

1. *Oracle accuracy* — share of sites where the reference variant scores
   highest with the image.
2. *Prior accuracy* — the same, without the image.
3. *Image gain* of the reference variant — image score minus no-image score.
4. *Contrastive accuracy* at λ ∈ {0.5, 1.0}: argmax of
   `score_image − λ·score_no_image`.
5. *Greedy accuracy* at the same sites, from T1 with `TYPHOON_CARD`.

**What the comparison means, stated in advance.** Oracle accuracy well above
greedy accuracy means the evidence is in the model and a decoding-time remedy
has headroom. Oracle close to greedy means it is not, and the remedy must act
on the input. Prior accuracy close to oracle accuracy, with low image gain,
means the language model is deciding marks without the image.

## 6. Uncertainty

Item-level bootstrap, 10,000 resamples, seed 20260927; stratum proportions kept.
Every comparison is reported with its interval. No test is confirmatory.

## 7. Not in scope

Any remedy, any compression arm, the locked split, Fine-grained and
Handwritten tasks.
