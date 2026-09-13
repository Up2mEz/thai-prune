# Attempt 3 engineering evidence

The private Kaggle version-2 output contained exactly two files under the run
artifact directory: `engineering/AUTHORIZATION_VALIDATED.json` and
`engineering/FAILURE.json`. It contained no `sealed/` directory, scientific
raw-output artifact, or call ledger.

The downloaded files and read-only remote snapshot remain in the ignored local
run directory. They were marked read-only after download. SHA-256 identities:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `fetched/.../engineering/AUTHORIZATION_VALIDATED.json` | 1,430 | `ef12ebfba939cc4bef8d6b47c47f60d3516b4ed6107258b95d0d4eb5204b1ece` |
| `fetched/.../engineering/FAILURE.json` | 307 | `c7811a38d4643cf6279a34b2c32dd3ebd3a678070455655b102bf677d6f3aeb8` |
| `fetched/labbs2026-paddle-wayu-locked-model-budget-panel.log` | 2,971 | `82c3b74702e3afef1215077577ef00f9e951ae53caaee28d1696a9a69c24b239` |
| `remote_snapshot/kernel-metadata.json` | 740 | `6a5980a3c2aba66779df396c1baa72145a64614d1e1882da589f27d7f29a7c0c` |
| `remote_snapshot/labbs2026-paddle-wayu-locked-model-budget-panel.py` | 84,681 | `1d56d21724f71390e4d1a9233add0428c3c467abf747128d2a0b138cfb72ace9` |

The tracked `AUTHORIZATION_VALIDATED.json` and `FAILURE.json` in this evidence
directory reproduce the corresponding engineering records semantically in
pretty-printed JSON. The byte-for-byte originals remain in the ignored run
directory and are identified above.

`SUBMISSION.json` records the submission identity and the single authorized
`SaveKernel` call. No credential or scientific output is included.
