# Paddle/Wayu locked panel — execution attempt 2

> Status: `TECHNICAL_INVALID_PRE_SUBMISSION`
>
> Completed scientific calls: `0 / 6,400`
>
> Human review required before any further repair or submission.

## Separate identities

- `SCIENTIFIC_DESIGN_COMMIT`:
  `871996221a36a56a401fa040c239f55768561210`
- `EXECUTION_REPAIR_COMMIT`:
  `a38943d4e55759173902833b90ad3de5f4da39bd`
- Distinct Attempt 2 run ID:
  `kaggle-paddle-wayu-locked-panel-attempt2-a38943d4e557`

Attempt 1 and its `FAILURE.json` remain unchanged.

## Authorization-only staging validation

The exact rendered worker was run locally with its authorization-only stop.
It decoded the packaged artifacts from `worker.py` and exited before source
checkout, locked image generation, environment sync, or model loading.

- Result: `AUTHORIZED_TO_POINT_IMMEDIATELY_BEFORE_LOCKED_EXECUTION`
- Scientific contract valid: `true`
- Frozen design size: 9,421 bytes
- Frozen design SHA-256:
  `6143c454337570217c9cd028522de510b4fd5b4f9f361fa0ea206014eed185a1`
- Locked source bundle size: 2,114,013 bytes
- Locked source bundle SHA-256:
  `9edff88382c51ed4d48a073813b4309535fb34ba5318ea85ca8ea6da75bc229e`
- Runtime config SHA-256:
  `626484d85f252852f2b97e2ab18f529c55c56a5e62a06955ca90858adc829e5a`
- Locked allocation hash:
  `385c283091852820016bd6b1247a01af90ee04e966d298761f14cd392b8f47e8`
- BASE revision:
  `c5630abae1d940eafe0697512a0325494b02ab42`
- SPECIALIZED revision:
  `af0204b4f334a6d5068b6bac2b3738932d6e289b`

Only `worker.py` (2,844,948 bytes) and `kernel-metadata.json` were placed in
the Kaggle staging directory; the worker did not depend on an assumed
supporting-file copy.

## Submission failure

The exact submission command reached the Kaggle `SaveKernel` API and returned:

```text
400 Client Error: Bad Request for url:
https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel
```

No new kernel version was created. The existing kernel status and last-run time
still referred to Attempt 1/version 1. The API/CLI response did not provide a
more specific cause, so this report does not attribute the failure to file size
or any other unverified mechanism.

## Scientific exposure audit and stop

- Completed scientific calls: 0.
- No Attempt 2 Kaggle execution began.
- No model was loaded.
- No scientific-output artifact exists.
- No prediction, accuracy, CER, DID, omnibus statistic, component outcome, or
  FULL-validity result was produced or inspected.
- No retry, package adjustment, or resubmission was performed.

Attempt 2 is engineering-only and supplies no scientific evidence. Stop for
human review.
