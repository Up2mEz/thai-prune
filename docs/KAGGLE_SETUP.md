# Kaggle setup — for a new collaborator's Claude Code session

**Audience note.** This file is written to be executed directly by an AI coding
agent (Claude Code or similar) working in this repository on the new
collaborator's machine, not primarily as prose for a human to read and
type manually. Each step names the exact command or file to produce. If you
are that agent: run the commands in order, stop and surface the exact error to
the human if any step fails, and do not skip the verification step at the end.

## 0. Preconditions

- This repository is cloned locally and `main` is checked out
  (`git checkout main && git pull`).
- `uv` is installed (`uv --version`; if missing, follow
  https://docs.astral.sh/uv/getting-started/installation/).
- The human collaborator has their **own** Kaggle account, separate from any
  other project member's. If they don't have one yet, they create one at
  https://www.kaggle.com — this must be done by the human in a browser, not by
  the agent, because it requires accepting Kaggle's own terms and (for GPU
  access) phone verification.

## 1. Install project dependencies

```bash
uv sync --all-extras
```

Verify: `uv run pytest -q` should report failures only in
`tests/test_glmm_failure_contract.py` (these are pre-existing, Docker-dependent,
and unrelated to anything Kaggle) — every other test passes. If a different
test fails, stop and report it before continuing; do not proceed to submit
anything to Kaggle on top of a broken checkout.

## 2. Get a Kaggle API token

This step is done by the human in a browser, because it requires being logged
into their own Kaggle account:

1. Go to https://www.kaggle.com/settings/account
2. Under "API", click "Create New Token". This downloads a file named
   `kaggle.json` containing `{"username": "...", "key": "..."}`.

The agent then places it where the `kaggle` CLI and this project's scripts
expect it:

- **Windows:** `%USERPROFILE%\.kaggle\kaggle.json`
- **macOS/Linux:** `~/.kaggle/kaggle.json`

```bash
mkdir -p ~/.kaggle
mv <path-to-downloaded-file>/kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json   # macOS/Linux only; skip on Windows
```

**Verify** the token is valid and read the username out of it (the agent needs
this value for step 3):

```bash
uv run kaggle kernels list --mine
```

This must print a table (even if empty) rather than an authentication error.
If it errors, the most common cause is that `kaggle.json` was placed in the
wrong directory, or its `key` was copy-pasted with extra whitespace.

## 3. Enable GPU quota on the Kaggle account

GPU kernels require phone verification on the account, done by the human in
the browser:

1. https://www.kaggle.com/settings/account → "Phone Verification" → verify.
2. Confirm quota is available: https://www.kaggle.com/code shows a GPU quota
   meter (30 hours/week per account) once verified.

Nothing for the agent to do here except wait for the human to confirm this is
done before step 5, since a kernel push will queue indefinitely without error
on an unverified account.

## 4. Create the per-person local config

This repo intentionally does not hardcode any one person's Kaggle username or
git branch in tracked files — see `docs/COLLABORATION.md` §6 for why. The
agent creates this file (it is git-ignored; never commit it):

```bash
cp configs/kaggle_local.example.yaml configs/kaggle_local.yaml
```

Then edit `configs/kaggle_local.yaml` and set `kaggle_username` to the exact
value of `"username"` from the `kaggle.json` obtained in step 2 (not a display
name — the API username). Leave `remote_ref` commented out; it should default
to whatever branch is checked out.

**Verify:**

```bash
uv run python -c "
from pathlib import Path
from labbs2026.kaggle import load_local_config, kernel_id, local_remote_ref
root = Path('.').resolve()
print(load_local_config(root))
print(kernel_id(root, 'labbs2026-example'))
print(local_remote_ref(root))
"
```

This must print the username set in step 4, a kernel id prefixed with that
username, and the currently checked-out branch (e.g. `refs/heads/main` if run
right after cloning — this is fine at this stage; it will reflect whatever
feature branch is checked out once real work begins).

## 5. First real submission — confirm the whole path end to end

Before starting any new experiment track, run an existing track's smallest
possible smoke to confirm push → queue → run → fetch works on this account.
The Thai-marks track supports a 1-item smoke:

```bash
uv run python scripts/thai_marks_kaggle.py --tests t1 --limit 1 --submit
```

This will refuse to run (by design — see `docs/COLLABORATION.md` and
`AGENTS.md`) if there are uncommitted tracked changes, or if the checked-out
branch has not been pushed to `origin` at the exact commit HEAD is at. If it
refuses for either reason, commit and push first, then retry.

**Watch it complete** rather than assuming success — Kaggle GPU kernels can sit
`QUEUED` for tens of minutes depending on platform load, and a session
mid-queue can outlive a branch push race (this project hit exactly that bug
once; it is fixed by fetching the exact commit SHA rather than a branch tip,
so it will not recur, but the queue wait itself is real and can be long):

```bash
KERNEL="$(uv run python -c "
from pathlib import Path
from labbs2026.kaggle import kernel_id
print(kernel_id(Path('.').resolve(), 'labbs2026-thai-marks-t1-t2'))
")"
uv run kaggle kernels status "$KERNEL"
```

Poll this every couple of minutes until it reads `COMPLETE` (or `ERROR` — if
so, fetch the log and report it rather than retrying blindly):

```bash
uv run kaggle kernels output "$KERNEL" -p /tmp/kaggle-smoke-check
cat /tmp/kaggle-smoke-check/*.log
```

A `COMPLETE` status with a `SUCCESS.json` in the fetched artifacts confirms
the whole chain — token, quota, branch, and the project's own worker script —
works on this account. Only after this succeeds should the collaborator start
their own experiment track (see `docs/COLLABORATION.md` §4 for how to name and
scope a new track without colliding with existing ones).

## Troubleshooting reference

| Symptom | Cause | Fix |
|---|---|---|
| `kaggle kernels list --mine` errors with 401/403 | `kaggle.json` missing or malformed | Redo step 2 |
| Kernel stays `QUEUED` for over ~1 hour | Kaggle platform GPU queue load, or account not phone-verified | Check step 3; otherwise this is normal — Kaggle's own queue, not a bug in this project |
| `RuntimeError: ... configs/kaggle_local.yaml not found` | Step 4 skipped | Redo step 4 |
| `RuntimeError: tracked files have uncommitted changes` | Working tree dirty | `git status`; commit or stash before submitting |
| `remote ref ... is not at HEAD; push first` | Local commits not pushed, or pushed after the branch moved | `git push`, then retry; this check exists specifically because a stale branch tip once caused a checkout failure mid-queue |
