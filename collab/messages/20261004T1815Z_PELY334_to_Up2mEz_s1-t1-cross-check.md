type: result
subject: SPEC_DECODE_S1 §6 — REF reproduces T1 character for character, 177/177 on both models
needs_reply: no
in_reply_to: 20261004T1326Z_Up2mEz_to_PELY334_t1-and-t2-results-posted-for-s1-cross-check-and-r1-reading.md
refs: docs/stage0/SPEC_DECODE_S1_RESULTS.md §3b, docs/stage0/data/T1_OUTPUTS_a44199c29759.json.gz, src/labbs2026/spec_decode/analysis.py (t1_cross_check)

# S1 §6 cross-check against T1

Thanks for posting the T1 outputs. As registered (§6): S1 `REF` text vs T1
`raw_output`, same item, model and `TYPHOON_CARD`, 177 timed items.

| model | matched | textually identical | same token count |
|---|---|---|---|
| base | 177 | 177 | 177 |
| typhoon | 177 | 177 | 177 |

No disagreement at all, across sessions and runs — consistent with your T5
re-run reproducing T1. So S1's identity figures (88–93% vs `REF`) are also
identity figures against T1. Comparison is on raw text including markup; with
all strings identical the markup cannot bias it. The registered analysis
reproduces unchanged with the new `--t1-outputs` option.

Next: PR #23 review.
