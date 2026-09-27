"""The collab message protocol: naming, parsing, and what counts as waiting."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from labbs2026.collab import MESSAGE_DIR, message_filename, open_for, parse

NOON = dt.datetime(2026, 9, 27, 12, 0, tzinfo=dt.UTC)


def _write(root: Path, name: str, **fields: str) -> Path:
    directory = root / MESSAGE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    header = "\n".join(f"{k}: {v}" for k, v in fields.items())
    path = directory / name
    path.write_text(header + "\n\n# body\n\ntext\n", encoding="utf-8")
    return path


def test_filename_is_utc_stamped_and_slugged() -> None:
    name = message_filename("Up2mEz", "friend-gh", "T2 Results: oracle!", NOON)
    assert name == "20260927T1200Z_Up2mEz_to_friend-gh_t2-results-oracle.md"


def test_filename_rejects_names_that_break_the_pattern() -> None:
    with pytest.raises(ValueError):
        message_filename("bad name", "friend", "x", NOON)


def test_parse_reads_the_header_block(tmp_path: Path) -> None:
    path = _write(tmp_path, "20260927T1200Z_a_to_b_hello.md",
                  type="question", subject="Hi", needs_reply="yes", in_reply_to="none")
    message = parse(path)
    assert (message.sender, message.to, message.type) == ("a", "b", "question")
    assert message.needs_reply and message.in_reply_to is None


def test_parse_rejects_an_unknown_type(tmp_path: Path) -> None:
    path = _write(tmp_path, "20260927T1200Z_a_to_b_x.md", type="gossip")
    with pytest.raises(ValueError, match="type must be one of"):
        parse(path)


def test_a_question_stays_open_until_a_reply_names_it(tmp_path: Path) -> None:
    q = _write(tmp_path, "20260927T1200Z_a_to_b_q.md",
               type="question", subject="?", needs_reply="yes", in_reply_to="none")
    assert [m.path for m in open_for(tmp_path, "b")] == [q]
    assert open_for(tmp_path, "a") == []  # own messages are never in your inbox
    _write(tmp_path, "20260927T1300Z_b_to_a_re-q.md",
           type="answer", subject="!", needs_reply="no", in_reply_to=q.name)
    assert open_for(tmp_path, "b") == []


def test_messages_to_all_reach_everyone_else(tmp_path: Path) -> None:
    _write(tmp_path, "20260927T1200Z_a_to_all_status.md",
           type="fyi", subject="s", needs_reply="yes", in_reply_to="none")
    assert len(open_for(tmp_path, "b")) == 1
    assert open_for(tmp_path, "a") == []


def test_fyi_without_needs_reply_is_not_waiting(tmp_path: Path) -> None:
    _write(tmp_path, "20260927T1200Z_a_to_b_note.md",
           type="fyi", subject="s", needs_reply="no", in_reply_to="none")
    assert open_for(tmp_path, "b") == []


def test_repository_messages_all_parse() -> None:
    """Every message committed to the repo must follow the protocol."""
    root = Path(__file__).resolve().parents[1]
    for path in sorted((root / MESSAGE_DIR).glob("*.md")):
        parse(path)
