# Stage 0 Difference-Mask Construction

## Purpose and scope

`difference_mask` identifies pixels whose glyph coverage differs between two
members rendered under the same font, size, canvas, color, and position
condition. It is audit metadata for controlled stimuli; it is not evidence of
perceptual importance and is not a Stage 2 size-matching criterion.

## Anti-aliasing and threshold

FreeType produces an 8-bit grayscale coverage mask for each glyph. Coverage 0
means no ink and 255 means full foreground coverage. RGB stimulus pixels are
created deterministically by alpha-compositing this coverage against the
registered foreground/background colors.

For masks `coverage_a` and `coverage_b`, the binary rule is:

```text
coverage_delta = abs(int16(coverage_a) - int16(coverage_b))
difference_mask = coverage_delta >= coverage_delta_threshold
```

The registered `coverage_delta_threshold` is `1`, so every reproducible
one-level-or-larger anti-aliasing difference is retained. The conversion to
`int16` prevents unsigned subtraction wraparound. The output mask uses 0 for
unchanged pixels and 255 for changed pixels.

`critical_pixel_area` is exactly the count of nonzero pixels in this binary
mask. The manifest also records `max_coverage_delta` and
`coverage_delta_sum`. These values must not be interpreted as physical area or
as a claim that `BASE_CHARACTER` controls are size-matched.

## Reproducibility rule

Every pair-condition is rendered twice in the candidate-review build. The
following must match exactly within the pinned environment:

- A-member RGB bytes;
- B-member RGB bytes;
- binary difference-mask bytes;
- all `PairRenderMetadata`, including `critical_pixel_area`.

A mismatch records `NONDETERMINISTIC_RERENDER` and fails automated validation.
The packet pins font hashes, `uharfbuzz`, `freetype-py`, and the FreeType
library version; cross-environment equality is not assumed without rerunning
the audit.

## Global-layout shift rule

The renderer shapes each member independently but computes one union bounding
box and one shared canvas origin. Both members are rasterized from that exact
origin. It never centers A and B independently.

The manifest records:

- `shared_origin_policy`;
- `actual_origin_delta`, which must be `(0, 0)`;
- `separately_centered_origin_delta`, the translation that independent
  centering would have introduced.

Any nonzero `actual_origin_delta` records `GLOBAL_LAYOUT_SHIFT` and fails the
candidate build. `separately_centered_origin_delta` is diagnostic only: a
nonzero value shows an artifact avoided by the shared-origin rule. Natural
within-string placement changes caused by different glyph advances remain
visible in the mask and are not mislabeled as canvas recentering. Their role as
a visual-size/layout confound belongs to Stage 2.

For `TONE_MARK`, `STACKED_TONE_MARK`, `UPPER_VOWEL_VARIANT`, and
`LOWER_VOWEL_VARIANT`, the builder additionally compares the shaped glyph
runs. After removing or replacing the registered target glyph, every unchanged
glyph ID and placement must match exactly. A contextual glyph substitution or
movement outside the target feature records
`UNEXPECTED_CONTEXTUAL_LAYOUT_CHANGE` and fails validation. This check caught
and removed `ฬา` versus `ฬ่า`, where the font selected a contextual base-glyph
form rather than changing only the tone mark. `BASE_CHARACTER` is exempt from
this target-only shaping rule because base glyph size/advance differences are
part of the Stage 0 distinction and are explicitly not assumed size-matched
for Stage 2.

## Change control

Changing the threshold, renderer, font file, font size, canvas, position, or
global-origin policy invalidates prior mask hashes and requires a new immutable
candidate-review packet and human review before model inference.
