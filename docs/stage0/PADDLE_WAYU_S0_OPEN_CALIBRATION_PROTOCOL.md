# Paddle/Wayu S0 Open-Calibration Baseline Protocol

> Frozen before inference. Status:
> `APPROVED_FOR_S0_OPEN_CALIBRATION_BASELINE_ONLY`.

## Question and boundary

S0 asks whether the base OCR VLM and its Thai-specialized OCR descendant provide
a usable full-information transcription baseline on the open-calibration set.
It does not test compression, `MODEL x BUDGET`, causal mechanism, or a new
method. No locked-validation example may be read or inferred.

## Models and workload

- BASE: `PaddlePaddle/PaddleOCR-VL-1.6@c5630abae1d940eafe0697512a0325494b02ab42`
- SPECIALIZED: `wayu-ai/wayu-paxa-ocr-zero@af0204b4f334a6d5068b6bac2b3738932d6e289b`
- Prompt: exactly `OCR:`; greedy decoding; `max_new_tokens=32`.
- Inputs: identical registered 448x448 PNG bytes for both models.
- Selection: the 100 frozen open-calibration pairs minus the five engineering
  smoke pairs. No replacement is drawn from locked validation.
- Conditions: 2 members x 2 registered fonts x 2 registered sizes.
- Total: 95 `pair_id` x 8 conditions x 2 models = 1,520 calls; 19 independent
  `pair_id` clusters per orthographic component.

## Frozen parser

`parsed_output = raw_output.strip()` is the sole primary parsing operation.
It removes leading and trailing Unicode whitespace only. Internal whitespace,
line endings, punctuation, and all codepoints are preserved. The primary parser
does not apply Unicode normalization, autocorrection, fuzzy matching, or
punctuation deletion. NFC exact match is a pre-registered secondary descriptive
metric and never replaces the primary value.

Error categories are mutually exclusive in this order: exact target, opposite
member substitution, deletion/empty, output-contract failure, other Thai
substitution, non-Thai output. Output-contract failure means internal whitespace
remains after the primary parse. Thai-output rate means at least one codepoint is
in U+0E00--U+0E7F. Output length and edit distance count Unicode codepoints.

## Primary analysis

For each model and `pair_id`, average exact-target indicators over its eight
member/font/size observations. The overall estimate is the mean of the 95 pair
means. Report a pair-clustered 95% percentile bootstrap CI using 10,000
resamples and seed `20260912`. Define `delta_model = SPECIALIZED - BASE` and
bootstrap paired `pair_id` differences. Component estimates use the same method
within each set of 19 clusters and remain calibration-only.

Secondary analyses are codepoint edit distance/CER, the frozen error taxonomy,
Thai-output rate, output length, NFC exact match, font/size descriptives, and
pair-level variability. No fixed recognition-accuracy pass threshold is used.
After observing S0, numerical validity criteria may be proposed using the
calibration uncertainty and the planning SESOI of 10 percentage points; those
criteria must be frozen before any locked outcome is opened.

## Fail-closed checks and stop

The run fails technically on a revision/hash mismatch, locked exposure,
workload mismatch, cross-model PNG mismatch, prompt drift, non-isolatable output
tokens, Unicode corruption, non-finite/runtime corruption, or unexplained visual
token accounting. The expected full-information count is 1,024 pre-merge
positions and 256 projector/LLM image positions for every call.

After artifacts and analysis are preserved, recommend exactly one authorized
S0 disposition and stop at `HUMAN_REVIEW_AFTER_S0_OPEN_CALIBRATION`.
