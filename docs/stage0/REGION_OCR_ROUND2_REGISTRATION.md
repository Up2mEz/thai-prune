# Region-OCR round 2 — registration of two new post-encoder arms and of cost measurement

**Status: `APPROVED` — human approval recorded in `docs/DECISION_LOG.md`,
entry 2026-09-21.**
This document was written before the run, not after, so that what was decided in
advance can be distinguished from what was decided once the numbers were
visible. It was held `PENDING_HUMAN_APPROVAL_NOT_IN_EFFECT` until that entry was
made.

Round 1 (`kaggle-region-ocr-44109c662d84`, 400 regions × 13 conditions) compared
one family of interventions against another: Input Resolution Reduction against
post-encoder Token Pruning, matched per region on the number of visual positions
the language model receives. This round adds two further post-encoder policies
and, separately, the cost instrumentation that round 1 could not support.

---

## 1. Why round 1 cannot answer the efficiency question

Round 1 recorded one wall-clock number per observation, measured around
`generate()`. Those numbers must not be compared across families, for a reason
that has nothing to do with noise: **the families did not run the same code.**
`FULL` and `RR` handed `pixel_values` to `generate()` and let it drive the vision
tower internally; pruning ran the tower itself and passed `inputs_embeds`. A
difference between two different call graphs is not a measurement of the
intervention.

Round 1 also recorded a single process-wide peak allocation for the whole job,
which cannot be attributed to any condition.

Both defects are in the instrument, not in the result. The round 1 accuracy
findings stand; its timings are withdrawn from any comparative use.

## 2. Change to the execution path, and the check that guards it

Every family now walks the identical path: run the vision tower explicitly,
build embeddings and M-RoPE positions explicitly, apply a selection (the
identity, for `FULL` and `RR`), and call `generate(inputs_embeds=...)`.

This makes cross-family timing meaningful. It also carries a risk that must not
be waved through: if routing `FULL` through `inputs_embeds` changes what the
model emits, then the `FULL` baseline recorded in round 2 is not the same
quantity as the one recorded in round 1, and every delta measured against it
silently changes meaning.

`assert_path_equivalence` therefore runs both routes on a real region under
greedy decoding and **requires character-identical output** before any
observation is written. The run fails closed if they differ, and the result is
recorded in the run manifest as `path_equivalence`.

## 3. Cost measurement

Timing is resolved into stages rather than reported as one total, because the
two things that matter move in opposite directions:

| Stage | What it is | Can a post-encoder method reduce it? |
|---|---|---|
| `processor` | image preprocessing on CPU | no |
| `vision` | vision tower + projector | **no, by construction** |
| `select` | the intervention itself | it *is* the added cost |
| `embed` | embedding + M-RoPE positions | no |
| `prefill` | one forward over the staged sequence | **yes — this is the whole saving** |
| `generate` | full greedy decode | partly, and confounded |

`generate` is confounded because its length is an *outcome* of the
intervention: a condition that degrades into emitting two tokens instead of
forty looks fast. `prefill` is the part an intervention can legitimately
shorten, so it is measured on its own pass.

CUDA is asynchronous; every stage synchronises on entry and exit, or the timer
measures queue submission rather than work. Peak allocation is captured per
stage via reset-and-read, and stages are forbidden to nest so the readings
cannot overlap.

Alongside the clock, each observation records exact counters that do not depend
on hardware or contention: `vision_patches`, `vision_tokens_after_merge`,
`llm_prefill_positions`, `llm_visual_positions`. **Any efficiency claim rests on
these; the seconds are illustrative.** Wall clock on a shared T4 is not
reproducible and will not be presented as though it were.

The report asserts `post_encoder_vision_cost_invariant`: within a region, every
post-encoder condition must process the same number of vision patches. This is
not a diagnostic that might fail — it is the definitional statement that
post-encoder pruning cannot make the encoder cheaper, made checkable. A
whole-pipeline speed-up must never be quoted from a language-model-only saving.

## 4. The two new arms

### 4.1 `MERGE_GRID` — post-encoder spatial merge

**This is not ToMe and will not be described as ToMe.** Token Merging as
published (arXiv:2210.09461) merges tokens *between the layers of the vision
transformer*. Averaging the projector's output afterwards is a different
operation at a different insertion point. Borrowing the name would claim a
reproduction that has not been performed. The name states where it acts.

Construction: the grid is partitioned by assigning every token to its nearest
`PRUNE_GRID` survivor (Euclidean on row/column, ties to the lower ordinal). Each
survivor's feature vector is replaced by the mean of its cell.

The survivors, their count, and their M-RoPE positions are **identical to
`PRUNE_GRID`** — `select_keep_indices` returns the same tuple for both, and a
test asserts it. The only difference between the two conditions is what the
surviving vectors contain.

That isolation is the point. If merging is better than pruning at the same
budget, the damage pruning causes is the *discarded content*. If they are
indistinguishable, the damage is the reduced token count itself. No other
comparison in this design separates those two.

### 4.2 `PRUNE_COVERAGE` — coverage-preserving, content-aware selection

`PRUNE_GRID` guarantees spatial coverage but is blind to content: its
representative can land on background while the glyph sits one token away. Small
Thai marks — tone marks, upper and lower vowels — are exactly what that would
lose.

Construction: the same cell partition as above; within each cell, keep the token
with the highest contrast instead of the geometric representative. Contrast is
the standard deviation of the raw patch pixels, computed from the image, not
from model attention, so it costs no extra forward pass and cannot leak decoder
information into the selection. Ties break to the lower flat index.

Coverage is preserved exactly — one survivor per cell — so this differs from
`PRUNE_GRID` only in *where within a cell* the survivor sits.

## 5. Pre-registered analysis

Three contrast families, each Holm-corrected across its own three budgets, each
with its own bootstrap interval computed on the shared cluster-bootstrap index
matrix (clusters = `source_photo_id`):

| Family | Contrast | Question |
|---|---|---|
| A (carried over) | ΔCER(`PRUNE_GRID`) − ΔCER(`RR`) | does *where* compression happens matter? |
| B (new) | ΔCER(`MERGE_GRID`) − ΔCER(`PRUNE_GRID`) | does the discarded content matter, at fixed count and fixed positions? |
| C (new) | ΔCER(`PRUNE_COVERAGE`) − ΔCER(`PRUNE_GRID`) | does placement within a cell matter? |

Families are corrected separately and are **not** pooled; with three families of
three the round-wide error rate is not controlled, and no result here may be
reported as confirmatory. `PRUNE_RANDOM` at two seeds remains the structure-free
reference: both seeds are reported, neither is selected after the fact.

Efficiency is descriptive. No exchange rate between characters and seconds is
registered, and none may be introduced afterwards — choosing one after seeing
the numbers is choosing the conclusion.

## 6. A confound this round must be able to rule out

Round 1 found `RR_25` scoring *better* than `FULL`. Before that is interpreted as
compression helping, the mundane explanation has to be excluded: these regions
are small crops (median well under 200×50 px), and the processor upsamples them
to reach its pixel floor. A lower budget upsamples less. Removing an
interpolation artefact is not evidence that compression helps, and the two are
indistinguishable without the geometry.

Every observation now records `native_source_height/width`,
`native_processed_height/width`, `native_processor_scale` and
`native_processor_upsampled`, and the report tabulates the upsampled fraction and
median scale per condition. If `FULL` is heavily upsampled and `RR_25` is not,
the round 1 inversion is explained and must be reported as such.

## 7. What this round deliberately does not do

**One model only.** `wayu-paxa-ocr-zero` is not run here. A new method and a new
model introduced together cannot be told apart when something looks wrong: an
anomaly could be a merge implemented incorrectly or a genuine property of the
second model. The second model runs only once this round's mechanics are
confirmed — token counts correct, M-RoPE positions consistent, output boundary
intact, path equivalence identical — and it then runs under exactly this
contract.

**Methods deferred, with the reason:**

| Method | Why not now |
|---|---|
| Pre-encoder token dropping (patches removed before the ViT, at fixed resolution) | needs the vision tower's attention mask and rotary positions rebuilt for a non-rectangular grid; a compatibility probe comes before any arm |
| VisionZip | compatibility with this backbone unverified; must be probed before the name is used |
| ET-Prune | conceptual challenger for text-rich inputs; worth doing, after the mechanics above are settled |
| SparseVLM, FastV, S²Prune | require decoder attention scores, a different instrument from anything built here |
| RTPrune | designed against DeepSeek-OCR; not this architecture |

None of these may appear in a write-up as "tested" or "compared" on the strength
of this round.

## 8. Claim level

Unchanged: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. Scope is text-region
recognition on Thai document images, one model family, no sealed confirmatory
split. This round does not approve Gate 0 or Gate 1 and does not confirm H1 or
H3.

---

## Appendix — engineering smoke, 2026-09-21

Two regions, nineteen conditions each, CPU float32, `PaddleOCR-VL-1.6` at
`c5630ab`. This verifies mechanics only. **No number below is evidence about any
hypothesis**: two regions from one photo cannot support an estimate, and the
contrast values computed from them are noise recorded to prove the code runs,
not findings.

Mechanics verified:

- `path_equivalence: IDENTICAL` — the rerouted `FULL` reproduced the legacy
  `pixel_values` route character-for-character.
- 38/38 observations completed, 0 execution failures.
- `llm_visual_positions == expected_placeholders` for every observation.
- `post_encoder_vision_cost_invariant: true` — one distinct `vision_patches`
  value per region across all post-encoder conditions.
- `MERGE_GRID`, `PRUNE_COVERAGE` and `PRUNE_GRID` produced different outputs at
  the same budget, so the policies are not silently collapsing onto each other.

One defect found and fixed: the contrast score for `PRUNE_COVERAGE` reshaped
`pixel_values` as a flat `(patches, values)` matrix, but this checkpoint returns
`(patches, channels, height, width)`. All six coverage observations failed
closed rather than scoring the wrong patches, which is the intended behaviour of
the assertion.

Two observations that bear on interpretation, both from the new instrument and
both to be re-examined at full scale:

1. **Resolution Reduction reduces encoder work; post-encoder pruning does not.**
   At the 25% budget, `RR` processed 156 vision patches against 600 for every
   post-encoder condition, and its measured `vision` stage fell accordingly while
   theirs did not. End-to-end, `RR` was the cheaper intervention. A single total
   latency would not have shown this.

2. **The processor upsamples these crops heavily, and most at `FULL`.** Median
   area scale was 15.7x at `FULL`, falling to 3.9x at `RR_25`; every observation
   was upsampled. This is the alternative explanation for round 1's `RR_25`
   beating `FULL`, and it is now measurable rather than speculative.
