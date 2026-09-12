# Paddle/Wayu Gate-0 Locked Full-Information Protocol

> Status: `PREPARED_NOT_AUTHORIZED_NOT_RUN`
>
> This document prepares the protocol only. No locked image bundle was built,
> inspected, or sent to a processor/model in this task.

## Purpose and frozen scope

Gate 0 asks only whether each pinned checkpoint has sufficient overall
full-information exact-transcription measurement capacity under the frozen
contract. It does not test `MODEL x BUDGET`, Input Resolution Reduction,
component-specific degradation, or compression robustness.

Use exactly the 100 `locked_validation_pair_ids` already frozen in
`configs/stage0/calibration_design.yaml`, with no replacement based on S0. Each
pair contributes two members, two registered fonts, and two registered sizes.
The two models receive identical PNG bytes. The planned Gate-0 workload is:

`100 pairs x 2 members x 2 fonts x 2 sizes x 2 models = 1,600 calls`.

Only budget `B256_FULL` is allowed: 448x448 processor input,
`image_grid_thw=[1,32,32]`, 1,024 pre-merge patches, 256 projector positions,
and 256 LLM image placeholders. Prompt is exactly `OCR:`; decoding is greedy;
the primary parser removes leading/trailing whitespace only.

## Frozen Gate-0 criteria

Gate-0 measurement validity requires all of the following:

1. For each model separately, the lower pair-clustered 95% CI for overall exact
   transcription accuracy is at least 20%. This is `2 x` the 10 pp SESOI from
   the absolute zero floor. There is no upper-baseline requirement.
2. Output-contract failure is at most 1% for each model. Contract failures and
   empty outputs remain in the denominator and count as incorrect.
3. Visual-token accounting, generation boundary, model/processor revision,
   input hashes, and parser operation match the frozen contract on every call.
4. No parser/runtime corruption occurs and no unregistered locked pair appears.

Thai-output rate is diagnostic only. Component headroom classifications do not
block the overall Gate. Font and size effects are estimated as paired
`pair_id`-clustered contrasts and reported; there is no arbitrary render-range
pass threshold. Severe unexplained instability is flagged for human review.

The historical name `locked_pair_count=0` meant zero unauthorized exposure.
Because an authorized Gate-0 run intentionally contains 100 registered locked
pairs, its manifest must instead report both
`registered_locked_pair_count=100` and
`unauthorized_or_out_of_workload_locked_pair_count=0`. An unqualified count
must not be used.

## Analysis and failure handling

Aggregate the eight member/font/size observations within `pair_id` before the
10,000-resample percentile bootstrap (`seed=20260913`). Report each model's
overall exact accuracy and CI. Gate 0 remains a human decision; software reports
criterion states without opening a later stage.

No post-outcome pair or observation exclusion, replacement, parser repair, or
per-example retry is allowed. A missing/corrupt input, revision mismatch,
non-isolatable generation boundary, token mismatch, or runtime corruption stops
the run. Partial results are preserved but cannot be used as a valid Gate-0
decision.

## Locked reuse governance

The same 100 registered locked pairs are intended to form the later
`MODEL x BUDGET` panel. To prevent the locked full-information outcome from
tuning that experiment, the complete grid is frozen before any locked output:

- `B256_FULL`: 256 actual LLM image positions;
- `B196`: 196 positions;
- `B121`: 121 positions;
- `B64`: 64 positions.

The complete panel is 6,400 calls. Gate 0 would execute only the 1,600 FULL
calls; if and only if a later human decision authorizes continuation after Gate
0, the remaining 4,800 reduced-resolution calls use the already frozen grid,
analysis, metrics, and exclusions. Locked baseline accuracy cannot change a
budget, prompt, parser, pair, outcome, model, contrast, or exclusion rule.

If this reuse contract is later changed or cannot be enforced, stop and create
a new human-approved split/protocol before locked inference.

Terminal state: `OVERALL_MODEL_BUDGET_DESIGN_FROZEN_PENDING_LOCKED_AUTHORIZATION`.
