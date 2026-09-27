# Paddle/Wayu locked panel — Attempt 4 execution identity

> Authorization: `LOCKED_PANEL_RERUN_AUTHORIZED`

## Committed identity

- Attempt: `4`
- Run ID: `kaggle-paddle-wayu-locked-panel-attempt4`
- Scientific design commit:
  `871996221a36a56a401fa040c239f55768561210`
- Identity source:
  `configs/runtime/kaggle_locked_panel_attempt4_transport.yaml`

The run ID is stable and does not contain the execution commit SHA. The
lifecycle script reads attempt number, authorization label, and run ID from
the single committed identity source. There is no CLI or environment override
for these fields.

Bootstrap writes the same identity into `AUTHORIZATION_VALIDATED.json`. Core
requires exact agreement with the execution spec and explicitly requires
Attempt 4. Attempt-3 identity and mixed identities fail closed.

## Engineering changes only

The patch changes Attempt identity, its validation, engineering failure
evidence, import preflight diagnostics, tests, and documentation. It does not
change the model pair/revisions, locked allocation, source content, prompt,
parser, budgets, resize implementation, metrics, GLMM, uncertainty,
multiplicity, SESOI, decision classifier, blinding, or sealed scientific
outputs.

## Local validation

```text
focused identity/handoff tests: 29 passed
full suite: 181 passed, 1 skipped
scientific design diff: PASS_EMPTY
```

The skipped test is the existing optional Kaggle Python-client import test in
the default local environment. The system Kaggle CLI used for submission is
validated separately before submission.
