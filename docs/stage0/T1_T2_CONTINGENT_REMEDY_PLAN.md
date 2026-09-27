# What to build next, for each way T1/T2 could come out

**Status: `PLANNING_NOTE`, written before T1/T2 results exist.** No remedy here
is authorized to run. This exists so the choice of what to build next is made
by a rule fixed in advance, not by which explanation looks best once the
numbers are visible — the same discipline `docs/DECISION_LOG.md` entries and
`docs/stage0/*_REGISTRATION.md` files already apply to every run.

Every branch below cites literature located today (2026-09-28), in addition to
`docs/stage0/BEYOND_PRUNING_LITERATURE_SCAN.md`. All of it is search-level:
existence confirmed, abstracts and select sections read via fetch, nothing
verified in full. Nothing here may be cited in a paper before `ref-verify`.

## 1. The four numbers that route every decision

For each model × mark class (TONE, UPPER, LOWER), from the registered T1/T2
analysis (`src/labbs2026/thai_marks/analysis.py`):

| quantity | source | question it answers |
|---|---|---|
| **headroom** = `oracle_accuracy − greedy_accuracy` | T2 vs T1 at the same sites | does re-scoring the few legal variants recover anything greedy decoding misses? |
| **image_gain** = `oracle_accuracy − prior_accuracy` | T2 `oracle`/`prior` | does the image carry information the language prior does not already have? |
| **oracle_accuracy** on its own | T2 `oracle` | is the correct variant even reachable by scoring, or is it not favoured under *any* conditioning? |
| **real_word_share** of mark errors | T1 lexical split (`labbs2026.thai_marks.lexicon`) | when wrong, does the output land on another real word (prior-shaped) or on no word at all (perception-shaped)? |

Compare each across TONE vs UPPER/LOWER, and across base vs Typhoon.

## 2. Decision tree

```
headroom large (oracle >> greedy)?
├── YES
│   ├── image_gain large, prior_accuracy low
│   │     → §3.A: build the registered decoding-time remedy as planned.
│   │       This is the plan's original best case.
│   └── image_gain small, prior_accuracy ≈ oracle_accuracy
│         → §3.A still worth building (cheap, exact), but expect most of
│           the gain to come from collapsing to the globally likely answer,
│           not from the image — say so plainly, do not claim a vision fix.
└── NO (oracle ≈ greedy)
    ├── oracle_accuracy itself low, image_gain flat
    │     → §3.B: the evidence is not in the representation at all.
    │       A decoding-time remedy has nothing to re-score. Move to an
    │       input-side or representation-level intervention.
    └── oracle_accuracy already high (both oracle and greedy do well)
          → no remedy needed at these sites; narrow the claim to the
            sites that remain wrong and re-run this tree on them alone.
```

Cross-cutting, checked regardless of which branch:

- **real_word_share high** at sites with low headroom → consistent with the
  language prior dominating regardless of scoring method (§3.C).
- **Typhoon shows lower image_gain / higher prior_accuracy than the base** at
  matched sites → RQ-C supported directionally: specialization increased
  reliance on the prior. Route to §3.C and §3.D specifically for Typhoon.
- **Typhoon shows the same or better image_gain** → RQ-C not supported by this
  measure; the earlier "prior-override is worse in OCR specialists" finding
  (`docs/exec-plans/active/QWEN3VL_TYPHOON_EXPERIMENT_PLAN.md` §1, citing
  arXiv:2605.27750) does not replicate here, and that should be reported as a
  finding in its own right, not smoothed over.

## 3. The remedy families, one per branch

### 3.A — Mark-constrained, image-contrastive re-scoring (already planned)

Unchanged from `QWEN3VL_TYPHOON_EXPERIMENT_PLAN.md` §4. T2 *is* this method's
upper bound already measured; if headroom is large, building it is mostly
engineering, not research risk.

### 3.B — The evidence isn't in the representation: new candidates found today

Two failure shapes fall under "oracle_accuracy low, image_gain flat", each
pointing at a different fix:

**B1. Visual embeddings over-aligned with the text manifold.**
["When Language Overwrites Vision"](https://arxiv.org/abs/2605.08245) traces
VLM hallucination to visual embeddings being pulled so far toward the text
manifold during modality bridging that linguistic bias concentrated in a
"universal, dataset-agnostic text subspace" comes to dominate fine-grained
visual evidence. **This is a mechanism, not just a symptom-description** — and
it predicts exactly the pattern in this branch: a low, flat image_gain even
though the model is evidently capable of reading text (it reads consonants
fine). The paper's own remedy is **training-free**: project that identified
linguistic subspace out of the visual embeddings before they reach the
language model, adding no inference-time cost by their account. This is a
positive intervention a diagnosis-only ablation (like G1's DeepStack study)
does not give us, and is worth registering as its own probe if this branch is
reached: does projecting out the subspace raise image_gain at mark positions
specifically, more than at consonant positions?

**B2. Consensus voting across the scale axis this project already measured.**
Round 3 found a real magnification U-curve on the earlier backbone
(`docs/stage0/REGION_OCR_ROUND3_RESULTS.md` §1): accuracy depends on
rendering scale, with a real optimum away from the model's default. Separately,
["Consensus Entropy"](https://arxiv.org/html/2504.11101v4) and
["Geometric Risk Control"](https://arxiv.org/html/2603.19790) both show that
re-rendering an image under mild transforms (crop, scale) and voting across
the resulting transcriptions catches errors a single pass does not — Geometric
Risk Control reports a 112× reduction in severe errors at ~90% coverage on
scene-text OCR, using exact-match consensus across views rather than any
learned signal.

**A genuinely new combination, not published as such anywhere found today:**
render the page at two or three scales bracketing the project's own measured
optimum (G3 in `QWEN3VL_TYPHOON_ARCHITECTURE_GAPS.md`), but only re-run
generation **at the sites T2 already flagged as uncertain** — a handful of mark
positions per page, not the whole page — and take the majority codepoint at
each. This is training-free, uses only work this project has already done
(the scale curve, the site sampler), and turns two published ideas (consensus
voting; scale sensitivity) plus one internal finding into a targeted, cheap
remedy rather than the expensive whole-page multi-pass their papers use. Worth
naming and registering only if branch B is actually reached — do not build it
speculatively.

### 3.C — The language prior dominates: attention and geometric interventions

If real_word_share is high and prior_accuracy is close to oracle_accuracy
regardless of headroom, three training-free levers target the prior directly,
already in the plan's §2 table plus B1 above:

- PAI ([arXiv:2407.21771](https://arxiv.org/abs/2407.21771)) — amplify
  attention to image tokens at inference time.
- The subspace projection of §3.B(B1), which is specifically about the prior
  overwriting the image rather than about missing detail — the same
  intervention answers both this branch and B1; which one is live depends on
  whether oracle_accuracy is high (§3.C) or low (§3.B) when prior dominance is
  observed.
- OCR-head sink-token redistribution
  ([arXiv:2505.15865](https://arxiv.org/abs/2505.15865)) — reported to improve
  performance by redistributing attention mass within heads already identified
  as doing the copying; untested on diacritics.

### 3.D — Specialization actively hurt grounding: a route, not a fix

If Typhoon is measurably worse than the base on image_gain, the literature on
**catastrophic forgetting of visual grounding under instruction fine-tuning**
is directly relevant context (search-level; not yet read past abstracts):
fine-tuning "erases upstream image-understanding skills"
([SMoLoRA](https://arxiv.org/pdf/2411.13949) on dual catastrophic forgetting;
general MLLM forgetting surveyed in
[arXiv:2309.10313](https://arxiv.org/pdf/2309.10313)). None of this proposes a
training-free fix — the fixes in that literature are training-time
(dual-expert architectures, replay). The training-free analogue available to
us is **routing between the two models**: use the base's output at a site
where Typhoon's image_gain is low and the base's is not, in the spirit of
Consensus Entropy's "trust the ensemble when models disagree" rule, but keyed
to the per-site signal T2 already computes rather than to a separate agreement
metric. This is only worth registering if §RQ-C's asymmetry is confirmed; it
answers "what to do about it," not "why it happens."

### 3.E — Detect and flag instead of fix (a different notion of "fewer errors")

Selective prediction — abstain on likely-wrong transcriptions rather than
correct them — is a different shape of answer to "fewer errors" than the
project has scoped so far: it reduces the error rate *among outputs kept*, at
the cost of not answering some. Two training-free-compatible options:

- Geometric Risk Control (above) — no learned parameters, black-box, but needs
  multiple re-renders per accepted item, so its cost is closer to §3.B(B2)
  than to a cheap post-hoc check.
- Latent Representation Probes
  ([arXiv:2511.19806](https://arxiv.org/html/2511.19806)) — stronger
  (75.0% vs. 68.0% abstention accuracy against self-consistency on English
  OCRBench v2/SEED-Bench-2-Plus/HierText/EgoTextVQA) but **requires trained
  probes on labelled error data**, so it is not training-free by this
  project's own constraint unless the probe is trained on data separate from
  the calibration/locked split — a scope question for the humans, not a
  technical one.

Flag this family to the researchers explicitly: whether "fewer errors" as
stated permits abstention is a decision, not an inference I should make.

## 4. What this note does not do

It does not choose a branch — T2 has not run. It does not register any test;
whichever branch is reached still needs its own
`docs/stage0/<name>_REGISTRATION.md` before any inference, per
`ONBOARDING.md` §6.2. It does not resolve whether abstention (§3.E) is in
scope — that is for the researchers to decide when the results are in front of
them, not before.
