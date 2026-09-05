# Stage 0 Checkpoint A — Human Review Packet

**Status:** `AWAITING_HUMAN_DECISION`  
**Scientific evidence status:** `NOT TESTED` — no model inference has been run

This packet freezes the engineering evidence available before any Thai
candidate outcome is observed. Its purpose is to let the human researcher
decide linguistic admissibility, rendering admissibility, and the calibration
design without outcome-driven pair or condition selection.

## Reproducible artifact

- Git commit: `d63c9f3db01a0b993a6e6c3f7bea39cd9b9f9873`
- Review packet:
  `runs/stage0/candidate_review/20260905T195831Z_d63c9f3d/review_packet.json`
- Review-packet SHA-256:
  `715491c6fff6e815f1b2e5374a3f983e09fbf15eeeace9e375b37f9db8b91617`
- Pair inventory SHA-256:
  `2b7fe07334e1c2c6eece003e3a18efbf69e7010ad89d50452d438aabac5ec501`
- Rendering config SHA-256:
  `cfed2ed3be154e3973675ce8bb1e30ff702ed4bef3e0640647ecd00c3039463d`
- Full metadata: `render_manifest.json` and `resolved_pairs.json` in the
  review-packet directory.
- Human decision template: `configs/stage0/human_review.template.yaml`.

The artifact was generated in a clean detached worktree because an unrelated,
untracked `README.md` exists in the main checkout. That file was not modified
or included in this work.

## Candidate-pair inventory

The 30 pairs below are a candidate pool, not a frozen sample size. Automated
checks passed for every pair and all 12 render conditions; this does not imply
linguistic approval.

| Component | Candidate pairs |
|---|---|
| `BASE_CHARACTER` | กา/ภา, ขา/ชา, คา/ดา, นา/มา, บา/ปา, ลา/สา |
| `TONE_MARK` | กา/ก่า, ขา/ข่า, คา/ค่า, ปา/ป่า, นา/น่า, มา/ม่า |
| `UPPER_VOWEL` | กิ/กี, ขิ/ขี, คิ/คี, ปิ/ปี, นิ/นี, มิ/มี |
| `LOWER_VOWEL` | กุ/กู, ขุ/ขู, คุ/คู, ปุ/ปู, นุ/นู, มุ/มู |
| `UPPER_VOWEL_TONE` | กี/กี่, ขี/ขี่, คี/คี่, ปี/ปี่, นี/นี่, มี/มี่ |

Automated validation covered Thai code-point membership, NFC normalization,
the category-specific one-component transformation, canonical mark order,
duplicate detection, missing glyphs, non-empty ink, non-empty difference
masks, shared-origin rendering, clipping, and unexpected global layout shift.
It produced 720 rendered stimuli from 30 pairs × 12 conditions × 2 pair
members, with zero automated issues.

Contact sheets use the preview condition `NotoSansThai-Regular`, 96 px,
centered. The engineering visual audit found no missing glyph, clipping, or
global-layout artifact, and the visible difference masks were localized to the
intended feature. A human Thai-linguistic decision remains required for every
pair, including whether constructed or mixed lexical-status strings are
admissible.

## Rendering conditions proposed for selection

The candidate pool is the Cartesian product of:

- fonts: pinned `NotoSansThai-Regular` and `NotoSerifThai-Regular`;
- sizes: 72 px and 96 px;
- positions: center, `(-14, -14)`, and `(+14, +14)` pixels;
- canvas: 448 × 448 px, black on white;
- renderer: HarfBuzz Thai shaping plus FreeType rasterization;
- pinned font SHA-256 values and renderer versions recorded in the packet.

All 12 conditions passed automated checks. The subset used in calibration is
not yet selected. Render variants of one `pair_id` remain repeated
observations, not independent samples.

## Calibration sample design proposed for human freeze

- Allocate whole `pair_id` clusters, never individual renders.
- Keep locked-validation `pair_id`s disjoint and unseen during calibration.
- Balance component categories as far as the human-approved inventory permits.
- Use a human-selected balanced incomplete subset of rendering conditions.
- Render both members for every selected pair-condition; this produces one
  expected `A` and one expected `B` label under a shared deterministic order.
- Run separately labeled blank-image language-prior controls.
- Repeat the exact frozen calibration workload with the same seed.
- Analyze repeated renders with `pair_id`-clustered uncertainty.

No pair count, split, or final number of observations is proposed before the
human establishes the usable inventory. `configs/stage0/calibration_design.yaml`
therefore remains `PROPOSED_NOT_FROZEN`.

## Prompt and parser specification

Proposed fixed prompt:

```text
ข้อความใดปรากฏอยู่ในภาพ
A. {candidate_a}
B. {candidate_b}
ตอบเพียง A หรือ B เท่านั้น
```

Candidate order is deterministic from `seed + order_group_id`. Both displayed
members of a pair-condition share the same orientation, so expected labels are
balanced by construction. The parser strips surrounding whitespace, applies
ASCII case folding, and accepts only exact `A` or `B`; any additional text is a
parser failure. Raw output is stored before parsing, and parser failure is not
counted as an ordinary incorrect visual choice.

## Metrics registered for calibration

- forced-choice accuracy across all observations;
- accuracy conditional on successful parsing;
- parser-failure rate;
- accuracy by component, rendering condition, and expected label;
- candidate-order gap;
- `pair_id`-clustered bootstrap interval;
- full-information versus blank-control separation;
- exact-rerun agreement for raw output, parsed output, and token metadata;
- actual visual-token count, latency, peak RAM/VRAM, and execution failures.

These metrics have no scientific pass thresholds yet.

## Gate 0 criteria proposal status

The defensible proposal at Checkpoint A is a derivation rule, not numeric
criteria. After calibration, numeric criteria must be tied to:

1. baseline ceiling and usable headroom;
2. interval precision at `pair_id` level;
3. parser, order, and blank-control behavior;
4. exact-rerun reproducibility; and
5. a human-selected smallest later-stage effect of interest.

Accordingly, the numeric Gate 0 criteria proposal is
`BLOCKED_PENDING_CALIBRATION_AND_HUMAN_EFFECT_CHOICE`. It cannot be filled now
without inventing thresholds, and it must never be selected from Stage 1A
outcomes.

## Exact Kaggle workload status

Backend feasibility is already verified for the pinned
`Qwen/Qwen2.5-VL-3B-Instruct` revision on a Kaggle T4. The Stage 0 workload is
`BLOCKED_PENDING_HUMAN_FREEZE`: exact calls depend on accepted pair IDs,
calibration/locked allocation, selected conditions, and blank-control IDs.

Once those fields are frozen, the code derives rather than guesses:

```text
full-information calls = 2 × selected calibration pair-condition assignments
blank-control calls     = 2 × selected blank pair-condition assignments
total submitted calls   = (full + blank) × exact-rerun count
```

The derived workload pins the primary model revision, requests
`NvidiaTeslaT4`, uses `FULL_INFORMATION` only, and explicitly excludes locked
validation. No Kaggle Stage 0 inference has been submitted yet.

## Human decisions required now

1. Accept or reject each candidate pair and record a reason for every
   exclusion.
2. Decide whether constructed/nonword or mixed lexical-status pairs are
   admissible for this diagnostic.
3. Approve the allowable rendering-condition pool and select the calibration
   subset without seeing model outcomes.
4. Freeze disjoint calibration and locked-validation `pair_id` allocations.
5. Select pair IDs used for separately reported blank-image controls.
6. Approve or revise the fixed prompt and strict parser.
7. Approve the registered metrics and whether Kaggle T4 will run calibration.
8. State the smallest later-stage effect of interest before the numeric Gate 0
   criteria are proposed.

Until decisions 1–7 are recorded, calibration inference is fail-closed. The
smallest effect decision may be recorded now or during calibration review, but
must precede the Gate 0 criteria freeze and locked validation.

## Scope boundary

- Stage 0 scientific status: `NOT TESTED`.
- Calibration: `BLOCKED` pending Checkpoint A approval.
- Locked Stage 0 validation: `BLOCKED` pending calibration and Checkpoint B.
- Gate 0 approval: not authorized.
- Stage 1A and every compression intervention: not authorized.
