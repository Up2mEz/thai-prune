"""Every repository path ONBOARDING.md tells a new session to read must exist.

A collaborator's AI follows these paths literally; a renamed or moved file
would send it looking for something that is not there, so the guide is kept
honest by test rather than by memory.
"""

from __future__ import annotations

import re
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP_LEVEL = ("docs/", "src/", "scripts/", "configs/", "infra/", "collab/", "tests/")
ROOT_FILES = ("AGENTS.md", "ONBOARDING.md")
# Files the guides tell each person to create locally; git-ignored by design,
# so they must be absent from the repository.
USER_CREATED = frozenset({"configs/kaggle_local.yaml"})


@lru_cache(maxsize=1)
def _in_repository() -> frozenset[str]:
    """Tracked files and every directory containing one.

    Checked against git rather than the working tree: a file that exists only
    on one person's disk would pass on their machine and mislead the other's AI.
    """
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True,
                           capture_output=True, text=True).stdout.split()
    present = set(files)
    for name in files:
        parts = name.split("/")
        for depth in range(1, len(parts)):
            present.add("/".join(parts[:depth]))
    return frozenset(present)


def _missing(paths: set[str]) -> list[str]:
    return sorted(p for p in paths if p not in USER_CREATED and p not in _in_repository())


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
    missing = _missing(_paths(text))
    assert not missing, f"ONBOARDING.md points at paths not in the repository: {missing}"


def test_collaboration_docs_paths_exist() -> None:
    for name in ("docs/COLLABORATION.md", "collab/README.md", "docs/KAGGLE_SETUP.md",
                 "docs/exec-plans/active/INDEX.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        missing = _missing(_paths(text))
        assert not missing, f"{name} points at paths not in the repository: {missing}"


def test_user_created_files_are_not_committed() -> None:
    assert not (USER_CREATED & _in_repository())
