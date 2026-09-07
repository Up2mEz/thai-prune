# Stage 0 Dataset Publication-Readiness Audit

**Audit basis:** frozen pre-outcome inventory and rendering artifacts plus open
calibration precision; no locked outcome was opened and no pair was changed
after Qwen3.5 results

## Observed strengths

- 200 unique `pair_id`, balanced 40/component; frozen 20 calibration + 20
  locked/component;
- `pair_id` is the independent unit; fonts, sizes and displayed members are
  repeated observations;
- 12 validated rendering conditions, 2,400 pair-condition records and 4,800
  stimuli; 2,400/2,400 deterministic rerender checks passed;
- zero automated missing-glyph, empty-mask, clipping, actual-origin,
  contextual-layout or remaining shaping issues;
- difference masks use pinned FreeType coverage and critical region metadata;
- frozen four-condition critical-pixel areas show intended scale variation:

| Component | Records | Min | Median | Max critical pixels |
|---|---:|---:|---:|---:|
| `BASE_CHARACTER` | 160 | 95 | 1,755 | 4,169 |
| `TONE_MARK` | 160 | 98 | 134 | 200 |
| `UPPER_VOWEL_VARIANT` | 160 | 45 | 116.5 | 187 |
| `LOWER_VOWEL_VARIANT` | 160 | 201 | 306 | 463 |
| `STACKED_TONE_MARK` | 160 | 84 | 115 | 148 |

## Publication gaps

- lexical status: 33/400 members are provisionally `REAL`, 367 are
  `UNCERTAIN`, 0 are positively classified `CONSTRUCTED`; semantic
  predictability is therefore not controlled strongly enough for a
  Thai-specific publication claim;
- 281 unique strings among 400 member slots, with 80 duplicated-string groups
  and maximum reuse 3; `pair_id` remains unique but shared strings/bases can
  create dependency not captured by a single flat pair random effect;
- `BASE_CHARACTER` passes Stage 0 validity but is explicitly
  `NOT_ASSESSED_NOT_ASSUMED` as a size-matched Stage 2 control;
- automated checks reduce trivial pixel/render defects but do not prove absence
  of semantic cues or replace blinded Thai-linguistic review;
- 20 pairs/component/split meets a granularity floor, not a power guarantee for
  compression-by-component or hierarchical interactions

## Size recommendation

The current 200-pair inventory is adequate for calibration diagnostics but not
yet defensible as the final main-experiment dataset. In the Qwen2.5 open
calibration, component CI widths were 7.5–12.5 pp at 20 pairs/component. Using
the worst observed 12.5-pp width and the planning approximation
`n_new = n_old × (width_old / width_target)^2`, a 10-pp full-width target gives
`20 × (12.5/10)^2 = 31.25`, rounded up to **32 independent pairs/component per
split**, or **at least 320 total pair_id** across calibration and locked-like
evaluation partitions

This 320-pair number is a transparent precision floor, not a power result.
Before Stage 1, it must be checked with a hierarchical simulation that models
pair, reusable string/base, font, size and member effects after a measurement
instrument is valid. A publication version should also reduce member reuse,
freeze stronger lexical/semantic annotations and add blinded cue review. None
of these recommendations authorizes changing the current frozen calibration or
opening the locked split

## Status

`CALIBRATION_READY_NOT_PUBLICATION_READY`
