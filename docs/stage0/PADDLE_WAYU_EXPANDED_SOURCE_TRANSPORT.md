# Paddle/Wayu expanded locked-source transport amendment

> Engineering transport amendment only.
>
> Scientific design commit remains
> `871996221a36a56a401fa040c239f55768561210`.

Kaggle expanded the uploaded archive. Scientific input identity is therefore
verified using exact relative-path and uncompressed-file SHA-256 membership,
rather than requiring preservation of the ZIP container bytes.

## Frozen identities

- `ORIGINAL_TRANSPORT_ARCHIVE_SHA256`:
  `9edff88382c51ed4d48a073813b4309535fb34ba5318ea85ca8ea6da75bc229e`
- `LOCKED_CONTENT_MANIFEST_SHA256`:
  `5b0983c7cc75e2904ac240ef0adc0472a9bf2bbe4695fb0669f7f9f36e2eaebb`
- `KAGGLE_DATASET_ID`: `12006749`
- `KAGGLE_DATASET_VERSION`: `1`
- Dataset owner/slug:
  `thanakritsamoena/labbs2026-paddle-wayu-locked-source`
- Dataset visibility: private
- Content members: `803`
- Total uncompressed bytes: `3,794,984`

The original archive remains unchanged and is not recreated or recompressed.
Its hash is historical transport provenance; the frozen content manifest is
the runtime scientific-input identity.

## Manifest construction safety

The manifest records each regular member's normalized relative POSIX path,
uncompressed byte size, and uncompressed SHA-256 in lexicographic path order.
Construction rejects duplicate paths, absolute/traversal paths, symlinks,
non-regular entries, case collisions, non-NFC paths, backslashes, and ambiguous
normalization. Directory entries are validated but excluded from scientific
records.

No image was rendered, decoded, displayed, normalized, altered, or interpreted
while constructing or checking the manifest.

## Dataset version 1 verification

Read-only download and verification of the existing private Dataset version 1
found exactly one expanded `locked_source/` directory. Exact file-set, every
file size, every SHA-256, member count, total uncompressed bytes, external
manifest hash, and frozen content-manifest hash all passed.

The worker repeats these checks before source checkout, environment setup,
locked image generation, or model loading. The execution module verifies the
same content manifest again before copying the expanded source into sealed
artifacts. It never creates a replacement ZIP.

No research hypothesis, estimand, analysis, budget, Dataset membership,
stimulus, model revision, prompt, parser, or claim boundary changes.

