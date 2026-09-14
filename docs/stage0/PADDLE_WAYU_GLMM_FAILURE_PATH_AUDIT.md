# Paddle/Wayu GLMM Failure-Path Audit

> Authorization: `GLMM_FAILURE_PATH_AUDIT_ONLY_AUTHORIZED`
>
> Scientific rerun: **not performed**
>
> Reduced-budget outcomes: **not inspected or computed during this audit**
>
> Terminal state: `GLMM_FAILURE_PATH_AUDIT_COMPLETE_PENDING_HUMAN_REVIEW`

## Scope and frozen identities

- Original scientific design commit:
  `871996221a36a56a401fa040c239f55768561210`
- U+FFFD amendment commit:
  `ee9f8c4f85feea935f8c99d05005deea16c30442`
- Attempt-5 execution commit:
  `1fa4cdda6ebe37faf215e574a6a5db467beda1cb`
- Analysis packaging amendment commit:
  `3ea83cdd56c4fc07c2598f08150840a4ffbb05f9`
- Analysis runner amendment commit:
  `e089995d29da6b985b71e719074af571b21b15a0`
- Frozen analysis image:
  `sha256:7328bb5ac82d574e2d895018981a8cf18b0ae8e73c9b90bf1ce0b350ed7091df`
- Frozen R entrypoint SHA-256:
  `e30341f261995fb15a7136132a9edc94b7b4752c604e95af7c45c2b966aaec1e`

The authoritative fallback specification and design configuration have no diff
from the original design commit. `run_glmm.R` and
`locked_panel_analysis.py` have no diff from the Attempt-5 execution commit
except the already accepted U+FFFD derivation change outside fallback logic.

## 1. Exact frozen fallback contract

The strongest and most specific frozen language is in
`PADDLE_WAYU_PRIMARY_ANALYSIS_SPEC.md`:

- lines 107–122 define diagnostics on successfully materialized full and null
  fit objects;
- lines 124–127 say a failed check yields
  `PRIMARY_GLMM_DIAGNOSTIC_FAILURE` and require preservation of the fit and
  diagnostic values;
- line 131 says: “If and only if the GLMM fails the diagnostics” the fallback
  is used;
- lines 134–143 define the pair-level DID vector, 10,000 pair-clustered
  resamples, covariance, 3-df Wald global test, DID p-values, and Holm control;
- lines 145–148 require disclosure that the fallback supplies the primary
  result.

The frozen YAML expresses the same boundary:

- `overall_model_budget_design.yaml:129-139` defines diagnostics and
  `failure_status: PRIMARY_GLMM_DIAGNOSTIC_FAILURE`;
- `overall_model_budget_design.yaml:140-148` defines the fallback global test,
  non-estimable status, Holm procedure, and forbids a silent switch.

The Decision Log is also diagnostics-specific:

- `DECISION_LOG.md:403-407` states that “Diagnostic failure” invokes the
  preregistered pair-clustered marginal-DID fallback.

No frozen source explicitly defines the state in which `glmer(...)` throws an
exception before either fit object and its diagnostics are materialized. The
sources do not explicitly include that state, but they also do not explicitly
declare a numerical fit exception ineligible.

**Eligibility classification:** `C. FROZEN_CONTRACT_AMBIGUOUS`

## 2. Exact failure and code path

The registered path is:

1. `scripts/paddle_wayu_locked_panel.py:642-666` verifies the accepted image and
   calls `write_analysis_inputs(...)`.
2. `run_glmm.R:12-27` reads the registered CSV, enforces 6,400 unique rows,
   factors variables, fixes both formulas, and fixes the `bobyqa` control.
3. `run_glmm.R:29-42` calls `glmer(...)` for the full fit and then the null fit.
4. `run_glmm.R:47-80` would derive fit diagnostics only after both calls return.
5. `run_glmm.R:93-114` would write `glmm_result.json` only after diagnostics,
   separation checking, and the LRT are available.
6. `locked_panel_analysis.py:293-300` requires `glmm_result.json`, reads
   `diagnostics_pass`, and only then selects GLMM or fallback.

The observed stack was:

```text
fit_with_warnings -> do.call -> <Anonymous> -> <Anonymous> -> fn -> pwrssUpdate
Downdated VtV is not positive definite
```

This exception came from the registered `lme4::glmer` fit path before
`fit_diagnostics(...)` ran. The upstream lme4 repository also records this
message as a numerical model-fitting/PIRLS failure. That supports classifying
the observed event as a **numerical GLMM fit exception**, not a Docker,
package-loading, file-I/O, or input-row-count failure. It does not establish the
data-specific numerical cause. Because the R script emits no fit marker before
each call, the preserved trace does not prove whether the full or null fit was
active.

The immediate implementation fact is therefore:

> The R process exits before emitting the structured state that the Python
> fallback router requires.

However, it does not follow that this is merely an engineering control-flow
defect, because the frozen eligibility contract does not say whether a
pre-diagnostic fit exception may enter the fallback.

## 3. What the registered fallback provides

| REGISTERED_QUANTITY | GLMM_PATH | FALLBACK_PATH | AVAILABLE? | PRE-REGISTERED? |
|---|---|---|---|---|
| Global `MODEL × BUDGET` test | 3-df full-vs-null LRT | 3-df Wald test of the DID vector using bootstrap covariance | Yes, if covariance is finite and invertible | Yes |
| Global interaction p-value | LRT chi-square p-value | Wald DID-vector chi-square p-value | Yes, conditionally | Yes |
| Marginal probabilities | Empirical standardized cell means define DIDs | Pair/model/budget cell means are used internally | Internal estimator available; absolute cell probabilities are not emitted as a standalone result | Estimator yes; standalone output no |
| `DID_196` | Empirical probability-scale estimand | Mean pair-level DID | Yes | Yes |
| `DID_121` | Empirical probability-scale estimand | Mean pair-level DID | Yes | Yes |
| `DID_64` | Empirical probability-scale estimand | Mean pair-level DID | Yes | Yes |
| 95% confidence intervals | Pair-clustered bootstrap | Same percentile pair-clustered bootstrap | Yes | Yes |
| Raw DID p-values | Null-centered bootstrap | Same null-centered bootstrap | Yes | Yes |
| Holm-adjusted p-values | Holm across three DIDs | Same Holm family | Yes | Yes |
| SESOI classifier inputs | LRT p + DIDs + Holm p-values | Wald global p + DIDs + Holm p-values | Yes when fallback global test is estimable | Yes |

Implementation locations:

- `locked_panel_analysis.py:164-200`: pair-level DIDs, bootstrap CIs, raw
  p-values, and Holm adjustment;
- `locked_panel_analysis.py:201-217`: registered fallback global Wald test and
  `FALLBACK_GLOBAL_TEST_NOT_ESTIMABLE`;
- `locked_panel_analysis.py:296-317`: GLMM/fallback routing and classifier call;
- `interaction_decision.py:14-42`: classifier requires one finite global p-value,
  all three DIDs, and all three Holm-adjusted p-values.

The fallback is not merely a DID-only substitute. It has a separately
preregistered global interaction test. When its covariance is estimable, the
same four-case classifier can run without replacing the global test with “any
DID significant” or a CI-based rule. If covariance is not estimable, the code
returns `PRIMARY_INTERACTION_NOT_ESTIMABLE` and the four-case classifier does
not run.

**Classifier classification:** `A. FULL_CLASSIFIER_REMAINS_EXECUTABLE`

This classification concerns the fallback's registered outputs only; it does
not resolve whether the current fit exception is eligible to use it.

## 4. `diagnostics_pass=false` would be semantically invalid

The current exception occurs at `run_glmm.R:31-42`. Diagnostics are not
constructed until lines 47–80. Recording `diagnostics_pass=false` would falsely
represent unobserved diagnostics as observed failed checks and would erase the
distinction between a returned fit with failed diagnostics and no returned fit.

A minimally faithful proposed schema is:

```json
{
  "fit_status": "FIT_EXCEPTION",
  "fit_exception_class": "NUMERICAL_GLMM_FIT_EXCEPTION",
  "fit_exception_message": "Downdated VtV is not positive definite",
  "fit_stage": "FULL_OR_NULL_NOT_IDENTIFIED_BY_CURRENT_TRACE",
  "diagnostics_available": false,
  "fallback_eligibility": "FROZEN_CONTRACT_AMBIGUOUS"
}
```

Any future schema must keep these states separate:

1. `FIT_SUCCESS_DIAGNOSTICS_PASS`
2. `FIT_SUCCESS_DIAGNOSTICS_FAIL`
3. `FIT_EXCEPTION_FALLBACK_ELIGIBLE`
4. `FIT_EXCEPTION_NOT_FALLBACK_ELIGIBLE`
5. `TECHNICAL_ANALYSIS_FAILURE`

This audit does not implement that schema.

## 5. Exception scope

| Exception class | Observed here? | Frozen fallback eligibility |
|---|---:|---|
| Numerical exception thrown inside registered `glmer` fit | Yes | Ambiguous |
| Returned fit with failed convergence/Hessian/singularity/finite/separation diagnostic | No | Clearly eligible |
| Package/runtime or analysis-environment failure | No | Not covered; technical failure |
| Malformed input, missing column, row mismatch | No | Not covered; technical failure |
| Formula/config mismatch | No | Not covered; technical/protocol failure |
| File-I/O failure | No | Not covered; technical failure |
| Analysis code bug | No | Not covered; technical failure |

No evidence from this audit supports making every R exception
fallback-eligible.

## 6. Patch classification

A patch that catches this exception and automatically invokes the statistical
fallback would decide a missing eligibility rule after scientific data access
began and FULL results became known. It therefore cannot currently be labeled
an engineering-only repair.

**Patch classification:**
`POST_DATA_ACCESS_STATISTICAL_PROTOCOL_AMENDMENT_REQUIRED`

The output-schema work itself can be engineering, but routing
`NUMERICAL_GLMM_FIT_EXCEPTION` into the fallback requires an explicit human
statistical decision. No choice may depend on the unobserved reduced-budget
result.

## FACT / INFERENCE / UNKNOWN

### FACT

- The frozen fallback trigger is expressed as GLMM **diagnostic failure**.
- The registered fallback contains a conditional 3-df global test, three DIDs,
  bootstrap CIs/p-values, Holm correction, and all classifier inputs.
- The current exception occurred inside the registered `glmer` fit before
  diagnostics or `glmm_result.json` existed.
- Current Python control flow cannot reach fallback without a GLMM JSON object
  containing `diagnostics_pass`.
- No GLMM rerun, fallback, DID, CER, or component analysis occurred in this
  audit.

### INFERENCE

- The observed message is consistent with a numerical lme4/PIRLS model-fitting
  exception rather than infrastructure corruption.
- Automatically treating it as diagnostic failure would add meaning not
  currently encoded in the frozen contract.

### UNKNOWN

- Whether the full or null fit threw the exception.
- The data-specific numerical cause of the exception.
- Whether the researcher intended pre-diagnostic numerical fit exceptions to
  be fallback-eligible when freezing the phrase “fails the diagnostics.”
- All reduced-budget estimates and conclusions remain uncomputed under this
  audit authorization.

## Final classifications

- Fallback eligibility:
  `C. FROZEN_CONTRACT_AMBIGUOUS`
- Classifier under an eligible and estimable fallback:
  `A. FULL_CLASSIFIER_REMAINS_EXECUTABLE`
- Patch type required to route this exception:
  `POST_DATA_ACCESS_STATISTICAL_PROTOCOL_AMENDMENT_REQUIRED`
- Combined recommendation:
  `C. FALLBACK_ELIGIBILITY_AMBIGUOUS_POST_DATA_ACCESS_AMENDMENT_REQUIRED`

## One recommended next action

Request an explicit human statistical amendment deciding, without inspecting
any reduced-budget result, whether only this class of numerical exception from
the registered `glmer` fit is fallback-eligible; keep all environment, input,
formula/config, I/O, and code errors as technical failures.

## Stop

`GLMM_FAILURE_PATH_AUDIT_COMPLETE_PENDING_HUMAN_REVIEW`
