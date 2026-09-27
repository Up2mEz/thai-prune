# collab/ — how the two AI sessions talk to each other

This project has two researchers, each working with their own Claude Code
session. Neither session can see the other's conversation. This folder is the
only channel between them, and every message is a file in git — versioned,
reviewable, and readable by either AI without any extra tooling.

Participants are identified by **GitHub username**. The owner is `Up2mEz`.

## Layout

```
collab/
├── README.md                 ← this protocol
├── templates/message.md      ← copy this to write a message
├── status/<github-user>.md   ← each person's live status; only its owner edits it
└── messages/                 ← one file per message, never edited after writing
```

## Rules

1. **One message, one file.** Name it
   `YYYYMMDDTHHMMZ_<from>_to_<to>_<slug>.md` (UTC). Get a correct name with
   `uv run python scripts/collab_inbox.py --new --me <you> --to <them> --slug "<subject>"`.
   `<to>` may be `all`.
2. **Never edit a message after it is merged** — not yours, not theirs. Answer
   by writing a new message with `in_reply_to: <the original filename>`. This is
   why messages can never conflict.
3. **Only edit your own status file.** Update `collab/status/<you>.md` at the
   end of every working session.
4. **Header block first**, then a blank line, then free Markdown. The header
   fields are parsed by `src/labbs2026/collab.py`; `tests/test_collab.py`
   rejects any committed message that does not parse.
5. **Delivery is a PR.** A PR that only adds files under `collab/messages/`
   or changes only your own `collab/status/` file may be merged by its author
   as soon as the `light-checks` workflow passes — it does not wait for review.
   That workflow runs `tests/test_collab.py`, which rejects malformed messages. Anything else in
   the same PR follows `docs/COLLABORATION.md` §3 as usual.

## At the start of every session, the AI does this

```bash
git checkout main && git pull
uv run python scripts/collab_inbox.py --me <your-github-username>
```

Then reads each listed message, reads the other person's
`collab/status/<them>.md`, and tells its human what is waiting before starting
new work.

## Message types

| type | use it for | needs_reply |
|---|---|---|
| `question` | something you cannot decide or find out alone | yes |
| `answer` | reply to a question | no |
| `proposal` | "I intend to do X" — e.g. claiming a track, before starting it | yes |
| `decision-request` | a choice the *humans* must make together (licence, scope, Decision Log entry) | yes |
| `handoff` | "this is ready for you to build on" — with paths and commit SHA | usually no |
| `result` | an experiment finished — run id, where artifacts are, headline numbers, claim level | no |
| `review-request` | "please review PR #N" | yes |
| `fyi` | anything else worth knowing | no |

## What a good message contains

- Exact paths, commit SHAs, PR numbers, Kaggle run ids — never "the file I
  changed" or "the latest run".
- What you need from the other side, in one sentence, if anything.
- For `result`: the claim level (`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE` etc.)
  so no number travels without its caveat.
