# Stage 0 Measurement Validity Execution Plan

**Status:** PILOT PROTOCOL REVISED; `QUICK_HUMAN_PROTOCOL_CHECK`;
Gate 0 remains `NOT_RUN`

## Objective

Establish whether the pinned full-information Qwen2.5-VL-3B measurement system
can discriminate controlled Thai orthographic stimuli. Stage 0 does not vary
resolution, visual-token budget, or any compression mechanism.

The Qwen2.5 repaired calibration and a separately pre-registered Qwen3.5-4B
backbone audit are now complete on the open calibration split. Qwen2.5 was not
adequate across all components; Qwen3.5-4B collapsed to an A-position-biased,
chance-level measurement. The current recommendation is
`MEASUREMENT_REDESIGN_REQUIRED`. The frozen D1-D4 diagnostic in
`docs/stage0/QWEN35_MEASUREMENT_DIAGNOSTIC_PROTOCOL.md` is now complete. Its
pre-registered classification is `inconclusive`, producing recommendation C:
screen an architecturally distinct backbone. Execution is stopped for human
review; no screening run is authorized.

The human researcher subsequently approved an A/B/C measurement-contract
pilot in principle with required revisions. The revised protocol and exact
config are now recorded, but only documentation and non-model validation are
authorized until the required quick human protocol check is complete.

## Authorization and stop boundary

Authorized now:

- candidate-pair inventory and non-model validation;
- deterministic HarfBuzz + FreeType rendering;
- Unicode, shaping, difference-mask, prompt, parser, record, and metric code;
- analysis and documentation of the completed D1-D4 run using only already
  exposed calibration pairs.
- protocol/config revision and non-model validation for the proposed 25-pair
  A/B/C measurement-contract pilot.

Forbidden now:

- locked Stage 0 validation before criteria are human-frozen;
- Gate 0 approval;
- Stage 1A or any compression intervention.
- post-outcome prompt, label, rendering, pair, or backbone changes presented as
  the same registered calibration;
- any further model inference, including backbone screening.

## Dependencies and checkpoints

```text
Candidate inventory
  → Unicode/font/shaping/difference-mask checks
  → human linguistic + rendering review (Checkpoint A)
  → freeze calibration allocation, render design, prompt/parser, metrics
  → full-information calibration + exact rerun
  → estimate precision, ceiling/headroom, order bias, parser behavior,
    negative-control separation, and compute
  → propose Gate 0 criteria and locked workload
  → human freezes criteria/design (Checkpoint B)
  → STOP: locked validation is a separate run after that freeze
```

## Candidate inventory contract

- Inventory size is a pool, not a final sample size.
- `pair_id` is the independent allocation and analysis unit.
- Both members of an accepted pair are rendered; render variants remain
  repeated observations.
- Candidate labels follow `EXPERIMENT_PROTOCOL.md`: `BASE_CHARACTER`,
  `TONE_MARK`, `UPPER_VOWEL_VARIANT`, `LOWER_VOWEL_VARIANT`, and
  `STACKED_TONE_MARK`.
- `BASE_CHARACTER` is valid for Stage 0 but is not presumed to provide
  size-matched controls for Stage 2.
- Every member records `lexical_status` as `REAL`, `CONSTRUCTED`, or
  `UNCERTAIN`; constructed strings remain admissible.
- Automated validity does not substitute for human Thai-linguistic review.
- Pair inclusion/exclusion is frozen before any model outcome is opened.

## Proposed rendering-factor pool

The renderer validates the full candidate factor pool without implying that
all combinations will enter calibration:

- fonts: pinned open-license `NotoSansThai-Regular` and
  `NotoSerifThai-Regular`;
- font sizes: 72 and 96 pixels;
- canvas: 448 × 448 pixels;
- positions: center and ±14-pixel diagonal offsets;
- foreground/background: black on white;
- shaping: pinned `uharfbuzz` + `freetype-py` with Thai script/language.

The calibration workload should use a balanced incomplete subset of these
conditions after human review. The exact number of accepted pairs and rendered
observations is intentionally unresolved.

## Proposed calibration allocation

- Allocate entire `pair_id` clusters, never individual renderings.
- Keep locked-validation `pair_id`s unseen by calibration.
- Balance component categories as far as the usable inventory permits.
- Render both pair members under each selected condition so expected A/B
  labels are balanced by construction.
- Repeat the same frozen workload with the same seed to assess exact
  reproducibility.
- Include separately labeled `LANGUAGE_CANDIDATE_BIAS_BLANK` controls. They
  have no visual ground truth and never enter full-information accuracy.

The calibration/validation pair counts and condition subset require human
approval after the usable inventory is known. No numeric split is registered
in advance of that evidence.

## Proposed prompt and parser

- Fixed Thai forced-choice prompt with candidate text inserted into A/B slots.
- Candidate order is deterministic from `seed + order_group_id` and shared by
  the two displayed members of the same pair/condition, yielding one correct A
  and one correct B label.
- Parser accepts only a single `A` or `B` after surrounding whitespace removal
  and ASCII case folding.
- Raw output is always stored before parsing.
- Parser failure is separate from an incorrect parsed decision.

Prompt wording and parser policy require Checkpoint A approval before model
calibration.

## Proposed metrics

- all-observation forced-choice accuracy;
- accuracy conditional on successful parsing;
- parser-failure rate;
- per-component and per-render-condition accuracy;
- accuracy by expected A/B label and candidate-order gap;
- pair-clustered bootstrap intervals;
- blank-control candidate/order/lexical-status preference, reported without
  visual accuracy;
- exact rerun agreement for raw output, parsed output, and token metadata;
- visual-token count, latency, peak RAM/VRAM, and execution failures.

No decision threshold is attached to these metrics yet.

## Gate 0 criteria derivation

After calibration, the proposal must connect numeric criteria to:

1. baseline ceiling and usable headroom;
2. interval precision at `pair_id` level;
3. parser/order/control behavior;
4. reproducibility; and
5. the human-selected provisional 10 percentage-point SESOI for Advisor
   Readiness measurement planning.

Criteria must not use Stage 1A results. Checkpoint B freezes the criteria,
locked pair allocation, rendering conditions, prompt/parser, and exact Kaggle
workload before the first locked validation run.

## Current unresolved scientific decisions

- which candidate pairs are linguistically acceptable;
- whether constructed low-semantic-predictability graphemes are admissible;
- which rendering-factor subset enters calibration;
- calibration versus locked-validation `pair_id` allocation;
- numeric Gate 0 criteria;
- final pair/allocation/render-subset freeze after inventory expansion.
