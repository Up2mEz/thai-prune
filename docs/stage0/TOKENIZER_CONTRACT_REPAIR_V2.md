# Stage 0 Repair v2 — Tokenizer and Generation-Boundary Audit

**Status:** `VERIFIED_BEFORE_REPAIR_V2_INFERENCE`

The audit used the pinned `Qwen2Tokenizer` from
`Qwen/Qwen2.5-VL-3B-Instruct@66285546d2b821cf421d4f5eb2576359d3770cd3`,
the unchanged `stage0_forced_choice_th_v1` prompt, and the already exposed
calibration pair `base_ka_pha`.

The actual chat template ends the model input with
`<|im_start|>assistant\n`. Appending canonical `A` or `B` leaves the prefix
tokenization unchanged and adds exactly one token:

| Continuation | Token IDs | Interpretation |
|---|---|---|
| `A` | `[32]` | valid canonical label |
| `B` | `[33]` | valid canonical label |
| ` A` | `[362]` | distinct leading-space token; not canonical |
| ` B` | `[425]` | distinct leading-space token; not canonical |
| `A\n` | `[32, 198]` | two-token continuation |
| `B\n` | `[33, 198]` | two-token continuation |

Therefore Repair v2 can preserve the registered exact `^[AB]$` parser by
generating exactly one token and constraining that token to IDs 32 or 33.
Runtime code must re-resolve and verify this mapping for the exact prompt and
pinned tokenizer before every prediction. Any mismatch is an output-contract
failure and must stop the run rather than fall back to a permissive parser.

The machine-readable record is
`docs/stage0/tokenizer_contract_repair_v2.json`. This audit does not expose a
locked-validation pair and is not visual-accuracy evidence.
