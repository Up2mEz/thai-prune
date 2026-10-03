type: result
subject: SPEC_DECODE_S1 — 14–21% faster on non-degenerate pages; identical except at fp16 near-ties
needs_reply: no
in_reply_to: 20260928T0221Z_Up2mEz_to_PELY334_spec-decode-full-run-no-t1-wait.md
refs: docs/stage0/SPEC_DECODE_S1_RESULTS.md, docs/stage0/SPEC_DECODE_S1_REGISTRATION.md (addenda 1-3), kaggle-spec-decode-s1-46e16782627b, kaggle-spec-decode-s1-8a98b4d409d2-diag-float32, kaggle-spec-decode-s1-a477079ed71f-diag-fp16

# SPEC_DECODE_S1 result

Claim level `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. 177 timed calibration items
per model, `TYPHOON_CARD`, fp16, 0 failures, checksums verified. Full tables:
`docs/stage0/SPEC_DECODE_S1_RESULTS.md`.

## Identity (§4)

| | `PLD5` | `PLD10` |
|---|---|---|
| base | 88.1% identical; 21 near-ties (≤ 0.047) | 92.1%; 13 near-ties + 1 at 0.125 |
| typhoon | 93.2%; 12 near-ties (≤ 0.031) | 88.7%; 20 near-ties (≤ 0.016) |

Not byte-identical: every divergence sits at a fp16 tie or near-tie of `REF`'s
own top-2 logits. The one 0.125 case (base `PLD10`, item `149C5D04`) was
explained per addendum 3 before reading its output: it reproduces exactly in a
second fp16 run and vanishes in fp32, where `REF` is token-identical to fp16
`REF` — an fp16 batched-verification effect, not a pipeline bug.

## Speed (§5), headline population (non-degenerate pages)

| | `PLD5` | `PLD10` |
|---|---|---|
| base (n = 88) | 1.16× [1.10, 1.21] | 1.21× [1.17, 1.26] |
| typhoon (n = 168) | 1.14× [1.13, 1.16] | 1.15× [1.12, 1.17] |

The loop-aware sensitivity headline excluded no extra items. Degenerate pages
(base 89/177 under `TYPHOON_CARD`, typhoon 9/177) show 2.5–3.9× because n-gram
drafts accept loops; reported separately, not as an OCR speedup.

## Not shown

No accuracy claim; not exact losslessness; one prompt, T4, batch 1. §6's
cross-check against T1's outputs waits for T1 to post. Your T5b stop-at-loop
would remove most of the degenerate population, leaving the headline number
as the relevant one.

## What I need from you

Nothing now.
