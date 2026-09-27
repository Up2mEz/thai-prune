# Region-OCR round 3 — breaking the magnification confound

**Status: `APPROVED` — human instruction recorded in `docs/DECISION_LOG.md`,
entry 2026-09-21b.** Written before the run. The predictions in §4 are stated
here so that whichever way the numbers fall, it is visible that they were not
chosen afterwards.

Round 2 delivered an ordered, significant family A and two clean nulls, and then
undermined its own headline finding with its own instrument. This round exists
to repair that, and nothing else. No second model, no new insertion point.

---

## 1. The defect, stated precisely

TEMS regions are small: a median crop is far below the processor's pixel floor
of 112,896 px (144 tokens × 784). A representative region measures 41 × 176 =
7,216 px — **fifteen times smaller than the floor**.

The consequence is not obvious and it changes what round 2 measured. Because
every budget is above the source resolution, **no condition in round 2 ever lost
source information.** `RR_25` renders that region at 84 × 364, still a 4.2×
area *upsample* of the source. `FULL` renders it at 168 × 700, a 16.3× upsample.
Both contain the complete source; they differ in how much interpolation sits
between the glyph and the patch grid.

So "Input Resolution Reduction" on this corpus is not compression at all. It is
a change of magnification. And magnification and token count are **one knob**:
tokens = pixels / 784, so nothing that changes one can hold the other fixed for
a whole image.

This is why round 2's family A cannot be read as an insertion-point result.
`RR_b` and `PRUNE_GRID_b` do deliver the same token count, but the encoder saw
different images, and round 2 cannot say which difference produced the effect.

It is also why `RR_25` (macro CER 0.1962) beat `FULL` (0.2714): the ordering
across `FULL` → `RR_75` → `RR_50` → `RR_25` is monotone in magnification
(0.2714, 0.2520, 0.2230, 0.1962) and the least magnified condition wins.

## 2. Two arms that separate what one knob joined

### 2.1 `RR_RESTORED_b` — reduced detail at FULL's token count

Render the region at budget *b*'s grid, then restore it to FULL's grid, both
steps using the processor's own resampling filter so the coarse step matches
what `RR_b` actually does.

The result enters the processor at FULL's dimensions and therefore produces
FULL's token count and FULL's magnification, while carrying only the detail
budget *b*'s grid could hold. Verified on a real region: the restored image
yields grid `[1, 12, 50]` and 150 placeholders, identical to `FULL`, with
different pixel values.

**Against `FULL` this isolates the detail reduction with token count and
magnification held fixed.** That is contrast family E.

### 2.2 `PRUNE_GRID_RESTORED_b` — the H3 contrast with detail matched

The same restored image, then pruned to budget *b*'s token count.

Against `RR_b`: both arms carry budget *b*'s pixel detail, both deliver budget
*b*'s token count. What remains is whether the reduction happened before the
encoder or after it — **which is H3, with the confound removed.** That is
contrast family D.

### 2.3 `SWEEP_200`, `SWEEP_150`, `SWEEP_012` — trace the curve past FULL

Forced budgets at 2.0×, 1.5× and 0.125× FULL's token count. The sweep
deliberately ignores the processor's own floor and ceiling, because reaching
magnifications `FULL` cannot reach is the entire point.

The direction above `FULL` is the informative one. Nothing in a
compression-helps story predicts that magnifying *more* than `FULL` should hurt;
a scale-preference story predicts exactly that.

## 3. Grid

28 conditions per region: round 2's 19, plus `RR_RESTORED` and
`PRUNE_GRID_RESTORED` at each of three budgets, plus three sweep points.
400 regions → 11,200 observations.

Round 2's conditions are re-run unchanged rather than reused, so every contrast
in this round comes from one run on one set of images, and families B and C get
a replication at no analytical cost.

## 4. Predictions, registered in advance

| | if the effect is magnification | if the effect is detail | if the effect is the insertion point |
|---|---|---|---|
| **E** `RR_RESTORED` vs `FULL` | ≈ 0 | large and positive | ≈ 0 |
| **D** `PRUNE_GRID_RESTORED` vs `RR` | ≈ 0 | ≈ 0 | positive, like family A |
| **sweep** above `FULL` | CER keeps rising | flat | flat |

The three columns make genuinely different predictions on all three rows, so
this round can distinguish them rather than merely add numbers.

The outcome that would most change the project's direction is **E ≈ 0 and
D ≈ 0**: it would mean round 2's family A measured magnification preference, H3
has no support on this corpus at these budgets, and the corpus itself — crops
far below the pixel floor — is the wrong instrument for the question.

## 5. Analysis

Five contrast families, each Holm-corrected across its own three budgets, on the
shared cluster bootstrap (clusters = `source_photo_id`), not pooled:

| family | contrast |
|---|---|
| A | ΔCER(`PRUNE_GRID`) − ΔCER(`RR`) — carried over, now interpretable only alongside D |
| B | ΔCER(`MERGE_GRID`) − ΔCER(`PRUNE_GRID`) |
| C | ΔCER(`PRUNE_COVERAGE`) − ΔCER(`PRUNE_GRID`) |
| D | ΔCER(`PRUNE_GRID_RESTORED`) − ΔCER(`RR`) |
| E | ΔCER(`RR_RESTORED`) against `FULL` |

The sweep is descriptive: an ordering, reported with intervals, not a test.

Five families of three leaves the round-wide error rate uncontrolled. Nothing
here is confirmatory, and the prohibition list now also forbids reading family A
as an insertion-point result without family D beside it.

## 6. Unchanged from round 2

Model `PaddleOCR-VL-1.6` @ `c5630ab` alone; `wayu` still waits, because adding a
model to a contrast that is still confounded produces numbers nobody can
interpret. Path equivalence still asserted before the first observation.
Stage-resolved cost still recorded. Claim level still
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

## 7. What this round still will not answer

Whether the result generalises beyond crops that sit below the processor's pixel
floor. Every region here does. A corpus of larger regions, where reducing
resolution genuinely discards source information, would test a different and
arguably more interesting regime — and if §4's "E ≈ 0 and D ≈ 0" outcome lands,
that corpus becomes the next thing to obtain rather than the next method to
implement.
