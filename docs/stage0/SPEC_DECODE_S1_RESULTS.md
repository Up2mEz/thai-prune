# SPEC_DECODE_S1 — results (Track A)

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`** (calibration split
only). Registration: `docs/stage0/SPEC_DECODE_S1_REGISTRATION.md` with
addenda 1–3. Authorization: `docs/DECISION_LOG.md` 2026-09-28. Analysis:
`scripts/spec_decode_analyze.py` (registered §4–§5 and addendum 2), run on the
verified artifacts.

| | |
|---|---|
| full run | `kaggle-spec-decode-s1-46e16782627b`, commit `46e1678`, 2×T4, one model per GPU |
| items | 178 calibration items per model: 1 warm-up (excluded) + **177 timed** |
| prompt | `TYPHOON_CARD`, both models |
| precision | fp16 for both models (no fallback) |
| failures | 0; `SUCCESS.json` present; all checksums verified |
| wall time | base 5.66 h, typhoon 3.66 h, in parallel (budget estimate 6.50 T4-h, cap 12) |
| environment | `torch 2.14.0+cu130`, `transformers 5.12.0`, Tesla T4 |
| diagnostics (addendum 3) | `kaggle-spec-decode-s1-8a98b4d409d2-diag-float32`, `kaggle-spec-decode-s1-a477079ed71f-diag-fp16` |

## 1. Primary outcome — output identity (§4)

Outputs compared with `REF` token by token after cutting to
`max_new_tokens` (assisted decoding can overshoot by one).

| model | arm | identical to `REF` | mismatches | near-tie (≤ 0.1 logit) | above 0.1 | largest margin |
|---|---|---|---|---|---|---|
| base | `PLD5` | 156 / 177 (**88.1%**) | 21 | 21 | 0 | 0.047 |
| base | `PLD10` | 163 / 177 (**92.1%**) | 14 | 13 | **1** (0.125, §2) | 0.125 |
| typhoon | `PLD5` | 165 / 177 (**93.2%**) | 12 | 12 | 0 | 0.031 |
| typhoon | `PLD10` | 157 / 177 (**88.7%**) | 20 | 20 | 0 | 0.016 |

Every observed margin is a multiple of 2⁻⁷ or 2⁻⁶ — the resolution of fp16 at
logits of magnitude 16–64. Many are exactly 0.0: two candidate tokens with the
same fp16 logit.

**Claim, in §4's terms:** the outputs are **not** byte-identical to plain
greedy decoding. They are identical on 88–93% of items; every divergence occurs
at a position where `REF`'s own top-2 margin is at most 0.125 logit, i.e. a
tie or near-tie at fp16 resolution. No divergence indicates a logic error.

## 2. The one mismatch above the near-tie line (addendum 3)

Base, `PLD10`, item `149C5D04`: first divergence at generated token 205,
`REF` margin 0.125 logit (8 fp16 steps). Addendum 3 registered how it would be
explained before any diagnostic output:

| run | `PLD5` vs `REF` | `PLD10` vs `REF` | note |
|---|---|---|---|
| full run (fp16) | identical | diverges at 205 | |
| diagnostic, fp16 again | identical | **diverges at 205, margin 0.125** | all three arms token-identical to the full run: fp16 kernels are deterministic on this harness |
| diagnostic, **fp32** | identical | **identical** | fp32 `REF` is token-identical to fp16 `REF` (461 tokens); it is fp16 `PLD10` that departs |

This is the case addendum 3 stated as "reproduces in fp16 and vanishes in
fp32": an fp16 effect of verifying a 10-token draft in one batched forward.
It is reported as **1 mismatch at 0.125 logit, explained as fp16 numerics**,
and base `PLD10`'s speed is reported below. (Typhoon `PLD10` also diverges on
this item, at token 33 with margin 0.0, in both fp16 runs and not in fp32; it
is one of the 20 near-ties counted above.)

## 3. Secondary outcomes — speed (§5, addendum 2)

Geometric-mean speedup over `REF` and median acceptance (generated tokens per
target forward), each with an item-level bootstrap 95% interval (10,000
resamples, seed 20260927, within task); median decode ms/token.

**Populations.** Headline = `REF` neither reached `max_new_tokens` nor is
repetitive by T1's rule. The loop-aware sensitivity headline (addendum 2)
excluded **no further items** for either model, so it equals the headline.

| model | arm | population (n) | speedup | acceptance | ms/token arm vs `REF` |
|---|---|---|---|---|---|
| base | `PLD5` | **headline (88)** | **1.16 [1.10, 1.21]** | 1.33 [1.29, 1.38] | 31.9 vs 37.4 |
| base | `PLD5` | degenerate (89) | 2.81 [2.63, 2.98] | 4.03 [3.79, 4.33] | 12.2 vs 37.7 |
| base | `PLD10` | **headline (88)** | **1.21 [1.17, 1.26]** | 1.34 [1.30, 1.40] | 31.8 vs 37.4 |
| base | `PLD10` | degenerate (89) | 3.90 [3.56, 4.24] | 6.08 [5.46, 6.42] | 8.3 vs 37.7 |
| typhoon | `PLD5` | **headline (168)** | **1.14 [1.13, 1.16]** | 1.30 [1.28, 1.33] | 33.1 vs 38.5 |
| typhoon | `PLD5` | degenerate (9) | 2.52 [2.01, 3.14] | 2.97 [2.25, 4.12] | 16.1 vs 38.9 |
| typhoon | `PLD10` | **headline (168)** | **1.15 [1.12, 1.17]** | 1.31 [1.29, 1.35] | 33.1 vs 38.5 |
| typhoon | `PLD10` | degenerate (9) | 3.29 [2.39, 4.46] | 4.05 [2.11, 5.75] | 11.9 vs 38.9 |

Reading, as §5 stated in advance: the headline intervals lie above 1.0 for
both models and both draft lengths, so prompt lookup is a real speed lever for
Thai page OCR on this pair — **about 14–21% faster** on non-degenerate pages.
Combined with §1, it is "identical except at fp16 near-ties", not exactly
lossless. The much larger speedups are confined to the degenerate population
(loops, outputs that reach `max_new_tokens`), where n-gram drafting accepts
repeated text; they are reported as that, not as a speedup of OCR.

## 4. Exploratory, not registered

- **How far diverged outputs drift.** On mismatched items, the character edit
  distance between `REF`'s and the arm's text, divided by `REF`'s length, has
  median 0.06 (base `PLD5`), 0.13 (base `PLD10`), 0.20 (typhoon `PLD5`),
  0.23 (typhoon `PLD10`); 90th percentiles 0.25–0.68; one base `PLD5` item
  reaches 16.9 (the two decodes part ways and one enters a loop). Divergence
  happens at a median 22–55% of the way through `REF`. A near-tie at one token
  can therefore change much of the rest of a page. *(Corrected 2026-10-05,
  §4b: on text rather than raw HTML the median drift is 0.01–0.03 on Typhoon;
  the large values come from a few items.)*
- **What kind of token diverges** (added 2026-10-04 at Up2mEz's request,
  `collab/messages/20261004T0605Z_Up2mEz_to_PELY334_f1-addendum1-ok-pr38-track-d-review-s1-results.md`;
  CPU only, from the stored token ids; a token "has a mark" if its decoded
  text contains a Thai tone mark or upper/lower vowel):

  | model | `REF` tokens with a mark (base rate) | `REF` token at divergence has a mark: `PLD5` / `PLD10` | pairs differing only in marks | pairs involving a tone mark |
  |---|---|---|---|---|
  | base | 12.1% of 293,705 | 4/21 (19%) / 4/14 (29%) | 1 / 2 (e.g. `่า`→`้า`, `ี้`→`ี่`) | 3/21 / 5/14 |
  | typhoon | 22.4% of 123,736 | 0/12 (0%) / 1/20 (5%) | 0 / 0 | 0/12 / 1/20 |

  On the base, mark-bearing tokens are over-represented at near-tie
  divergences and some divergences are tone-mark swaps (`่`↔`้`): there,
  "identical except at fp16 near-ties" is **not neutral** for the errors this
  project cares about. On Typhoon — the primary model — divergences are almost
  never about marks; most are alternative Thai token boundaries (`ธร` vs `ธ`,
  `โอกาส` vs `โอกา`). Counts are a handful of events; direction only.
  *(Corrected 2026-10-05, §4b: the 12.1% base rate counts HTML tags; among
  Thai tokens alone the base's mark-bearing tokens are **not** over-represented
  at divergences. The tone-mark swaps remain.)*
- **Base with `TYPHOON_CARD` degenerates on half the pages** (89 / 177 reach
  `max_new_tokens` or repeat), Typhoon on 9 / 177. This matches the format and
  loop findings in `docs/stage0/OUTPUT_DIAGNOSTICS_NOTES.md`. *(Corrected
  2026-10-05, §4b: 83 base and 8 Typhoon outputs reach `max_new_tokens`; the
  other 6 + 1 are normal HTML tables flagged by T1's repetition rule.)*

## 4b. Markup check (added 2026-10-05, exploratory, not registered)

Audit first (`scripts/audit_markup.py`, run 2026-10-04 — this run was posted
before the audit tool existed, PR #53). `TYPHOON_CARD` asks for Markdown with
HTML `<table>`s, Thai picture descriptions in `<figure>` and `<page_number>`
tags; 163/178 base and 136/178 Typhoon outputs per arm carry tags, and T1's
normalization removes 20–22% (base) and 27–28% (Typhoon) of Thai characters
(structure-aware: 12% / 27–28%; on Typhoon the removed Thai is in blocks both
rules drop, e.g. picture descriptions). S1 makes no CER claim, identity is on
token ids and speed is per token, so §1–§3 are not affected by normalization.
Three parts of the analysis do read raw text. Code:
`src/labbs2026/spec_decode/markup_check.py` (tests
`tests/test_spec_decode_markup_check.py`), script
`scripts/spec_decode_markup_check.py`.

**1. The registered population split (§5).** T1's `is_repetitive` (a
20-character span 3 times in the last 200 characters) is applied to raw text,
so a normal table ending in repeated `</td></tr><tr><td>` counts as
repetitive. All items made degenerate by the rule rather than by the token
budget — base 6 (`2981C9B5`, `48F7EF29`, `B990A466`, `839D694C`, `35C470EE`,
`E317CF05`), Typhoon 1 (`60D954B1`) — are such tables: none reaches the
budget, `loop_period` finds no loop in raw or structure-aware text, and every
table row is distinct. The same rule on text:

| | registered (raw) | structure-aware text | tags stripped |
|---|---|---|---|
| base headline / degenerate n | 88 / 89 | 93 / 84 | 91 / 86 |
| base `PLD5` headline speedup | 1.16 [1.10, 1.21] | 1.16 [1.10, 1.21] | 1.16 [1.10, 1.21] |
| base `PLD10` headline speedup | 1.21 [1.17, 1.26] | 1.21 [1.17, 1.26] | 1.21 [1.17, 1.25] |
| base degenerate `PLD5` / `PLD10` | 2.81 / 3.90 | 2.95 / 4.18 | 2.89 / 4.07 |
| typhoon headline / degenerate n | 168 / 9 | 169 / 8 | 169 / 8 |
| typhoon headline `PLD5` / `PLD10` | 1.14 [1.13, 1.16] / 1.15 [1.12, 1.17] | same | same |
| typhoon degenerate `PLD5` / `PLD10` | 2.52 / 3.29 | 2.77 / 3.75 | 2.77 / 3.75 |

**The headline speedups do not change.** The text rules have their own false
positives (a company name three times in one row, `C652EC9B`; repeated cell
values), so the 200-character rule is fragile on tables in any form. Of the
outputs at the budget (base 83, Typhoon 8), `loop_period` finds a loop in 76 / 7
on raw text but only 38 / 6 on structure-aware text; mostly a detection
artifact: a cut-off tag at the end (e.g. `<page`) is not removed by
normalization and breaks the run-to-the-end test — dropping it gives 53 / 6.
Calling these items degenerate stands.

**2. Divergence-kind base rate (§4).** The 12.1% base rate is over all `REF`
tokens, 65.9% of which are not Thai (HTML tags, ASCII, digits, whitespace),
and 86.8% of the base's `REF` tokens come from the 83 outputs at the budget.
Among Thai tokens only:

| model | mark share among Thai `REF` tokens | at divergence, Thai tokens only: `PLD5` / `PLD10` |
|---|---|---|
| base | 35.6% (34–36% headline-only or item-mean) | 4/14 (29%) / 4/11 (36%) |
| typhoon | 31.3% (31–34%) | 0/12 / 1/16 (6%) |

Mark-bearing tokens are not over-represented at the base's divergences; some
divergences are still tone-mark swaps, so near-ties can change marks, but not
disproportionately. Typhoon's reading is unchanged.

**3. Drift (§4).** Edit distance over `REF` length, linear-interpolation p90:

| model, arm | n | raw median (p90) | structure-aware median (p90) |
|---|---|---|---|
| base `PLD5` | 21 | 0.06 (0.68) | 0.06 (1.00) |
| base `PLD10` | 14 | 0.13 (0.74) | 0.15 (1.00) |
| typhoon `PLD5` | 12 | 0.20 (0.39) | 0.01 (0.40) |
| typhoon `PLD10` | 20 | 0.23 (0.59) | 0.03 (0.33) |

The p90 values above differ from the "0.25–0.68" earlier in §4, which used
another quantile rule; with n = 12–21 a p90 rests on one or two items. On
Typhoon the median diverged output differs from `REF` by 1–3% of its text;
the tail is `0159AF30` (the paragraph-loop page, 0.41 / 0.60) and one ratio
inflated by a very short normalized `REF` per arm (`A3407ABE` 2.72,
`839D694C` 24.1). Inference: most of the raw-text drift on Typhoon is in
markup and picture descriptions, not in page text.

## 5. What this result does not show

- No accuracy or CER claim (registration §8). A diverged output is neither
  better nor worse by construction; this run does not score them.
- Not exact losslessness in fp16. fp32 removed the divergence on the one
  diagnostic item; fp32 speed was not measured.
- Only `TYPHOON_CARD`, Kaggle T4, batch 1, these two checkpoints of one
  architecture family; nothing about other prompts, GPUs or models.
- §6's cross-check of `REF` against T1's outputs is still pending: T1 has not
  posted. It will be added when it does.
- The degenerate-population speedups describe loops, not reading.

## 6. Directions (proposals, each would need its own registration)

1. **Exactness.** Whether "identical except at fp16 near-ties" is acceptable,
   or verification should run in higher precision (cost unmeasured), is a
   decision for the researchers.
2. **Bigger lossless gains need content-bearing drafts**: HSD-style drafts from
   a classical Thai OCR engine (plan §3), after a licence check.
3. **Interaction with loop stopping.** If loops are cut (Up2mEz's T5b, on an
   unmerged branch), the degenerate population shrinks and only the headline
   speedup remains relevant.
