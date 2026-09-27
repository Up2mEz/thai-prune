# Qwen3.5 Measurement-Contract Pilot Artifacts

Run: `kaggle-qwen35-contract-39dd41767265-c32968de`

Source Git SHA: `39dd417672656d18d38a640e5b77452740afcab7`

The immutable raw inference evidence is `BC_raw_outputs.jsonl`; it contains
all 400 B/C outputs, raw decoded text, generated token IDs, and per-observation
visual-token metadata. `stimulus_manifest.jsonl` records all B/C image and
target-layer hashes. `measurement_contract_pilot_analysis.json` is registered
analysis schema v2; the earlier local schema-v1 analysis remains preserved in
the run directory and was not overwritten.

`verification.json` records `VERIFIED`, including B=200, C=200, 25 selected
pairs, 200/200 pixel-identity checks, no artifact checksum failure,
`locked_pair_count=0`, no compression, and Gate 0 `NOT_RUN`.

## SHA-256

```text
313701dd28707cd6da5edccbac81d5ceedccd4e4fc22b2c084459b468316b420  BC_raw_outputs.jsonl
0c9fa2379da0a9a43fa32d73145789b3ebe9dde6951f9fd509ba3e61dad399f7  checksums.sha256
37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570  execution_failures.json
aeff2add065830bc790fa021fbbfbf05697485587c69d89ae16839ff7e74052e  measurement_contract_pilot_analysis.json
e7d54e3a3a591a619d5917ef01ea7dc5f75ceb955c57bb34348b7dd7ded80d6c  paired_observations.jsonl
bb2e67362dadbb984e3b545d13a23a00bd5ba1be84fd2ba4f6d93718a75f12c0  preflight.json
c7e4a661a5140cef11909081aeac23b9a80c79f7b71b875b945c42b42845693c  run_spec.json
b7013e54162102e1cd5b41ca19ff82d9d3f5190be2e21c567cb06c5b39ae6f72  runtime.json
8764be312e6868b3e6fe3c79def7d6d8a8a721340f04aa5d2f77cf3ffcf2d0ae  stimulus_manifest.jsonl
c7e4a661a5140cef11909081aeac23b9a80c79f7b71b875b945c42b42845693c  submission.json
dd21179418df0c5b5118c0dd21e9e3a44fd992fc5726f125d4a531c3210c65c6  submission_manifest.json
85f14ecd07ce657781e8fbc9c343e9bfd06667eff7aaa666d39809feac94606f  SUCCESS.json
44ba6b840110cc428e524592f88f16c575ccc964903e02535ddbb3ec76eee582  verification.json
```
