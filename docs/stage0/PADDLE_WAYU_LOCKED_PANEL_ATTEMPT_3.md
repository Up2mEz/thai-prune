# Paddle/Wayu locked panel — execution attempt 3

> Status: `LOCKED_PANEL_TECHNICAL_INVALID_SCIENTIFIC_OUTPUTS_REMAIN_SEALED`
>
> Human review is required before any repair or further submission.

## Registered identity

- Frozen scientific design commit:
  `871996221a36a56a401fa040c239f55768561210`
- Attempt 3 execution repair commit:
  `5091c573b7c7f97ad8696ddf3bd875471a21d08f`
- Run ID: `kaggle-paddle-wayu-locked-panel-attempt3-5091c573b7c7`
- Private Kaggle kernel:
  `thanakritsamoena/labbs2026-paddle-wayu-locked-model-budget-panel`, version 2,
  kernel ID `134190206`
- Private source Dataset:
  `thanakritsamoena/labbs2026-paddle-wayu-locked-source`, numeric ID
  `12006749`, version 1
- Original transport archive SHA-256:
  `9edff88382c51ed4d48a073813b4309535fb34ba5318ea85ca8ea6da75bc229e`
- Frozen content-manifest SHA-256:
  `5b0983c7cc75e2904ac240ef0adc0472a9bf2bbe4695fb0669f7f9f36e2eaebb`

## Submission audit

- Authorization-only validation passed before submission.
- The staging allowlist contained only `kernel-metadata.json` and `worker.py`.
- Total submitted bundle size was 84,811 bytes.
- Dataset version 1 was confirmed private immediately before submission.
- Exactly one `SaveKernel` call was made for Attempt 3.
- Kernel version 2 was created and ran once.
- No retry, resubmission, or Dataset version 2 was created.

## Runtime source verification

The runtime worker reached
`AUTHORIZED_TO_POINT_IMMEDIATELY_BEFORE_LOCKED_EXECUTION` and verified:

- exactly one expanded `locked_source/` directory;
- 803 manifest members;
- 3,794,984 total uncompressed bytes;
- exact relative path set;
- every file size;
- every file SHA-256;
- frozen-design and content-manifest identities.

This establishes that the approved expanded-file transport reached the worker
unchanged. It is engineering provenance evidence only.

## Technical failure

The kernel then returned `ERROR`. The terminal exception in the preserved log
was:

```text
FileExistsError: [Errno 17] File exists:
'/kaggle/working/artifacts/kaggle-paddle-wayu-locked-panel-attempt3-5091c573b7c7'
```

The bootstrap worker had already created that directory to write
`engineering/AUTHORIZATION_VALIDATED.json`. The core
`execute_remote_panel()` entrypoint then attempted to create the same directory
with `exist_ok=False` and stopped before entering the scientific workload.

The log also contains an earlier `sitecustomize` warning that `wrapt` was not
available. That warning is not the terminal exception and the preserved
evidence does not establish it as the cause of this failure.

## Scientific exposure and workload audit

- Completed model calls: 0 of 6,400.
- CUDA/model preflight did not begin.
- Neither model was loaded.
- No locked image was generated or decoded.
- No `sealed/` directory, raw-output file, or call ledger exists in the
  downloaded output.
- No scientific prediction, accuracy, CER, DID, component outcome, Gate-0
  result, or registered analysis was displayed, inspected, or calculated.

Attempt 3 is therefore a pre-inference technical invalidation and provides no
scientific evidence about either model or controlled BICUBIC Input Resolution
Reduction.

## Preservation and stop

The downloaded engineering records, kernel log, and remote source snapshot were
hashed and marked read-only locally. Their hashes are recorded under
`docs/stage0/evidence/paddle_wayu_locked_panel_attempt_3/ARTIFACTS.md`.

No repair was implemented. No additional Kaggle submission was made. A narrow
future engineering repair would need to resolve ownership of the run artifact
directory without changing any frozen scientific element, but such a repair is
not authorized here.

Terminal state: `HUMAN_REVIEW_AFTER_ATTEMPT_3_PRE_INFERENCE_TECHNICAL_FAILURE`.
