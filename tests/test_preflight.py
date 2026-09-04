from pathlib import Path
from unittest.mock import patch

from labbs2026.preflight import REQUIRED_PATHS, inspect_repository


class _Result:
    def __init__(self, stdout: str, returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode


def test_preflight_reports_missing_paths(tmp_path: Path) -> None:
    with patch("labbs2026.preflight._run_git", side_effect=[_Result("abc123\n"), _Result("")]):
        result = inspect_repository(tmp_path)

    assert result.git_commit == "abc123"
    assert result.git_clean
    assert result.missing_paths == REQUIRED_PATHS
    assert not result.valid


def test_preflight_accepts_complete_clean_repository(tmp_path: Path) -> None:
    for relative_path in REQUIRED_PATHS:
        path = tmp_path / relative_path
        if relative_path.endswith("active"):
            path.mkdir(parents=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    with patch("labbs2026.preflight._run_git", side_effect=[_Result("abc123\n"), _Result("")]):
        result = inspect_repository(tmp_path)

    assert result.valid

