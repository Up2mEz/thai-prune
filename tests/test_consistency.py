from pathlib import Path

from labbs2026.consistency import SOURCE_FILES, inspect_source_of_truth


def _write_source_files(root: Path) -> None:
    contents = {
        "AGENTS.md": "Research rules",
        "docs/RESEARCH_SPEC.md": (
            "Stage 1A Resolution Sensitivity\n"
            "Resolution Reduction is not post-encoder Token Pruning\n"
            "The primary independent sampling/analysis unit is the linguistic minimal pair\n"
            "The primary RQ is non-directional\nPENDING_HUMAN_DECISION"
        ),
        "docs/EXPERIMENT_PROTOCOL.md": (
            "Stage 1A Resolution Sensitivity\n"
            "Stage 1A is not the main Stage 1 experiment\n"
            "never choose or relax a threshold using Stage 1A\n"
            "primary independent sampling/analysis unit is `pair_id`"
        ),
        "docs/ARCHITECTURE.md": (
            "Current sequential candidate strategy\n"
            "Backbone selection must not use observed effects\n"
            "Opening the secondary candidate requires a Decision Log entry\n"
            "does not make Stage 1A a post-encoder pruning experiment"
        ),
        "docs/DECISION_LOG.md": (
            "Stage 1A Resolution Sensitivity\n"
            "Stage 1A does not approve Gate 1\n"
            "Post-encoder Token Pruning and H3 remain `NOT TESTED`\n"
            "calibration estimates\nhuman researcher must freeze the criteria\n"
            "# Gate 4 — Unresolved gap after existing methods\n"
            "PASS → a meaningful unresolved failure remains"
        ),
        "docs/CLAIMS.md": (
            "Directionality:** not frozen\n"
            "`Tested` `Preliminary/Pilot` `Not Tested` `Blocked`"
        ),
    }
    for relative_path in SOURCE_FILES:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents[relative_path], encoding="utf-8")


def test_consistency_accepts_approved_invariants(tmp_path: Path) -> None:
    _write_source_files(tmp_path)

    result = inspect_source_of_truth(tmp_path)

    assert result.valid
    assert result.issues == ()


def test_consistency_rejects_missing_stage_1a_boundary(tmp_path: Path) -> None:
    _write_source_files(tmp_path)
    decision_log = tmp_path / "docs/DECISION_LOG.md"
    decision_log.write_text(
        decision_log.read_text(encoding="utf-8").replace(
            "Post-encoder Token Pruning and H3 remain `NOT TESTED`",
            "Compression is tested",
        ),
        encoding="utf-8",
    )

    result = inspect_source_of_truth(tmp_path)

    assert not result.valid
    assert "interventions-separated" in {issue.check_id for issue in result.issues}
