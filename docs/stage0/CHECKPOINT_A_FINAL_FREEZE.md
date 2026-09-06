# Stage 0 Checkpoint A — Frozen Calibration Design

**Status:** `FROZEN_CALIBRATION`
**Model exposure at freeze:** none; the authorized calibration was subsequently run
**Stage 0 scientific status:** `NOT TESTED`

> Human decision on 2026-09-06: `APPROVED FOR STAGE 0 CALIBRATION ONLY`.
> Locked validation, Gate 0 approval, Stage 1A, and all compression
> interventions remain unauthorized.

This packet incorporates the conditional visual approval and all requested
pre-calibration revisions. The human freeze authorizes only the frozen
full-information calibration workload. It does not authorize locked
validation, Gate 0 approval, Stage 1A, or compression.

## Immutable review artifact

- Git commit: `e1ad6f354c867a2aba1ea67270556b761e07115e`
- Review directory:
  `runs/stage0/candidate_review/20260905T204206Z_e1ad6f35/`
- Review packet SHA-256:
  `e340a2b8386751352beb36732d21a6c613fd3bbdd1822262880e4a0a4b671df3`
- Candidate inventory SHA-256:
  `cf69f0d23bec61fbeaca7fd5ed34d48219aaad9624e509cc2208a0c98a8021b2`
- Rendering config SHA-256:
  `f36a3b8d50a32e35e9e50a0a66cab399098ae94ca44b371ae940a3e7149e4bbd`
- Proposed calibration config SHA-256:
  `8da33bdbb55e51ef6b6c9a0a27a0d210ee216e271b0592b15239988a3d5f7c32`

The earlier 30-pair packet remains immutable. This revision expands and
revalidates it; it does not overwrite the earlier artifact.

## Revised candidate inventory

The inventory contains 200 unique `pair_id`s and 40 pairs per registered
component:

| Component | Actual manipulation | Candidate pairs |
|---|---|---:|
| `BASE_CHARACTER` | base character changes | 40 |
| `TONE_MARK` | tone mark is added without an upper vowel | 40 |
| `UPPER_VOWEL_VARIANT` | U+0E34 versus U+0E35 | 40 |
| `LOWER_VOWEL_VARIANT` | U+0E38 versus U+0E39 | 40 |
| `STACKED_TONE_MARK` | upper vowel remains; only tone mark changes | 40 |

The full inventory, strings, code points, normalization, rationales, and
member-level lexical status are in `configs/stage0/candidate_pairs.yaml` and
the packet's `resolved_pairs.json`.

`BASE_CHARACTER` pairs are admissible for Stage 0 measurement validity. They
are explicitly `NOT_ASSESSED_NOT_ASSUMED` as size-matched Stage 2 controls.
The two proposed base-character splits use separate perfect matchings: within
each split every one of the 40 base-member strings occurs once, preventing
member reuse from inflating the nominal 20-pair count.

## Lexical-status metadata

Every pair member is one of `REAL`, `CONSTRUCTED`, or `UNCERTAIN`:

- `REAL`: 33 members provisionally human-confirmed as ordinary lexical items;
- `CONSTRUCTED`: 0 members positively classified in the current packet;
- `UNCERTAIN`: 367 members, including systematically expanded candidates for
  which no pinned lexicon or human lexical decision has been supplied.

`UNCERTAIN` is intentional and avoids silently calling a string a nonword.
Constructed strings remain admissible and must not be excluded solely for
being nonwords. The runner preserves displayed/candidate lexical status and
reports full-information subsets plus blank-control selected-status counts.
The final human freeze may reclassify individual members with documented
rationale without removing them merely for lexical status.

## Pair-level adequacy result

The initial six pairs per category were insufficient for the requested design:
an even disjoint split would leave three independent pairs per category and a
pair-level empirical granularity of 33.3 percentage points. Additional fonts,
sizes, positions, or renders cannot repair that independent-unit deficit.

The expanded inventory applies a pre-outcome planning floor derived from the
provisional 10 pp SESOI:

```text
target pair granularity = SESOI / 2 = 5 pp
minimum pairs per category per split = 100 / 5 = 20
minimum candidate inventory per category = 20 calibration + 20 locked = 40
```

The 40/category inventory therefore meets
`MEETS_PROVISIONAL_GRANULARITY_FLOOR_NOT_POWER_GUARANTEE`. This rule only
prevents an obviously coarse pair design. It does not establish power for a
10 pp interaction. Calibration must still estimate between-pair heterogeneity,
ceiling/headroom, and achieved pair-clustered interval precision; an
inadequate result may lead to `INCONCLUSIVE` rather than weaker criteria.

## Automated rendering and mask validation

- 12 rendering conditions;
- 2,400 pair-condition records;
- 4,800 rendered stimuli;
- 2,400/2,400 deterministic rerender checks passed;
- 1,920 target-only shaping checks passed;
- 480 `BASE_CHARACTER` records correctly marked as exempt from size matching;
- zero missing glyphs, empty masks, nonpositive critical areas, clipping,
  nonzero actual-origin deltas, or remaining contextual-layout failures;
- total automated issues: `0`.

The binary mask uses
`abs(coverage_a - coverage_b) >= 1` on FreeType 8-bit anti-aliased coverage.
`critical_pixel_area` is the count of thresholded pixels. Exact rerender bytes
and metadata must match. Both members use one union-bbox origin; independent
recentering is forbidden. For non-base categories, unchanged shaped glyph IDs
and placements must also match.

This added check detected `ฬา` versus `ฬ่า`: the fonts selected a contextual
base-glyph form, so the visible change was not tone-only. That candidate was
removed before model inference and replaced by `ฌา` versus `ฌ่า`, which passes
both pinned fonts and sizes. Exact rules are in
`docs/stage0/DIFFERENCE_MASK_SPEC.md`.

## Proposed pair allocation

The proposal is exactly 100 calibration pairs and 100 untouched locked pairs:

| Component | Calibration | Locked validation |
|---|---:|---:|
| `BASE_CHARACTER` | 20 | 20 |
| `TONE_MARK` | 20 | 20 |
| `UPPER_VOWEL_VARIANT` | 20 | 20 |
| `LOWER_VOWEL_VARIANT` | 20 | 20 |
| `STACKED_TONE_MARK` | 20 | 20 |

Base pairs use the two member-balanced matching rounds. Other categories use
the registered SHA-256 ordering with seed `20260906`; no model outcome exists
or entered the allocation. Exact IDs are frozen as a proposal in
`configs/stage0/calibration_design.yaml` and
`proposed_calibration_design.json`.

## Proposed calibration rendering subset

The 12-condition pool remains human-approved. To keep calibration lean while
crossing font and size, the proposed subset is the centered 2 × 2 factorial:

- `noto_sans_thai_regular__72__center`;
- `noto_sans_thai_regular__96__center`;
- `noto_serif_thai_regular__72__center`;
- `noto_serif_thai_regular__96__center`.

Position offsets remain validated candidate conditions but are not in this
calibration proposal. This avoids counting near-identical jittered renders as
new evidence and reduces compute before measurement validity is known.

## Blank language/candidate-bias controls

All 100 calibration pairs receive a blank-image control in both candidate
orientations, giving 200 control calls per run. The control type is
`LANGUAGE_CANDIDATE_BIAS_BLANK`, `expected_label` is null, and visual accuracy
is undefined. Reported outputs are parser behavior, A/B preference, canonical
member preference, and selected lexical-status counts. They never enter OCR or
full-information accuracy.

## Exact Kaggle calibration workload

| Work item | Calls per run |
|---|---:|
| Full-information: 100 pairs × 4 conditions × 2 members | 800 |
| Blank candidate-bias: 100 pairs × 2 orientations | 200 |
| Total per run | 1,000 |
| Exact rerun count | 2 |
| **Total model calls** | **2,000** |

Backend: approved Kaggle `NvidiaTeslaT4`. Model:
`Qwen/Qwen2.5-VL-3B-Instruct` pinned to revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`. Compression family is
`FULL_INFORMATION`. Locked validation calls are not included.

## Prompt, parser, and metrics

The previously reviewed Thai forced-choice prompt and exact A/B parser are
unchanged and human-approved. Registered metrics remain full-information
all-scored and conditional-parsed accuracy, parser failure, component,
condition, expected-label/order gap, `pair_id`-clustered intervals,
lexical-status subsets, exact-rerun agreement, visual-token counts, latency,
RAM/VRAM, and execution failures. Blank controls use only the bias metrics
described above.

No numeric Gate 0 pass criteria are frozen. The provisional 10 pp SESOI is a
measurement-planning input only, not a publication/absence threshold. Numeric
criteria will be proposed from calibration precision, ceiling/headroom,
parser/order/control behavior, and reproducibility, then require a separate
Checkpoint B human freeze before locked validation.

## Final decisions requested

Final Checkpoint A freeze requires explicit human approval or revision of:

1. the expanded 200-pair inventory and provisional member-level lexical
   statuses, including the `ฬา/ฬ่า` replacement;
2. the pair-granularity planning floor and 20/20 allocation per category,
   acknowledging that it is not a power guarantee;
3. the exact calibration/locked pair ID allocation;
4. the four centered calibration conditions;
5. all 100 calibration pairs as two-orientation blank bias controls;
6. the exact 2,000-call Kaggle workload; and
7. authorization to change config status to `FROZEN_CALIBRATION` and run only
   the calibration after recording the human decision.

Until that decision is recorded, the runner remains fail-closed and no Qwen
calibration may start.
