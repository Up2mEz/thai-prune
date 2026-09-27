# Attempt 2 HTTP 400 diagnostic evidence

All entries are engineering-only and contain no scientific predictions.

| File | SHA-256 |
|---|---|
| `auth_sanity.json` | `f5f712a048d76a1920c187bbff6861bf7c62ee6957f243b5e970fe979d6bcc8b` |
| `http400_capture.json` | `97952786e900a3fe7ea5a7a3ab7f4add74100238d440426b0d0c5c95617d7d82` |
| `package_audit.json` | `ed7ca90677d3d025a24b68ca2c404c7422eac085fca6f78fbf8fd60075480cf5` |
| `remote_state.json` | `c305a6322640ae681b2ea2e6154a014275cd6ee608c3a915e7ac0c1eb75a747b` |
| `request_diff.json` | `f2d40288cfb3ccfe5553d434b4f10107acf923578139a411903dcfb9f8bead1c` |

The ignored local request-construction artifacts record `network_calls: 0` and
are preserved under the immutable Attempt 2 run directory. The original
Attempt 2 HTTP response body and request headers were not captured by the CLI;
their absence is recorded rather than reconstructed.
