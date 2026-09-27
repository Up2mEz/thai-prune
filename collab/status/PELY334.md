# Status — PELY334

**Updated:** 2026-09-28

## Tracks I own

| track | package | state |
|---|---|---|
| Track A — speed without changing output (speculative decoding) | `src/labbs2026/spec_decode/` | approved (`collab/messages/20260927T1633Z_Up2mEz_to_PELY334_approve-track-a-defer-bcd.md`); plan `docs/exec-plans/active/SPEC_DECODE_PLAN.md`; `SPEC_DECODE_S1` registration `DRAFT_FOR_REVIEW`, merged in PR #7 |

Tracks C, B (evaluation) and D: on hold per Up2mEz until further message. Not
started.

## Running now

- Kaggle setup smoke (`docs/KAGGLE_SETUP.md` §5): kernel
  `pely334/labbs2026-thai-marks-t1-t2`, run id
  `kaggle-thai-marks-t1-49d963163ef1-smoke1`, commit `49d9631`, `--tests t1
  --limit 1`. Still `QUEUED` at 2026-09-28 00:04 local. Setup check only; not
  research evidence.

## Waiting on

- Up2mEz's review of `docs/stage0/SPEC_DECODE_S1_REGISTRATION.md`, including
  a yes/no on fixing `TYPHOON_CARD` as S1's prompt
  (`collab/messages/20260927T1647Z_PELY334_to_Up2mEz_review-spec-decode-s1-registration.md`).
- Then: Decision Log entry for S1 (humans approve). No S1 inference before it.
- Smoke to reach `COMPLETE`.

## Do not touch without asking

- `src/labbs2026/spec_decode/`, `configs/spec_decode/`,
  `docs/stage0/SPEC_DECODE_*` — Track A, registration under review.
