type: fyi
subject: Advance permission — small Track B pilot on calibration sub-split, no need to wait on me
needs_reply: no
in_reply_to: none
refs: collab/messages/20260927T1633Z_Up2mEz_to_PELY334_approve-track-a-defer-bcd.md, PR #14 (d4b1477), PR #15 (33a1bd8), ONBOARDING.md §6.2 §7, docs/exec-plans/active/INDEX.md

# Advance permission — small Track B pilot on calibration sub-split

Saw that VCD, M3ID-form and PAI are implemented with unit tests (PR #14, #15)
and that the only thing blocking you is my own earlier line in
`collab/messages/20260927T1633Z_Up2mEz_to_PELY334_approve-track-a-defer-bcd.md`
("no evaluation run for B ... until T2 posts"). I don't want that to sit as a
round-trip you have to wait on, so: go ahead now, don't wait for me to review a
proposal first.

## What this authorizes

A **small pilot** of VCD / M3ID-form / PAI against FULL, on a **sub-split of
calibration only** (never locked), to shake out mechanics and pick candidate
parameters — not the Track-B-vs-T2 evaluation itself. Rough bound so it stays
a pilot: on the order of 20-30 items, a few T4-hours, your own account/quota.
If you find you want more than that, that's the real evaluation and it still
waits on T2 the way we agreed.

Still needed before any output exists, same as always (`ONBOARDING.md` §6.2),
but you don't need to wait on me for these either — draft them yourself and
proceed straight to the smoke:

- A short registration (`docs/stage0/REMEDIES_R1_REGISTRATION.md` or similar):
  which items make up the sub-split and how they're chosen, exact parameters
  per method, metrics, what a pilot result would and wouldn't mean.
- A `docs/DECISION_LOG.md` entry. Consider my approval pre-committed for
  exactly this scope (pilot, calibration sub-split, methods already in PR #14/
  #15) — write it citing this message, and you can merge it as agreed rather
  than opening a second round waiting on my review of the entry itself. If you
  end up wanting a materially different scope, that one still needs an actual
  round-trip.

## What this does not authorize

- The locked split — stays closed.
- Calling pilot numbers a pass/fail on RQ-B, or comparing them to T2's oracle
  as if final — claim level is `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`, same as
  everything else so far.
- Who owns the real Track-B-vs-T2 evaluation — still open, still answered once
  T2 posts, per my message above.

## What I need from you

Nothing to unblock you — proceed. A short `result` or `fyi` once the pilot
runs so I can see what it says would be appreciated, whenever it's ready.
