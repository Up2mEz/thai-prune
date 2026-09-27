"""Asynchronous messages between the two researchers' AI sessions, stored as files.

Each message is its own file under `collab/messages/`, named so that two people
writing at the same moment can never produce the same path. Nothing is ever
edited after it is written: a message is answered by writing a reply that names
it in `in_reply_to`, so two sessions never touch the same file and messages
never cause merge conflicts. Protocol: `collab/README.md`.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

MESSAGE_DIR = Path("collab") / "messages"
TYPES = ("question", "answer", "proposal", "decision-request", "handoff", "result",
         "review-request", "fyi")
_FILENAME = re.compile(
    r"^(?P<stamp>\d{8}T\d{4}Z)_(?P<sender>[A-Za-z0-9-]+)_to_(?P<to>[A-Za-z0-9-]+|all)"
    r"_(?P<slug>[a-z0-9-]+)\.md$"
)
_FIELD = re.compile(r"^(?P<key>[a-z_]+):\s*(?P<value>.*)$")


@dataclass(frozen=True)
class Message:
    path: Path
    sender: str
    to: str
    type: str
    subject: str
    in_reply_to: str | None
    needs_reply: bool


def message_filename(sender: str, to: str, slug: str, now: dt.datetime | None = None) -> str:
    """`YYYYMMDDTHHMMZ_<sender>_to_<to>_<slug>.md`, in UTC."""
    moment = (now or dt.datetime.now(dt.UTC)).astimezone(dt.UTC)
    slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")[:60] or "message"
    name = f"{moment:%Y%m%dT%H%MZ}_{sender}_to_{to}_{slug}.md"
    if not _FILENAME.match(name):
        raise ValueError(f"invalid participant name in {name!r}; use GitHub usernames")
    return name


def parse(path: Path) -> Message:
    """Read the header block (`key: value` lines up to the first blank line)."""
    match = _FILENAME.match(path.name)
    if not match:
        raise ValueError(f"{path.name} does not follow the message naming rule")
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            break
        found = _FIELD.match(line.strip())
        if found:
            fields[found["key"]] = found["value"].strip()
    kind = fields.get("type", "")
    if kind not in TYPES:
        raise ValueError(f"{path.name}: type must be one of {TYPES}, got {kind!r}")
    reply = fields.get("in_reply_to") or None
    return Message(
        path=path, sender=match["sender"], to=match["to"], type=kind,
        subject=fields.get("subject", ""), in_reply_to=reply if reply != "none" else None,
        needs_reply=fields.get("needs_reply", "no").lower() == "yes",
    )


def load_all(root: Path) -> list[Message]:
    directory = root / MESSAGE_DIR
    if not directory.exists():
        return []
    return [parse(p) for p in sorted(directory.glob("*.md"))]


def open_for(root: Path, person: str) -> list[Message]:
    """Messages to `person` (or `all`) that ask for a reply and have none yet."""
    messages = load_all(root)
    answered = {m.in_reply_to for m in messages if m.in_reply_to}
    return [
        m for m in messages
        if m.to in (person, "all") and m.sender != person
        and m.needs_reply and m.path.name not in answered
    ]
