# Paddle/Wayu locked panel — Attempt 5 execution identity

> Authorization: `ATTEMPT5_FRESH_FULL_LOCKED_PANEL_AUTHORIZED`

## Exact identities

- Attempt: `5`
- Run ID: `kaggle-paddle-wayu-locked-panel-attempt5`
- Original scientific-design commit:
  `871996221a36a56a401fa040c239f55768561210`
- Accepted U+FFFD protocol-amendment commit:
  `ee9f8c4f85feea935f8c99d05005deea16c30442`
- Attempt-5 execution commit: resolved from the exact committed and pushed
  `HEAD`; it is recorded separately in the execution spec, authorization
  artifact, run manifest, and failure evidence.
- Committed identity source:
  `configs/runtime/kaggle_locked_panel_attempt5_transport.yaml`

The effective scientific protocol is
`ORIGINAL_SCIENTIFIC_DESIGN_PLUS_U_FFFD_PER_CALL_PROTOCOL_AMENDMENT`. Attempt 5
must not be described as using only the original design commit.

The stable run ID does not contain the execution commit SHA. Attempt number,
authorization label, and run ID have no CLI or environment override.
Bootstrap receives them from the packaged execution spec; core validates them
against both that authorization artifact and the same committed identity file.

## Scope of this patch

This patch changes only Attempt-5 execution identity/provenance handling,
identity and handoff tests, and engineering decision documentation. It does not
change models/revisions, Dataset or allocation, prompt, generation, decoding,
budgets, BICUBIC resize, metrics, statistical analysis, multiplicity, SESOI,
decision classifier, or validity thresholds beyond the already accepted U+FFFD
per-call amendment.

Preflight compares the execution revision against the accepted amendment and
requires:

`ADDITIONAL_SCIENTIFIC_DIFF_AFTER_ACCEPTED_AMENDMENT_EMPTY`

## Attempt 4 boundary

Attempt 4 remains `PARTIAL_SCIENTIFIC_OUTPUTS_SEALED` at 4,136/6,400 calls.
Its canonical artifact SHA-256 is
`e6db8c69b530464bbebdcfa0c8640c1b3c1f771d4b5f89fcb71ef2af8cca8127`.
No Attempt-4 call may be resumed, reused, inspected, compared, or included in
Attempt 5.

## Execution boundary

Exactly one Kaggle submission is permitted only after all local, Git, Dataset,
package, runtime-import, authorization, and handoff checks pass. Automatic
retry, a second `SaveKernel` request, metadata fallback, alternate execution
commit, and Attempt 6 are not authorized.
