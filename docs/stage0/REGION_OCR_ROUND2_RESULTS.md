# Region-OCR round 2 — results

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** Scope is text-region
recognition on Thai document images, one model, no sealed confirmatory split.
This approves no gate and confirms no hypothesis.

| | |
|---|---|
| run id | `kaggle-region-ocr-120b5adc9e90` |
| git sha | `120b5adc9e9071b89d41de11ca1878d0775e66bf` |
| model | `PaddleOCR-VL-1.6` @ `c5630ab`, float16, sdpa, Tesla T4 |
| observations | 7,600 (400 regions × 19 conditions), **0 execution failures** |
| wall time | 42.6 min |
| `path_equivalence` | `IDENTICAL` |
| `post_encoder_vision_cost_invariant` | `true` |
| registration | `docs/stage0/REGION_OCR_ROUND2_REGISTRATION.md`, approved 2026-09-21 |

---

## 1. Family A — post-encoder pruning degrades more than resolution reduction

`DiD_b = ΔCER(PRUNE_GRID, b) − ΔCER(RR, b)`, positive meaning pruning is worse.

| budget | primary (400 regions / 200 clusters) | secondary (159 / 124) |
|---|---|---|
| 75% | **+0.0567** [+0.0156, +0.0956] p=0.0060 | +0.0036 [−0.0369, +0.0409] p=0.8518 |
| 50% | **+0.1170** [+0.0741, +0.1740] p=0.0004 | **+0.0695** [+0.0252, +0.1271] p=0.0238 |
| 25% | **+0.2268** [+0.1656, +0.3011] p=0.0000 | **+0.1756** [+0.1294, +0.2302] p=0.0000 |

p-values are Holm-adjusted within the family. The effect is ordered and grows as
the budget tightens, in both populations.

### The confound that bounds this

**This contrast is not clean, and the reason is visible in the geometry
record.** These regions are small crops; the processor upsamples them to reach
its pixel floor. At `FULL` and at every post-encoder condition the median area
scale is **9.67×**. At `RR_25` it is **2.44×**.

So a matched-token comparison between `RR` and `PRUNE` is not only a comparison
of *where* compression happens. `RR` also hands the encoder a far less
interpolated image. The measured `DiD` therefore confounds the intervention
position with the amount of interpolation artefact present, and the two cannot
be separated by this design.

The same explanation now covers round 1's inversion: `RR_25` reaches macro CER
**0.1962** against `FULL`'s **0.2714** — the least-upsampled condition is the
most accurate one in the whole panel. That is much more readily explained by
interpolation damage at `FULL` than by compression improving recognition.

**Consequence:** family A may be reported as *pruning at a matched token budget
is worse than reaching that budget by reducing resolution*, which is a true and
useful engineering statement. It may **not** be reported as evidence that the
position of compression is what causes the difference. Isolating that requires a
design where both arms see the same amount of interpolation.

## 2. Family B — the damage is the token count, not the discarded content

`ΔCER(MERGE_GRID, b) − ΔCER(PRUNE_GRID, b)`, negative meaning merging is better.

| budget | estimate | 95% CI | p (Holm) |
|---|---|---|---|
| 75% | −0.0002 | [−0.0264, +0.0242] | 0.9887 |
| 50% | −0.0327 | [−0.0624, −0.0070] | 0.0582 |
| 25% | −0.0513 | [−0.1234, +0.0049] | 0.2240 |

**Null across the family.** The direction favours merging at the two tighter
budgets and the 50% interval excludes zero before correction, but nothing
survives Holm.

This contrast is clean in a way family A is not: merging and pruning select the
same survivors, at the same grid positions, from the same 9.67×-upsampled image.
The only difference is whether the discarded tokens' content is averaged into
the survivors or thrown away — and averaging it back in does not recover
accuracy.

Taken at this sample size, that points at the reduced token count as what the
model is losing, not the information carried by the removed tokens. It also
means that a post-encoder merge method has no headroom to beat a post-encoder
pruning method here, whatever its selection rule.

## 3. Family C — content-aware placement within a cell does nothing

`ΔCER(PRUNE_COVERAGE, b) − ΔCER(PRUNE_GRID, b)`.

| budget | estimate | 95% CI | p (Holm) |
|---|---|---|---|
| 75% | +0.0104 | [−0.0226, +0.0485] | 1.0000 |
| 50% | −0.0050 | [−0.0632, +0.0438] | 1.0000 |
| 25% | −0.0081 | [−0.0844, +0.0580] | 1.0000 |

Flat. Moving each cell's survivor onto its highest-contrast token changed
nothing measurable. Consistent with family B: if content is not what is lost,
choosing a better-content survivor cannot help.

## 4. The random baseline earns its place

Macro CER, both registered seeds reported:

| budget | `PRUNE_GRID` | `RANDOM` s…920 | `RANDOM` s…921 |
|---|---|---|---|
| 75% | 0.3087 | **0.2693** | 0.2886 |
| 50% | 0.3400 | 0.3060 | 0.3448 |
| 25% | 0.4231 | 0.4602 | 0.5560 |

At the mildest budget **random selection beats the structured grid policy**, and
one random seed (0.2693) edges out `FULL` itself (0.2714). At the tightest
budget random is clearly worse, and the gap between the two seeds (0.4602 vs
0.5560) is larger than most effects reported above.

Two things follow. The structured policy's advantage exists only at aggressive
budgets. And single-seed random baselines are not trustworthy at 25% — reporting
both seeds was the right call, and neither may be selected after the fact.

## 5. Efficiency — post-encoder pruning bought nothing measurable

Median seconds per stage, and peak allocation per observation:

| condition | vision | prefill | generate | vision patches | LLM visual tokens | peak MB |
|---|---|---|---|---|---|---|
| `FULL` | 0.046 | 0.021 | 0.234 | 640 | 160 | 1873 |
| `PRUNE_GRID_75` | 0.046 | 0.021 | 0.238 | 640 | 120 | 1864 |
| `PRUNE_GRID_50` | 0.046 | 0.021 | 0.234 | 640 | 80 | 1863 |
| `PRUNE_GRID_25` | 0.046 | 0.021 | 0.222 | 640 | 40 | 1863 |
| `RR_75` | 0.032 | 0.022 | 0.237 | 480 | 120 | 1863 |
| `RR_50` | 0.027 | 0.022 | 0.238 | 320 | 80 | 1853 |
| `RR_25` | **0.025** | 0.021 | 0.237 | **160** | 40 | 1843 |

Three findings, and the first is the one that matters:

1. **Prefill is flat at 21 ms across every condition**, including `FULL`. These
   sequences are short — 160 visual tokens at most — so prefill is a rounding
   error against the 234 ms of decode. Post-encoder pruning shortens only
   prefill. **At this scale it therefore saves nothing that can be measured**,
   while costing up to +0.23 CER. A stage-resolved instrument was required to
   see this; a single end-to-end latency would have shown only noise.

2. **Resolution reduction does cut encoder work**, 0.046 s → 0.025 s, exactly in
   proportion to its patch count (640 → 160). It is the only arm here that
   reduces compute at all.

3. **Peak memory is flat**, 1.84–1.87 GB. Weights dominate; activations for a
   sequence this short are negligible. No arm delivers a VRAM benefit.

`post_encoder_vision_cost_invariant: true` — every post-encoder condition
processed 640 patches regardless of budget, as it must. No whole-pipeline
speed-up may be quoted from any of these arms.

## 6. What this round does not support

- No claim that the *position* of compression causes family A's effect; see §1.
- No confirmatory claim of any kind: three families of three corrected
  separately, round-wide error rate uncontrolled, no sealed split.
- No accuracy-per-second trade-off. None was registered, and §5 shows the
  denominator is flat anyway.
- Nothing about `wayu-paxa-ocr-zero`, which was not run.
- Nothing about VisionZip, ET-Prune, FastV, SparseVLM, S²Prune, RTPrune or
  pre-encoder token dropping, none of which were implemented.
- Scene text against a document-trained model; single model family; regions
  drawn from the `train` split only.

## 7. What the next round should test

The binding limitation is now §1: every post-encoder condition sees a
9.67×-upsampled image and `RR` does not, so the two families differ in more than
their insertion point. Two ways forward, in order of value:

1. **Break the interpolation confound.** Add an arm that reduces tokens
   post-encoder while feeding the encoder the *same* image `RR` gets, or an `RR`
   arm forced to the same upsampling factor as `FULL`. Without one of these the
   central H3 contrast stays bounded.
2. **Move the cut into the decoder** (FastV/SparseVLM territory, insertion point
   after decoder layer *k*). Families B and C say post-encoder selection rules
   are exhausted here — nothing about *which* post-encoder tokens survive
   changed the outcome. A different insertion point is the remaining variable.

Running `wayu` before either of these would add a factor to a contrast that is
still confounded.
