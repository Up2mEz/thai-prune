# Paddle/Wayu artifact handoff repair

> Status: `ARTIFACT_HANDOFF_REPAIR_VALIDATED_PENDING_RERUN_AUTHORIZATION`
>
> This is a local engineering-only repair. Kaggle resubmission is not authorized.

## Root cause and repair boundary

Attempt 3 failed because bootstrap created the run artifact directory for its
authorization record and core subsequently attempted to create the same
directory with `exist_ok=False`. The repair changes only the ownership handoff;
it does not change any scientific condition.

Bootstrap now creates exactly:

```text
<artifact_root>/
└── engineering/
    └── AUTHORIZATION_VALIDATED.json
```

The authorization file is written through the existing atomic temporary-file
replacement path. Bootstrap rejects an already-existing artifact root.

Core performs an exact inventory and symlink audit, validates the authorization
schema and every registered execution/source identity, and then creates
`engineering/CORE_OWNERSHIP_CLAIMED.json` with create-exclusive semantics. It
creates an empty `sealed/` directory with `exist_ok=False` only after the claim
succeeds.

## Fail-closed authorization checks

Core verifies:

- `run_id`, scientific-design commit, and execution commit;
- frozen-design and locked-content-manifest SHA-256 values;
- Kaggle Dataset numeric ID and version;
- exact expanded-source path, member count, total bytes, manifest identity,
  original archive provenance, and the three source-verification booleans;
- `authorization_only == false` and `scientific_contract_valid == true`;
- exact root and `engineering/` inventories;
- absence of symlinks, `sealed/`, `SUCCESS.json`, call ledger, and prior
  ownership marker.

The ownership claim records the authorization artifact SHA-256, timestamp,
run ID, both commit identities, frozen-design SHA-256, and content-manifest
SHA-256.

## Failure evidence

Artifact initialization now runs inside core's structured failure boundary.
After ownership, core failures retain the original exception type, message, and
traceback in `engineering/FAILURE.json`.

Before ownership, bootstrap remains the independent failure channel. A failed
core subprocess is represented as `CoreSubprocessFailure` and preserves its
return code, stdout, stderr, and outer traceback. An existing specific core
failure record is never replaced with a generic bootstrap record. Bootstrap
also writes a sibling `_bootstrap_failures/<run_id>.json` record, so preserving
the failure does not depend on the run artifact root being a usable directory.

## Tests

The new tests cover:

- exact expected bootstrap tree;
- valid authorization and one successful ownership claim;
- missing or invalid authorization;
- identity and hash mismatch;
- unexpected file or directory;
- pre-existing `sealed/`, `SUCCESS.json`, call ledger, or ownership claim;
- second initialization;
- symlink rejection;
- the actual bootstrap writer and core subprocess boundary, stopping after
  ownership and empty `sealed/` creation.

Results:

```text
focused handoff/worker/panel tests: 24 passed
full suite: 176 passed, 1 skipped
```

The single skip is the existing optional Kaggle-client import test because the
local default test environment does not install the Kaggle package.

## Environment preflight

An import-only check using the locked `model` extra passed for `accelerate`,
`huggingface_hub`, `numpy`, `PIL`, `torch`, `torchvision`, `transformers`,
`yaml`, `qwen_vl_utils`, and the three runtime project modules. It performed no
model download or inference.

`wrapt` is not in `uv.lock` and is not imported by the locked-panel runtime.
It was not added. The previous warning came from Kaggle `sitecustomize`; it is
not established as an application dependency or as the Attempt 3 failure cause.
The worker now performs the real import set after the frozen environment sync
and hashed Transformers override, before launching core in any future
authorized remote execution.

## Scientific-design diff assertion

The repair has no diff against frozen commit
`871996221a36a56a401fa040c239f55768561210` for:

- `configs/stage0/overall_model_budget_design.yaml`;
- `configs/stage0/calibration_design.yaml`;
- `configs/runtime/kaggle_t4_paddle_wayu.yaml`;
- `src/labbs2026/stage0/resolution_pipeline.py`.

No Dataset content, model identity, prompt, parser, budget, metric, statistical
test, SESOI, multiplicity rule, classifier, blinding rule, or scientific
sealed-output behavior was changed.

## Stop

No `SaveKernel`, locked image generation, model loading, or model inference was
performed. A future rerun requires a separate human authorization.
