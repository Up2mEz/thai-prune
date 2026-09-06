"""Machine-checkable invariants for the research Source of Truth."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


SOURCE_FILES = (
    "AGENTS.md",
    "docs/RESEARCH_SPEC.md",
    "docs/EXPERIMENT_PROTOCOL.md",
    "docs/ARCHITECTURE.md",
    "docs/DECISION_LOG.md",
    "docs/CLAIMS.md",
    "docs/exec-plans/active/ADVISOR_READINESS.md",
)


@dataclass(frozen=True)
class ConsistencyIssue:
    check_id: str
    detail: str


@dataclass(frozen=True)
class ConsistencyResult:
    checked_files: tuple[str, ...]
    issues: tuple[ConsistencyIssue, ...]

    @property
    def valid(self) -> bool:
        return not self.issues


def _require(
    issues: list[ConsistencyIssue],
    check_id: str,
    condition: bool,
    detail: str,
) -> None:
    if not condition:
        issues.append(ConsistencyIssue(check_id=check_id, detail=detail))


def inspect_source_of_truth(root: Path) -> ConsistencyResult:
    """Check approved methodological invariants without modifying documents."""

    issues: list[ConsistencyIssue] = []
    texts: dict[str, str] = {}

    for relative_path in SOURCE_FILES:
        path = root / relative_path
        if not path.is_file():
            issues.append(
                ConsistencyIssue(
                    check_id="required-source-file",
                    detail=f"Missing required Source-of-Truth file: {relative_path}",
                )
            )
            continue
        texts[relative_path] = path.read_text(encoding="utf-8")

    if len(texts) != len(SOURCE_FILES):
        return ConsistencyResult(SOURCE_FILES, tuple(issues))

    research = texts["docs/RESEARCH_SPEC.md"]
    protocol = texts["docs/EXPERIMENT_PROTOCOL.md"]
    architecture = texts["docs/ARCHITECTURE.md"]
    decisions = texts["docs/DECISION_LOG.md"]
    claims = texts["docs/CLAIMS.md"]
    active_plan = texts["docs/exec-plans/active/ADVISOR_READINESS.md"]
    normalized_decisions = " ".join(decisions.split())
    combined = "\n".join(texts.values())

    for relative_path, text in (
        ("docs/RESEARCH_SPEC.md", research),
        ("docs/EXPERIMENT_PROTOCOL.md", protocol),
        ("docs/DECISION_LOG.md", decisions),
    ):
        _require(
            issues,
            "stage-1a-declared",
            "Stage 1A" in text and "Resolution Sensitivity" in text,
            f"{relative_path} must declare Stage 1A Resolution Sensitivity.",
        )

    _require(
        issues,
        "stage-1a-is-pilot",
        "Stage 1A is not the main Stage 1 experiment" in protocol
        and "Stage 1A does not approve Gate 1" in decisions,
        "Stage 1A must remain a pilot and must not approve Gate 1.",
    )
    _require(
        issues,
        "interventions-separated",
        "Resolution Reduction is not post-encoder Token Pruning" in research
        and "does not make Stage 1A a post-encoder pruning experiment" in architecture
        and "Post-encoder Token Pruning and H3 remain `NOT TESTED`" in decisions,
        "Resolution Reduction evidence must stay separate from post-encoder pruning.",
    )
    _require(
        issues,
        "gate-0-calibration-derived",
        "calibration estimates" in decisions
        and "human researcher must freeze the criteria" in decisions
        and "never choose or relax a threshold using Stage 1A" in protocol,
        "Gate 0 criteria must be calibration-derived and frozen before validation.",
    )
    _require(
        issues,
        "pair-is-independent-unit",
        "primary independent sampling/analysis unit is `pair_id`" in protocol
        and "primary independent sampling/analysis unit is the linguistic minimal" in research,
        "The independent unit must be pair_id; renders are repeated observations.",
    )
    _require(
        issues,
        "sequential-backbone",
        "Current sequential candidate strategy" in architecture
        and "Backbone selection must not use" in architecture
        and "Opening the secondary candidate requires a Decision Log entry" in architecture,
        "Backbone feasibility must remain sequential and effect-independent.",
    )
    _require(
        issues,
        "gate-4-pass-defined",
        "# Gate 4 — Unresolved gap after existing methods" in decisions
        and "PASS → a meaningful unresolved failure remains" in decisions,
        "Gate 4 PASS must unambiguously mean that an unresolved failure remains.",
    )
    _require(
        issues,
        "advisor-status-vocabulary",
        all(status in claims for status in ("`Tested`", "`Preliminary/Pilot`", "`Not Tested`", "`Blocked`")),
        "Advisor evidence-status vocabulary is incomplete.",
    )
    _require(
        issues,
        "h1-frozen-nondirectional",
        "The primary RQ is non-directional" in research
        and "frozen non-directional" in research
        and "Directionality:** frozen as non-directional" in claims,
        "H1 must remain frozen as a non-directional interaction.",
    )
    _require(
        issues,
        "step-3-complete",
        "Step 3 is `COMPLETE`" in architecture
        and "**Decision:** Step 3 = `COMPLETE`." in decisions
        and "Step 3 — Sequential backbone feasibility | `COMPLETE`" in active_plan,
        "Step 3 completion must agree across architecture, decisions, and active plan.",
    )
    _require(
        issues,
        "kaggle-backend-proposed",
        all(
            "`KAGGLE_BACKEND_FEASIBLE_PROPOSED`" in text
            for text in (architecture, decisions, claims)
        ),
        "The Kaggle backend proposal status must agree across the Source of Truth.",
    )
    _require(
        issues,
        "kaggle-stage0-approved",
        all("`FROZEN_CALIBRATION`" in text for text in (architecture, decisions, claims))
        and (
            "Steps 4–6 — Stage 0 | `FROZEN_CALIBRATION`" in active_plan
            or "Steps 4–6 — Stage 0 | `CALIBRATION_INSTRUMENT_INVALID_PENDING_HUMAN_REVIEW`"
            in active_plan
        ),
        "The frozen Stage 0 calibration status must agree across the Source of Truth.",
    )
    _require(
        issues,
        "stage0-labels-and-controls",
        all(
            label in research and label in protocol and label in decisions
            for label in (
                "UPPER_VOWEL_VARIANT",
                "LOWER_VOWEL_VARIANT",
                "STACKED_TONE_MARK",
            )
        )
        and "LANGUAGE_CANDIDATE_BIAS_BLANK" in protocol
        and "without visual ground truth" in normalized_decisions,
        "Stage 0 component labels and blank-control semantics must agree.",
    )
    _require(
        issues,
        "later-stages-remain-gated",
        "# Gate 0 — Measurement validity\n\n**Status:** NOT_RUN" in decisions
        and (
            "Steps 4–6 — Stage 0 | `FROZEN_CALIBRATION`" in active_plan
            or "Steps 4–6 — Stage 0 | `CALIBRATION_INSTRUMENT_INVALID_PENDING_HUMAN_REVIEW`"
            in active_plan
        )
        and "Locked Stage 0 validation may not begin" in decisions
        and "# Stage 1A — Resolution Sensitivity Pilot\n\n**Status:** BLOCKED" in decisions,
        "Stage 0 preparation must not authorize locked validation or Stage 1A.",
    )

    forbidden_defaults = ("accuracy ≥0.75", "parser failure ≤1%", "A/B gap ≤10pp")
    _require(
        issues,
        "no-unjustified-gate-0-defaults",
        not any(value in combined for value in forbidden_defaults),
        "An unapproved numeric Gate 0 default reappeared in the Source of Truth.",
    )

    return ConsistencyResult(SOURCE_FILES, tuple(issues))


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    result = inspect_source_of_truth(root)
    payload = {
        "checked_files": result.checked_files,
        "issues": [asdict(issue) for issue in result.issues],
        "valid": result.valid,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
