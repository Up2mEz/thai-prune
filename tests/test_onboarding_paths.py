"""Every repository path ONBOARDING.md tells a new session to read must exist.

A collaborator's AI follows these paths literally; a renamed or moved file
would send it looking for something that is not there, so the guide is kept
honest by test rather than by memory.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP_LEVEL = ("docs/", "src/", "scripts/", "configs/", "infra/", "collab/", "tests/")
ROOT_FILES = ("AGENTS.md", "ONBOARDING.md")


def _paths(text: str) -> set[str]:
    found = set()
    for token in re.findall(r"`([^`\s]+)`", text):
        if "<" in token or "*" in token:
            continue
        if token.startswith(TOP_LEVEL) or token in ROOT_FILES:
            found.add(token.rstrip("/"))
    return found


def test_onboarding_paths_exist() -> None:
    text = (ROOT / "ONBOARDING.md").read_text(encoding="utf-8")
    missing = sorted(p for p in _paths(text) if not (ROOT / p).exists())
    assert not missing, f"ONBOARDING.md points at paths that do not exist: {missing}"


def test_collaboration_docs_paths_exist() -> None:
    for name in ("docs/COLLABORATION.md", "collab/README.md", "docs/KAGGLE_SETUP.md",
                 "docs/exec-plans/active/INDEX.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        missing = sorted(p for p in _paths(text) if not (ROOT / p).exists())
        assert not missing, f"{name} points at paths that do not exist: {missing}"
