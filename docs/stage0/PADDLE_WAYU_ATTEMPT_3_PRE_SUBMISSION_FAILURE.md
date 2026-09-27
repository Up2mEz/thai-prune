# Paddle/Wayu locked panel — Attempt 3 pre-submission failure

> Status: `ATTEMPT_3_PRE_SUBMISSION_ENGINEERING_VALIDATION_FAILED`
>
> `SaveKernel` calls: `0`
>
> Scientific model calls: `0 / 6,400`
>
> Stop for human review.

## Authorization and boundary

The human accepted `PACKAGE_OR_PAYLOAD_LIMIT_ERROR` and authorized
`PACKAGE_LIMIT_REPAIR_AND_ATTEMPT_3`. The permitted repair was limited to
moving the locked-source archive out of the kernel source and into a private
Kaggle Dataset. The frozen scientific design remains commit
`871996221a36a56a401fa040c239f55768561210` with frozen-design SHA-256
`6143c454337570217c9cd028522de510b4fd5b4f9f361fa0ea206014eed185a1`.

## Local dataset staging

Local staging contained only the two intended data files plus Kaggle's local
metadata control file:

| File | Bytes | SHA-256 |
|---|---:|---|
| `locked_source.zip` | 2,114,013 | `9edff88382c51ed4d48a073813b4309535fb34ba5318ea85ca8ea6da75bc229e` |
| `locked_source_manifest.json` | 321 | `d422ba795b02404ff496b1611653a3401992ee2d452b93b9a5b4712a33ea1487` |

The archive's internal manifest SHA-256 was
`572ca192fb360121fba7eabd7d347492dd276069c11d3528db7130b572f2b26a`.
Local validation checked the archive hash, byte size, internal manifest, all
member hashes, 100 registered locked pairs, and 800 PNG sources without visual
inspection. All local checks passed.

## Private Dataset creation identity

- Owner/slug: `thanakritsamoena/labbs2026-paddle-wayu-locked-source`
- Dataset ID: `12006749`
- Version: `1`
- Status: `ready`
- Visibility: `private` (`isPrivate: true`)
- Creation/update timestamp reported by the API:
  `2026-09-13T12:40:50.357000`

The installed client was given the owner/slug form only. No unsupported Dataset
version syntax was invented.

## Fail-closed finding

Kaggle accepted the upload but automatically expanded `locked_source.zip` into
remote paths under `locked_source/`. A read-only exact-file download for
`locked_source.zip` returned HTTP 404, while
`locked_source_manifest.json` remained directly downloadable with the expected
SHA-256.

Therefore the mandatory pre-submission conditions did not all pass:

| Check | Result |
|---|---|
| private Dataset exists | PASS |
| Dataset identity/version recorded | PASS |
| external manifest exact hash | PASS |
| exactly one expected `locked_source.zip` exists remotely | **FAIL** |
| worker can resolve and hash the required archive | **FAIL** |
| frozen design embedded/hash checked | implemented locally; Attempt 3 staging not built |
| model loading absent | PASS |
| scientific image inspection absent | PASS |

Per the explicit stop rule, no Dataset version repair, kernel staging,
`SaveKernel`, retry, model loading, locked call, or scientific analysis followed.
The private Dataset was not deleted or made public.

## Engineering implementation state

The unsubmitted repair implementation:

- attaches only `thanakritsamoena/labbs2026-paddle-wayu-locked-source` through
  `dataset_sources`;
- removes the large archive Base64 placeholder from the worker;
- keeps the frozen design embedded;
- requires exactly one archive and manifest under the Dataset mount;
- verifies external-manifest, archive, internal-manifest, and member hashes
  before any source use;
- uses an explicit two-file kernel staging allowlist and a distinct Attempt 3
  run ID.

It was not pushed for remote execution and no Attempt 3 submission directory
was produced because the remote Dataset gate failed first.

## Next decision required

Kaggle's archive-expansion behavior conflicts with the authorized requirement
that the attached Dataset expose an exact `locked_source.zip`. Any alternative
such as transporting the same bytes under a non-archive filename and restoring
the required local filename only after hash verification changes the approved
transport contract and requires human review before implementation or Dataset
versioning.

No scientific inference can be drawn from this engineering failure.

