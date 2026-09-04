"""Repository-level checks required before producing research evidence."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


REQUIRED_PATHS = (
    "AGENTS.md",
    "docs/RESEARCH_SPEC.md",
    "docs/EXPERIMENT_PROTOCOL.md",
    "docs/ARCHITECTURE.md",
    "docs/DECISION_LOG.md",
    "docs/CLAIMS.md",
    "docs/exec-plans/active",
    "pyproject.toml",
    "uv.lock",
)


@dataclass(frozen=True)
class PreflightResult:
    git_commit: str | None
    git_clean: bool
    missing_paths: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return self.git_commit is not None and self.git_clean and not self.missing_paths


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )


def inspect_repository(root: Path) -> PreflightResult:
    """Inspect Source-of-Truth paths and Git state without changing either."""

    missing = tuple(path for path in REQUIRED_PATHS if not (root / path).exists())
    commit_result = _run_git(root, "rev-parse", "HEAD")
    status_result = _run_git(root, "status", "--porcelain")
    commit = commit_result.stdout.strip() if commit_result.returncode == 0 else None
    clean = status_result.returncode == 0 and not status_result.stdout.strip()
    return PreflightResult(commit, clean, missing)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    result = inspect_repository(root)
    print(json.dumps(asdict(result) | {"valid": result.valid}, indent=2))
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

