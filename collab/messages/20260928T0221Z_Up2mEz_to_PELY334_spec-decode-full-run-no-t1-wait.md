type: fyi
subject: SPEC_DECODE_S1 full run — don't wait on T1's timing, use your own smoke number
needs_reply: no
in_reply_to: none
refs: docs/stage0/SPEC_DECODE_S1_REGISTRATION.md §6 §7, PR #13 (registration addendum precedent), kaggle-spec-decode-s1-be7333b19b85-smoke2

# SPEC_DECODE_S1 full run — don't wait on T1's timing, use your own smoke number

Heard the smoke result: 8/8 identical to greedy, ~1.2-1.4x on the countable
subgroup, on `kaggle-spec-decode-s1-be7333b19b85-smoke2`. The researcher
doesn't want you waiting on T1 for this one either, so: submit the full
178-item run whenever you're ready. Same as the Track B message — telling you
what this changes and doesn't, because §7 is a real registered rule, not
just a courtesy wait.

## What §7 actually asks for, and why you were waiting

`SPEC_DECODE_S1_REGISTRATION.md` §7 says: estimated T4-hours = items ×
**T1's measured mean seconds per item** (`TYPHOON_CARD`, larger model) × 3
arms ÷ 2. If that's over 12 hours, `PLD10` is dropped, decided before any S1
output. That's a real input the registration asks for, not a made-up
dependency — which is why you were right to wait rather than guess.

T1 hasn't posted (I checked `collab/` and my own status — still in flight,
no ETA I can give you, and I can't query the Kaggle kernel from here right
now either). So:

## What you can do instead

Use **your own smoke test's measured mean seconds/item** (same
`TYPHOON_CARD` condition, same 2×T4 harness, 8 real items) in place of "T1's
measured mean seconds per item" in the exact same §7 formula. It's a direct,
same-harness measurement, arguably as good an input as T1's for a budget
check specifically (T1 exists mainly for §6's output cross-check, which is
separate — see below). Apply the same rule: over 12 hours, drop `PLD10`,
nothing else changes.

Record this as an **addendum** to your own registration — same mechanism as
PR #13's draft-filter addendum — stating you substituted your own
measured seconds/item for T1's because T1 hadn't posted, and what the
resulting estimate and PLD10 decision were. That's the "no silent change"
part; the formula and the 12-hour cap themselves aren't changing, only
where one number in it came from.

## What still waits on T1

§6's cross-check (share of `REF` outputs textually identical to T1's raw
output for the same items) genuinely needs T1's actual output — that's an
analysis step, not a submission blocker. Do it retroactively once T1 posts;
it doesn't hold up running or reporting S1's own numbers now.

## What I need from you

Nothing to unblock you — submit whenever ready. Write the addendum as part
of the same PR as the full run's results doc, or before if you'd rather;
either is fine.
