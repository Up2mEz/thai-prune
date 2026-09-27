# Paddle/Wayu locked panel — Attempt 2 HTTP 400 diagnostic

> Terminal state: `ATTEMPT_2_HTTP400_ROOT_CAUSE_PENDING_HUMAN_REVIEW`
>
> Authentication: `AUTH_CONFIRMED`
>
> Root-cause classification: `D. PACKAGE_OR_PAYLOAD_LIMIT_ERROR`
>
> Attempt 3 is not authorized and was not submitted.

## Scope and scientific-integrity audit

This was a read-only/locally reconstructed engineering diagnostic. It did not
change commit `871996221a36a56a401fa040c239f55768561210` or any frozen scientific
condition. No locked image was generated, no model was loaded, no scientific
prediction or metric was opened, and no `SaveKernel` request was sent.

- Completed scientific calls: `0 / 6,400`.
- Attempt 2 Kaggle version created: `false`.
- Retry/resubmission: `false`.
- Scientific output produced or inspected: `false`.

## 1. Authentication sanity check

- Kaggle CLI: `Kaggle CLI 2.2.4`.
- Effective user: `thanakritsamoena`.
- Active mechanism: `OAUTH`, stored in Kaggle's config location
  `C:\Users\acer\.kaggle`.
- `kaggle config view`, sanitized: `path=None`, `proxy=None`,
  `competition=None`; no secret value was printed or preserved.
- No `KAGGLE*` environment variable, legacy `kaggle.json`, or
  `.config/kaggle/access_token` was present.
- Read-only authenticated check: `kaggle kernels list --mine --page-size 3 -v`
  succeeded and returned the user's kernels.

Classification: `AUTH_CONFIRMED`. Credential rotation is neither indicated nor
performed.

## 2. HTTP 400 response preservation and local request reconstruction

The immutable Attempt 2 failure record preserves:

| Field | Preserved value |
|---|---|
| HTTP status | `400` |
| client-visible message | `400 Client Error: Bad Request for url: https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel` |
| endpoint used by Attempt 2 | `https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel` |
| client exception family | `requests.exceptions.HTTPError` (established from the installed client path handling this response) |
| full response body | unavailable: not emitted or stored by the non-verbose Attempt 2 CLI invocation |
| Kaggle error code/message | unavailable beyond generic `Bad Request` |
| field-validation errors | unavailable |
| request ID | unavailable |

The installed CLI catches `HTTPError` and prints only `str(error)` unless the
client was run verbose. The HTTP client itself retains `error.response` and, in
verbose mode, can print `response.text`; therefore the missing body cannot be
recovered from the saved Attempt 2 artifacts without another network request.
No request was repeated merely to obtain the body.

`scripts/diagnose_kaggle_savekernel.py` now provides two fail-closed paths:

1. its default mode replaces the Kaggle transport with a capture object,
   constructs and serializes the exact `ApiSaveKernelRequest`, and records
   `network_calls: 0`;
2. its explicit `--submit-once` mode, reserved for a separately authorized
   future submission, records status, complete response body/JSON, request ID
   headers, exception type, and sanitized request metadata, and never retries.

The explicit submission mode was not executed in this diagnostic.

Local reconstruction produced `POST /api/v1/kernels/push` with request class
`ApiSaveKernelRequest`. Attempt 2 serialized successfully and raised no local
exception; this makes a local serialization defect unsupported.

## 3. Exact execution/submission metadata diff

The two reference runs completed through Kaggle previously. Scientific outputs
were neither opened nor compared.

| Field | Successful smoke | Successful S0 | Attempt 2 | Difference relevant to rejection |
|---|---|---|---|---|
| owner | `thanakritsamoena` | same | same | none |
| kernel slug | `labbs2026-paddle-wayu-smoke` | `labbs2026-paddle-wayu-s0-open-calibration` | `labbs2026-paddle-wayu-locked-model-budget-panel` | expected identity change |
| title | `LabBS2026 Paddle Wayu Engineering Smoke` | `LabBS2026 Paddle Wayu S0 Open Calibration` | `LabBS2026 Paddle Wayu Locked Model Budget Panel` | expected identity change |
| local code filename | `worker.py` | `worker.py` | `worker.py` | none |
| language | `python` | `python` | `python` | none |
| kernel type | `script` | `script` | `script` | none |
| private | `true` | `true` | `true` | none |
| GPU | `true` | `true` | `true` | none |
| internet | `true` | `true` | `true` | none |
| TPU | `false` | `false` | `false` | none |
| machine shape | `NvidiaTeslaT4` | same | same | none |
| dataset sources | omitted/empty | omitted/empty | omitted/empty | none |
| kernel sources | omitted/empty | omitted/empty | omitted/empty | none |
| competition sources | omitted/empty | omitted/empty | omitted/empty | none |
| model sources | omitted/empty | omitted/empty | omitted/empty | none |
| source directory | each run's `staging/` | each run's `staging/` | each run's `staging/` | same layout |
| API request endpoint/method | `POST /api/v1/kernels/push` | same | same | none |
| client version | `2.2.4` | same reconstructed client | same | none |
| file count | `2` | `2` | `2` | none |
| bundle bytes | `7,196` | `6,380` | `2,845,323` | Attempt 2 is 395–446 times larger |
| code bytes (`request.text`) | `6,849` | `6,017` | `2,844,948` | sole material request-shape difference |
| metadata bytes | `347` | `363` | `375` | small expected title/slug difference |

The local request JSON, excluding source text, differs only in `slug` and
`newTitle`. The title/slug mismatch warning observed for the successful smoke
also rules out that warning as the cause.

## 4. Remote-state verification

Read-only `GetKernel`, status, list, and pull operations established:

- `current_version_number: 1`;
- kernel ID `134190206`;
- pulled latest code is the 7,302-byte Attempt 1 worker;
- latest remote metadata has no dataset/kernel/competition/model sources;
- status is `KernelWorkerStatus.ERROR`, not queued or running;
- there is no version 2 and no hidden/partial Attempt 2 execution visible to
  the authenticated API.

The remote object therefore remains Attempt 1/version 1. The stop-on-existing-
remote-version condition was not triggered.

## 5. Package audit

Attempt 2 staging contains exactly `worker.py` (2,844,948 bytes) and
`kernel-metadata.json` (375 bytes), total 2,845,323 bytes.

The worker contains one Base64 payload for the frozen design (original 9,421
bytes; encoded literal 12,564 characters) and one for the locked source bundle
(original 2,114,013 bytes; encoded literal 2,818,684 characters). The source
ZIP contains 803 members: 800 PNG and 3 JSON files, 3,794,984 uncompressed
bytes. No content-hash duplicate occurs inside the ZIP.

No separate `runs/`, model weights, cache, or evidence bundle is present in the
staging directory. The large content is the execution-required locked source
bundle encoded into the Python source, not an accidental unrelated directory.
Nothing was removed.

## 6. Root-cause classification

`D. PACKAGE_OR_PAYLOAD_LIMIT_ERROR`

Evidence chain:

1. authentication and multiple read-only endpoints succeed;
2. the remote kernel remains version 1, so the failure is before execution;
3. the locally built request serializes successfully;
4. every execution metadata field matches successful submissions except the
   expected identity strings;
5. Attempt 2 sends 2,844,948 bytes as kernel source, versus 6,017–6,849 bytes
   for successful controls;
6. [Kaggle's kernel CLI documentation](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md)
   confirms that `kernels push` uploads the source selected by kernel metadata,
   and a [Kaggle-hosted incident report](https://www.kaggle.com/product-feedback/236663)
   documents the same HTTP 400 behavior when kernel source exceeds the
   platform's 1 MB source limit.

The absent original response body prevents direct recovery of Kaggle's own
field-level wording. Accordingly, the classification is a strongly supported
engineering inference, not a newly observed server error message. The evidence
does not support authentication, source-reference, serialization, quota, or
transient-service classifications.

## 7. Narrowest repair proposal — not applied

Keep the 9,421-byte frozen design embedded in `worker.py`, but move only the
immutable 2,114,013-byte locked source ZIP to a private, version-pinned Kaggle
Dataset. Add that exact dataset version as `dataset_sources`; before any locked
image generation or model loading, require the worker to locate the ZIP and
verify its existing SHA-256
`9edff88382c51ed4d48a073813b4309535fb34ba5318ea85ca8ea6da75bc229e`.

This proposal changes transport only. It does not alter the scientific design,
frozen-design SHA-256, locked allocation, models/revisions, prompt/parser,
budgets, resizing, analysis, SESOI, or decision rules. Creating the Dataset,
editing the staging metadata/worker, or submitting Attempt 3 requires another
human authorization and was not done.

## Preserved evidence

- `docs/stage0/evidence/paddle_wayu_locked_panel_attempt_2_http400/ARTIFACTS.md`
- `docs/stage0/evidence/paddle_wayu_locked_panel_attempt_2_http400/auth_sanity.json`
- `docs/stage0/evidence/paddle_wayu_locked_panel_attempt_2_http400/http400_capture.json`
- `docs/stage0/evidence/paddle_wayu_locked_panel_attempt_2_http400/request_diff.json`
- `docs/stage0/evidence/paddle_wayu_locked_panel_attempt_2_http400/remote_state.json`
- `docs/stage0/evidence/paddle_wayu_locked_panel_attempt_2_http400/package_audit.json`
- ignored immutable local reconstruction:
  `runs/kaggle/kaggle-paddle-wayu-locked-panel-attempt2-a38943d4e557/savekernel_request_construction.json`

No scientific claim is supported by this diagnostic.
