# Region-OCR round 3 — results

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** One model, no sealed
confirmatory split, five families corrected separately. Approves no gate,
confirms no hypothesis.

| | |
|---|---|
| run id | `kaggle-region-ocr-db8b5b1bf59b` |
| observations | 11,200 (400 regions × 28 conditions), **0 execution failures** |
| wall time | 64.6 min, Tesla T4 |
| `path_equivalence` | `IDENTICAL` |
| registration | `docs/stage0/REGION_OCR_ROUND3_REGISTRATION.md` |

Family A reproduced round 2 to four decimal places (+0.0567 / +0.1170 / +0.2268,
same Holm p-values). Greedy decoding, the same seeds and the same selection rule
give the same numbers, which is the reproducibility check this pipeline was
built to make cheap.

---

## 1. The magnification curve

Full detail throughout; only the budget the processor is forced to varies.

| condition | area scale | visual tokens | macro CER |
|---|---|---|---|
| `SWEEP_200` | 19.42× | 320 | 0.3351 |
| `SWEEP_150` | 14.34× | 240 | 0.2908 |
| `FULL` | 9.67× | 160 | 0.2714 |
| `RR_75` | 7.20× | 120 | 0.2520 |
| `RR_50` | 4.87× | 80 | 0.2230 |
| `RR_25` | **2.44×** | 40 | **0.1962** |
| `SWEEP_012` | 1.31× | 20 | 0.2762 |

**A U-curve with its minimum near 2.4× area upsample, and `FULL` sitting well
past it on the wrong side.** Above `FULL`, accuracy keeps degrading exactly as
the registration predicted for the magnification explanation; nothing in a
"compression helps" story predicts that. Below the optimum it turns back up, as
it must once there are too few tokens to carry the text.

Truncation is not driving any of this: 0, 1, 7 and 1 truncations out of 400 at
`SWEEP_200`, `SWEEP_150`, `SWEEP_012` and `FULL`.

This explains round 1's inversion without appeal to compression: `RR_25` beat
`FULL` because it is closer to the model's preferred scale.

## 2. Family E — pixel detail is irrelevant

ΔCER(`RR_RESTORED_b`) against `FULL`, at FULL's token count and magnification:

| budget | estimate | 95% CI | p (Holm) |
|---|---|---|---|
| 75% | −0.0012 | [−0.0046, +0.0026] | 1.0000 |
| 50% | +0.0012 | [−0.0053, +0.0097] | 1.0000 |
| 25% | −0.0035 | [−0.0140, +0.0058] | 1.0000 |

Zero, with intervals an order of magnitude tighter than any effect in this
study. Throwing away three quarters of the rendering detail and restoring the
image costs nothing measurable — because these crops sit below the processor's
pixel floor, so the discarded detail was interpolation, not source information.

**This is the finding that makes the rest interpretable.** It removes detail as
a candidate explanation for family A entirely.

## 3. Family D — the pruning penalty survives detail matching

ΔCER(`PRUNE_GRID_RESTORED_b`) − ΔCER(`RR_b`), both arms carrying budget *b*'s
detail and ending at budget *b*'s token count:

| budget | D estimate | (family A for comparison) | p (Holm) |
|---|---|---|---|
| 75% | +0.0602 [+0.0186, +0.0990] | +0.0567 | 0.0034 |
| 50% | +0.1137 [+0.0708, +0.1706] | +0.1170 | 0.0002 |
| 25% | +0.1957 [+0.1494, +0.2429] | +0.2268 | 0.0000 |

Matching the detail moved family A by at most 0.03. The penalty is not about
information.

### Where the registration over-claimed

The registration's prediction table said the magnification explanation predicts
D ≈ 0. **That row was wrong, and it was wrong by construction.** D's two arms
must differ in the magnification the *encoder* runs at — `RR_b` feeds the
encoder budget *b*'s grid, `PRUNE_GRID_RESTORED_b` feeds it FULL's and cuts
afterwards — because that difference *is* the insertion point. D cannot separate
"encoder magnification" from "insertion point"; for post-encoder pruning they
are the same thing. Row E is what carried the design, and it carried it
decisively.

## 4. A cleaner decomposition (descriptive, not registered)

`PRUNE_GRID_RESTORED_b` and `RR_RESTORED_b` receive **byte-identical images**
and run the identical encoder; one then drops tokens and the other does not.
No registered family tests this contrast, so the numbers below are descriptive
and carry no p-value.

| | macro CER |
|---|---|
| `RR_RESTORED_25` (160 tokens, no pruning) | 0.2679 |
| `PRUNE_GRID_RESTORED_25` (40 tokens, pruned) | 0.3920 |
| **cost of post-encoder pruning alone** | **+0.124** |
| `RR_25` (40 tokens, rendered small) | 0.1962 |
| **benefit of pre-encoder reduction alone** | **−0.075** vs `FULL` |

Reaching 40 visual tokens by rendering smaller *improves* accuracy by 0.075;
reaching the same 40 tokens by discarding tokens after the encoder *costs*
0.124. The two mechanisms point in opposite directions, and that gap is what
families A and D measure.

## 5. Families B and C — replicated nulls

| budget | B: merge − prune | C: coverage − prune |
|---|---|---|
| 75% | −0.0027 (p=0.83) | +0.0104 (p=1.00) |
| 50% | −0.0329 (p=0.056) | −0.0050 (p=1.00) |
| 25% | −0.0514 (p=0.22) | −0.0081 (p=1.00) |

Unchanged from round 2. Averaging the discarded tokens back into the survivors
does not help; moving each survivor onto its highest-contrast neighbour does not
help.

## 6. What the four results say together

1. The information in the pixels does not matter (E).
2. Which tokens survive, and whether the discarded ones are averaged in, does
   not matter (B, C).
3. The grid the encoder was run on does matter, and the model has a scale
   optimum it can be pushed past in both directions (§1).
4. Cutting tokens after the encoder is expensive; reaching the same count before
   it is not (§4).

A reading consistent with all four — and it is an interpretation, not a
measurement — is that the vision tower distributes a region's evidence across
whatever grid it was given, so a subsample of that grid is lossy however it is
chosen, while a smaller grid produces tokens that are individually complete.
Nothing here tests that mechanism directly.

## 7. Efficiency, unchanged

Vision time tracks patch count for the pre-encoder arms (0.115 s at 320 tokens
down to 0.025 s at 40) and is flat at 0.047 s for every post-encoder arm,
`post_encoder_vision_cost_invariant: true`. Prefill remains ~21 ms against
~230 ms of decode, so post-encoder pruning still buys nothing measurable at this
sequence length while costing up to +0.15 CER.

## 8. The limitation this round cannot fix

Every TEMS region sits below the processor's pixel floor — **4,984 of 5,000
crops, and 2,648 of 2,661 Thai-bearing crops**. Resolution reduction on this
corpus never discards source information; it only changes magnification. Family
E proves that is not a nuisance to be caveated but the actual regime.

Selecting differently does not help. Counting Thai regions where a budget would
genuinely discard source pixels: 26 at 75%, 61 at 50%, 415 at 25% — and
requiring a real compression regime (source area ≥ 2× the rendered grid) leaves
**61 regions across 52 photos in the entire dataset**, too few for the cluster
bootstrap this design uses.

**TEMS cannot test H3 in the compression regime at any budget, and no
re-selection fixes it.** What it can test, and has, is how this model responds
to magnification and to post-encoder token removal on small text regions.

## 9. Next

Two directions, both live:

1. **Report what this corpus genuinely supports.** The scale-optimum curve and
   the pruning-versus-rendering asymmetry are practical findings for anyone
   running a region recogniser: 40 visual tokens at 2.4× beat 160 at 9.67×,
   both in accuracy and in encoder cost.
2. **Obtain a corpus in the compression regime** to test H3 proper.
   `mekpro/ocr_th` is under feasibility probe: Apache-2.0, 4,000 synthetic
   document images, median area 363k px against the 112,896 px floor, with
   resolution reduction discarding source pixels in 100% of images at every
   budget. The blocking question is whether this checkpoint — a region
   recogniser whose card states it has never seen a whole page — can read them
   at all. The `table` subset is excluded outright: its ground truth serialises
   cells with a pipe character that appears nowhere in the image.
