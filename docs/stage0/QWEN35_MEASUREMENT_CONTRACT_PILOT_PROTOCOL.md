# Qwen3.5 Measurement-Contract Pilot Protocol — Pre-Inference Amendment

**Status:** `FROZEN_AUTHORIZED_FOR_PILOT_INFERENCE`

**Final human approval:** 2026-09-12. The approved execution is limited to
this frozen 25-pair Qwen3.5 pilot and must stop for human review after the
registered analysis. All interpretation boundaries in this document remain
unchanged.

**Outcome visibility:** `NO_PILOT_MODEL_OUTPUT_OBSERVED`

**Scope:** 25 deterministically selected, already exposed calibration
`pair_id` values only

**Gate 0:** `NOT_RUN`; this pilot cannot approve Gate 0 or compression

## 1. Question

This pilot asks whether Qwen3.5's weak target decision changes when the same
single-item image is transcribed instead of answered through the A/B
forced-choice interface, and whether adding a fixed surrounding visual layout
around the otherwise pixel-identical centered target changes target readout.

The three conditions are:

- A — existing forced-choice, using both registered and swapped candidate
  orders;
- B — isolated transcription of the exact single-item image used by A; and
- C — local-target readout under a fixed surrounding visual layout.

Conditions B and C return the same output type: one center target string.
Condition C is not full-line transcription, natural-language context, or
realistic document transcription. It changes controlled surrounding visual
content/layout around a matched target; the contrast does not identify a
single causal mechanism beyond that manipulated input difference.

## 1.1 Historical pre-inference amendment

Commit `13c64500442bc3790362f82964ad39666fc8b382` preserved the prior
pre-registration in Git history. Its Condition C required full-line output and
pipe-based target extraction. No pilot model output was observed under that
version. This amendment replaces only the pre-inference Condition B/C prompt,
Condition C readout/extraction, target-pixel construction, related secondary
metrics, and the name of the B-to-C contrast. Selection, Condition A,
`pair_id` analysis, SESOI, uncertainty, and prohibitions are unchanged.

## 2. Scientific boundary

- Use only the 25 `pair_id` values frozen in
  `configs/stage0/qwen35_measurement_contract_pilot.yaml`.
- All 25 must be members of the already exposed 100-pair calibration split.
- `pair_id` is the independent statistical unit. Member, font, size,
  candidate order, and condition are repeated observations.
- Do not read, render, package, inspect, or infer any locked-validation item.
- Do not change the frozen split or exclude difficult pairs.
- Do not screen another backbone.
- Do not run Resolution Reduction, Token Pruning, Token Merging, any other
  compression intervention, or the main experiment.
- Do not change prompts, anchors, geometry, decoding, normalization,
  alignment, taxonomy, metrics, or thresholds after model output is observed.
- Pilot outcomes are measurement diagnostics, never Gate 0 evidence.

## 3. Deterministic allocation

For every component, rank its already exposed calibration pairs by ascending
hexadecimal SHA-256 of the UTF-8 string

```text
measurement-contract-pilot-v1|20260912|<component_type>|<pair_id>
```

and take the first five. No model result, prior accuracy, lexical status,
glyph geometry, or researcher preference enters selection. Sort the final
stored list by component and rank. The selected-ID set hash is SHA-256 of the
newline-joined lexicographically sorted `pair_id` values with no terminal
newline:

```text
0dce30a370d40fffde1d1d9000e786835021054c828e3453ed22b828c7b6bebe
```

The fixed allocation is 25 pairs: five per each of the five registered
component categories. Both members and all four existing center conditions
(Noto Sans/Serif Thai at 72/96 px) are retained. This produces 200 target
observations per condition before A's order reduction.

With five independent clusters per component, component results are
descriptive diagnostics only. Decisions use the aggregate 25-pair paired
contrasts.

## 4. Condition A — forced-choice reference

Reuse the verified D1 rows from run
`kaggle-qwen35-measurement-953dd5e386ea-79122b58`; do not generate a new A
result. For each target-observation key

```text
(pair_id, displayed_member, font_id, font_size, position_id=center)
```

map the registered and swapped outputs back to canonical member `a` or `b`.
Define one comparable target score:

```text
A_target_accuracy =
  (correct_registered_order + correct_swapped_order) / 2
```

It is therefore one value in `{0, 0.5, 1}` for each target observation. The
two candidate orders are repeated measurements and must never be rows or
clusters counted as independent samples. If either A order is missing or
invalid, the observation is an A output-contract failure and is not silently
replaced.

## 5. Condition B — isolated transcription

Use the exact PNG pixels referenced by Condition A for the selected target
observation. Do not rerender, resize, crop, sharpen, or otherwise transform
the image.

Prompt, shared exactly with Condition C, in Thai:

```text
อ่านข้อความตรงกลางภาพตามที่เห็น แล้วตอบเฉพาะข้อความนั้น ห้ามอธิบาย
```

Generate an unconstrained transcription under the decoding contract in
Section 7. B target accuracy is binary under the frozen extraction taxonomy.

## 6. Condition C — local-target readout under line context

### 6.1 Fixed content

The five visual items, from left to right, are exactly:

```text
ก | น | TARGET | ม | ล
```

The target is always assigned to cell index 3. This constant assignment is
the deterministic target-position rule; target position is not varied or
treated as an independent factor.

The bars are visual layout elements only. The model is asked to return only
`TARGET`; it is neither asked nor expected to emit anchors or literal pipes.

### 6.2 Fixed geometry

Use the existing 448 x 448 RGB white canvas, the same two font files, 72/96 px
font sizes, HarfBuzz/FreeType shaping settings, foreground color, processor,
model revision, and Kaggle T4 runtime.

Horizontal half-open cells are frozen as:

| Element | x interval |
|---|---:|
| anchor `ก` | `[0, 64)` |
| separator | `[64, 80)` |
| anchor `น` | `[80, 144)` |
| separator | `[144, 160)` |
| target | `[160, 288)` |
| separator | `[288, 304)` |
| anchor `ม` | `[304, 368)` |
| separator | `[368, 384)` |
| anchor `ล` | `[384, 448)` |

All glyph ink is vertically centered in `[144, 304)`. Separators are fixed
two-pixel black vertical bars at x=`71:73`, `151:153`, `295:297`, and
`375:377`, y=`168:280`. They are deterministic layout marks, not font glyphs.

Each anchor is shaped once per font/size and centered in its fixed cell. Do
not rerender the target. Construct C by loading the exact frozen B PNG and
compositing only the anchor and separator layer outside the target cell. No
per-member scaling, centering, cropping, sharpening, or target-pixel rewrite
is allowed.

Before inference, fail closed unless all non-white B target ink lies inside
`[160, 288) x [144, 304)` and all anchor/separator ink lies outside it. For
every selected observation, hash the raw RGB bytes of the target-cell crop in
B and C and require exact equality. Also require a/b C images to have
byte-identical pixels outside the target cell for a shared font/size/pair.
Record B/C target-layer, anchor-layer, non-target-layer, source-PNG, and full-C
pixel hashes in the validation report.

Condition C uses the exact same prompt and decoding as B.

## 7. Frozen decoding

- model, processor, and tokenizer:
  `Qwen/Qwen3.5-4B@851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`
- `do_sample=false`
- `max_new_tokens=32`
- `min_new_tokens=1`
- `enable_thinking=false`
- stop only on the model's EOS rule or `max_new_tokens`
- do not constrain transcription tokens to A/B or candidate strings
- save token IDs and raw decoded output before normalization
- no per-example retry

## 8. Frozen normalization and extraction

### 8.1 Normalization

Primary evaluation uses raw Unicode code points after only:

1. converting CRLF and bare CR to LF;
2. removing surrounding Unicode whitespace once; and
3. retaining every internal character, space, punctuation, and code point.

No Unicode normalization is applied to the primary result. NFC-normalized
metrics are reported separately as sensitivity analyses and may not replace
the primary result.

Any non-empty internal newline produces `output_contract_failure`.

### 8.2 Condition B extraction

After primary normalization, compare the whole single-line output with the
displayed truth and its opposite pair member.

### 8.3 Condition C extraction

Use exactly the same whole-single-line target extraction as Condition B. Do
not split on pipes, infer a field position, remove anchors, or heuristically
realign output. Literal pipe output is not part of the response contract.

## 9. Mutually exclusive target error taxonomy

Apply the following precedence:

1. `output_contract_failure`: non-empty internal newline, undecodable output,
   execution failure, or Condition A missing/invalid order;
2. `deletion`: the normalized B or C output is empty;
3. `correct_target`: exact raw-codepoint match with displayed member;
4. `opposite_member_substitution`: exact match with the undisplayed member;
5. `other_substitution`: every other non-empty single-line output, including
   strings that contain a member plus additional code points.

Report counts and pair-clustered rates for all five categories. Failures count
as target-accuracy failures; they are never dropped from the denominator.

## 10. Target-component scoring

Target-word accuracy is exact `correct_target`. The secondary target-component
score uses the inventory's registered component rule:

- `BASE_CHARACTER`: first Thai base consonant equals the displayed member's
  base consonant;
- `TONE_MARK`: presence/absence of U+0E48 matches the displayed member;
- `UPPER_VOWEL_VARIANT`: the exclusive presence of U+0E34 versus U+0E35
  matches the displayed member;
- `LOWER_VOWEL_VARIANT`: the exclusive presence of U+0E38 versus U+0E39
  matches the displayed member;
- `STACKED_TONE_MARK`: presence/absence of U+0E48 matches the displayed member
  while the registered upper-vowel code point is present.

If both alternative critical code points occur, the registered surrounding
component is absent, or extraction failed, component accuracy is zero. This
score is diagnostic and does not replace exact target accuracy.

## 11. Metrics and uncertainty

Primary paired contrasts are:

```text
delta_interface   = mean(B_target_accuracy - A_target_accuracy)
delta_surrounding = mean(C_target_accuracy - B_target_accuracy)
```

For each target-observation key, form the paired difference first. Average
repeated observations within `pair_id`, then bootstrap the 25 `pair_id`
clusters with replacement for 2,000 replicates using seed `20260912`.
Report percentile 95% CIs. Never bootstrap orders, members, fonts, sizes, or
images as independent units.

The project diagnostic SESOI remains 10 percentage points. An important
contract effect requires both:

- paired contrast point estimate at least +0.10; and
- pair-clustered paired 95% CI lower bound greater than 0.

There is no 50% random-choice validity threshold for B or C. Neither absolute
transcription accuracy nor a CI above 50% is sufficient for measurement
validity. A positive pilot does not establish Gate 0 adequacy.

Secondary metrics are raw-codepoint and NFC-normalized target CER,
target exact accuracy, target-component accuracy, substitution directions,
output failures, and descriptive results by component. CER uses Levenshtein
distance divided by target reference code-point length, with failures retained
as their decoded outputs when available. An
execution/decoding failure with no output is scored as deletion of the entire
reference (`CER=1.0`) rather than removed.

Full-line transcription, full-line CER, and full-line exact accuracy are not
part of this controlled pilot. They are reserved for a separately registered
external-validity diagnostic.

## 12. Frozen decision rule

Evaluate `delta_interface` and `delta_surrounding` independently with the important-
effect rule above.

1. If `delta_interface` is important, report evidence that the forced-choice
   response contract contributes materially.
2. If `delta_surrounding` is important, report evidence associated with adding
   the frozen controlled surrounding visual layout around an otherwise
   matched centered target. Do not attribute it to one isolated mechanism or
   call it natural-language contextual rescue.
3. If either contrast is important and no interpretability flag applies,
   recommend `PIVOT_MEASUREMENT_DESIGN_FOR_FURTHER_OPEN_CALIBRATION`. This is
   not Gate 0 approval.
4. If neither contrast is important and the upper bound of each paired 95% CI
   is at most +0.10, treat improvements of the registered SESOI as excluded
   within this pilot and recommend `SECONDARY_BACKBONE_SCREENING`.
5. If contrast directions/effect status differ strongly by component, or
   output failures prevent interpretation, classify
   `MIXED_TARGETED_INSTRUMENT_REVIEW`.
6. Otherwise report the two effect decisions without forcing a root cause and
   stop as `INCONCLUSIVE`.

“Strongly by component” is operationalized for flagging, not confirmatory
inference: at least two component point estimates have opposite signs and
their difference is at least 0.20, or any component has output plus alignment
failure rate at least 0.20. With five pairs per component, this flag cannot
establish component-specific scientific effects.

## 13. Reproducibility and mandatory stop

Before inference, generate paired B/C contact sheets and a machine-readable
pixel-identity report. Final visual/protocol human approval is mandatory.

Record config and input hashes, allocation hash, seed, exact model revisions,
Git commit, environment, raw outputs, token IDs, renderer metadata, actual
visual counts, latency, failures, artifact checksums, and exact source run for
Condition A. Verify `locked_pair_count=0`, compression=`NOT_RUN`, and all
fixed-cell invariants before accepting results.

After analysis, update the report, `DECISION_LOG.md`, `CLAIMS.md`, and active
execution plans, then stop at human review. Do not open Gate 0, locked
validation, backbone screening, or compression.
