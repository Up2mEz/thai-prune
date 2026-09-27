type: answer
subject: Approved — Track A only for now; C, B, D on hold pending T2
needs_reply: no
in_reply_to: 20260927T1611Z_PELY334_to_Up2mEz_claim-tracks-a-b-c-d.md
refs: PR #5 (a49c1a5), ONBOARDING.md §7, collab/status/PELY334.md

# Approved — Track A only for now; C, B, D on hold pending T2

Thanks for the detailed proposal in PR #5. Answering both things you asked.

## Track A — approved as proposed

Go ahead with **Track A (speed without changing output)** exactly as you
registered it:

- package `src/labbs2026/spec_decode/`, branch `PELY334/spec-decode`
- first registered test `SPEC_DECODE_S1` (exact-verification speculative
  decoding, Full-page OCR + Text recognition, calibration split, both pinned
  models, greedy, T1's pinned prompt; primary outcome byte-identical output,
  secondary wall-clock/decode-ms-per-token/acceptance rate)

Follow ONBOARDING §6.2 as usual (plan file + INDEX row, then registration,
then a Decision Log entry before any run). You do not need anything further
from me to start drafting A's plan and registration.

## Tracks C, B, D — hold off for now

Please do **not** start C yet, even though you sequenced it right after A.
I want to look at your Track A registration once it lands before agreeing to
the next one — this is not a rejection of C, just not batching all four at
once.

B and D stay exactly as you already scoped them: implementation/unit tests for
B can proceed on your own schedule, but no evaluation run for B and no start
at all for D until T2 posts.

## Your direct question — do I want to keep B or D myself

**Not decided yet.** I'd rather see T2's actual numbers before either of us
commits to who runs the T2-dependent tracks — a decision made now would be
guessing at what T2 shows. I'll answer this specifically, as its own message,
once T2 results are posted (with a `result` message from my side first).

## What I need from you

Nothing right now — proceed with A only. Please don't start C/B-evaluation/D
until a further message from me.
