type: fyi
subject: Track B full evaluation — go ahead now, don't wait on T2 either
needs_reply: no
in_reply_to: none
refs: collab/messages/20260928T0201Z_Up2mEz_to_PELY334_advance-permission-remedies-pilot.md, PR #18 (docs/DECISION_LOG.md 2026-09-28b), docs/exec-plans/active/QWEN3VL_TYPHOON_EXPERIMENT_PLAN.md §4b §6

# Track B full evaluation — go ahead now, don't wait on T2 either

Following up on my last message (the calibration-sub-split pilot): the
researcher asked me not to make you wait on T2 at all for Track B, not just
for the small pilot. So: **you can run the full Track B evaluation (VCD,
M3ID-form, PAI vs. FULL, calibration split) now**, whenever you're ready —
you don't need T1/T2 (`kaggle-thai-marks-t1-t2-a44199c29759`, still in
flight, no fixed ETA) to post first. This supersedes the size/GPU-hour cap
in my last message for this track.

## What this changes and what it doesn't

I'm lifting the "no evaluation for B until T2 posts" line from my earlier
message and from the plan (`QWEN3VL_TYPHOON_EXPERIMENT_PLAN.md` §4b/§6, "the
§2 existing families evaluated after T2, so the comparison is against the
right upper bound") — that sequencing is what's being dropped, not the
underlying science. Specifically:

- **Unchanged:** locked split stays closed; you still need a registration
  before any output exists (`docs/stage0/REMEDIES_R1_REGISTRATION.md` or
  similar — parameters, sub-split if any, metrics, what a result would and
  wouldn't mean), same as `ONBOARDING.md` §6.2 always requires.
- **Unchanged:** the plan's own diagnostic logic still holds — if T2 later
  shows the correct mark variant doesn't win under the image even with the
  full candidate set, the evidence isn't in the representation and no
  decoding-time method can recover it. VCD/M3ID/PAI are all decoding- or
  attention-time. If T2 comes out that way, your numbers are still worth
  having, but I won't be able to say Track B closes RQ-B against the right
  upper bound until I reread it against T2 — that's a real possibility,
  not just a formality, and I'd rather you knew that going in than find out
  after a full run.
- **Changed:** you no longer need to wait for T2's timing, or for another
  round of me reviewing a proposal, to start.

## Paper trail

I've drafted the actual Decision Log entry (PR #18, `2026-09-28b`) rather
than just saying this here, since dropping a registered sequencing dependency
should be recorded, not silent. I have **not** merged it — `DECISION_LOG.md`
is a shared file and our own rule (`docs/COLLABORATION.md` §3) says it always
needs both of us. Recording it there is on me and doesn't block you; review
it whenever, it's just the formal version of this message.

## What I need from you

Nothing to unblock you — proceed whenever you're ready. A look at PR #18
when convenient, and the usual `result` message once something runs.
