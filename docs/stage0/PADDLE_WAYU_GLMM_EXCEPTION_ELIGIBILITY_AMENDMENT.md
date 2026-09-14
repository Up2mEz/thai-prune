# Paddle/Wayu Numerical GLMM Fit-Exception Eligibility Amendment

> Human authorization:
> `NUMERICAL_GLMM_FIT_EXCEPTION_FALLBACK_AMENDMENT_APPROVED`
>
> Classification: `POST_DATA_ACCESS_STATISTICAL_PROTOCOL_AMENDMENT`
>
> Timing: after Attempt 5 verification, scientific unsealing, FULL validity
> PASS, and the first registered GLMM fit exception; before any reduced-budget
> global interaction, DID, CER, or component result was computed or inspected.

## Eligibility amendment

The unchanged preregistered fallback is now eligible in exactly two cases:

1. a registered GLMM fit returns and fails the frozen diagnostics; or
2. the registered `lme4::glmer` numerical fitting/optimization path raises an
   eligible numerical model-fit exception after environment, input, formula,
   model-matrix, configuration, and provenance validation pass but before fit
   diagnostics can be materialized.

Eligibility is defined by execution location and failure class, not by the
observed exception text, model, budget, effect direction, magnitude,
significance, or any scientific outcome. The implementation uses a fail-closed
allowlist of registered numerical fit-call locations. An exception outside that
allowlist remains fatal.

Noneligible failures include package/environment/version failures, malformed or
missing inputs, invalid factor coding, formula/configuration mismatch,
non-finite model matrices, file I/O, provenance/checksum failure, container or
out-of-memory failure, source-code error, entrypoint failure, and any ambiguous
or unexpected exception outside the registered fitting path.

## Structured fit states

The amended pipeline keeps these states distinct:

- `FIT_SUCCESS_DIAGNOSTICS_PASS`
- `FIT_SUCCESS_DIAGNOSTICS_FAIL`
- `FIT_EXCEPTION_NUMERICAL_FALLBACK_ELIGIBLE`
- `FIT_EXCEPTION_NONELIGIBLE`
- `TECHNICAL_ANALYSIS_FAILURE`

An eligible exception records the actual R condition class and message,
`FULL_MODEL_FIT` or `NULL_MODEL_FIT`, and
`diagnostics_available=false`. It does not create or set
`diagnostics_pass=false`.

## Unchanged statistical method

This amendment changes only the fallback-eligibility trigger. It does not
change:

- full or null GLMM formula;
- random-effects structure, optimizer, link, iterations, or diagnostics;
- pair-level marginal-DID fallback implementation;
- `pair_id` resampling unit, seed `20260913`, or 10,000 replicates;
- bootstrap covariance or 3-df DID-vector Wald global test;
- `DID_196`, `DID_121`, or `DID_64`;
- percentile CIs, raw p-values, or Holm procedure;
- absolute SESOI of 10 percentage points;
- four-case interaction classifier;
- CER or descriptive component definitions.

Required diff labels:

```text
STATISTICAL_METHOD_DIFF = ONLY_FALLBACK_ELIGIBILITY_TRIGGER_CHANGED
FALLBACK_IMPLEMENTATION_DIFF = EMPTY
GLMM_FORMULA_DIFF = EMPTY
FALLBACK_ESTIMAND_DIFF = EMPTY
DECISION_CLASSIFIER_DIFF = EMPTY
```

## Execution implementation

The already accepted immutable analysis image remains the R/package runtime.
The amendment commit's `run_glmm.R` and failure-contract helper are verified by
SHA-256 and mounted read-only over the registered entrypoint path. No image
build, pull, package installation, optimizer search, or formula search occurs.

For successful fits, the original diagnostics and GLMM path remain active. For
eligible numerical fit exceptions, the R entrypoint writes a structured fit
state and exits successfully so the unchanged preregistered fallback can run.
All noneligible R exceptions remain nonzero technical failures.

## Transparency statement

The preregistered primary GLMM encountered a numerical fitting exception before
convergence diagnostics could be produced. The preregistered protocol already
contained a pair-clustered nonparametric fallback with a global interaction
test, DID contrasts, multiplicity correction, and the same SESOI decision
framework, but it was ambiguous whether a pre-diagnostic numerical fit
exception triggered that fallback. After the FULL validity gate had been
observed, but before any reduced-budget interaction or contrast result was
computed, the protocol was amended to classify numerical exceptions arising
inside the registered GLMM fitting path as fallback-eligible. No GLMM formula,
fallback estimator, test, threshold, or decision rule was changed. This
eligibility amendment was not preregistered and does not eliminate all risk of
post-data-access bias.

## Validation and execution gate

Only synthetic/non-scientific data may be used to validate the amendment before
commit. One Attempt-5 analysis rerun is conditionally authorized only after all
focused, synthetic, full-suite, research-consistency, clean-preflight, diff,
and Attempt-5 verification gates pass. No optimizer/formula search or manual
fallback is allowed.
