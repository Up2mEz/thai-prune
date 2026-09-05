"""Thin CLI for the Stage 0 candidate inventory and rendering review packet."""

from __future__ import annotations

import argparse
from pathlib import Path

from labbs2026.stage0.dataset import build_candidate_review


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path("configs/stage0/candidate_pairs.yaml"),
    )
    parser.add_argument(
        "--rendering",
        type=Path,
        default=Path("configs/stage0/rendering_candidates.yaml"),
    )
    parser.add_argument(
        "--calibration-design",
        type=Path,
        default=Path("configs/stage0/calibration_design.yaml"),
    )
    args = parser.parse_args()
    run_dir, report = build_candidate_review(
        args.inventory.resolve(),
        args.rendering.resolve(),
        args.calibration_design.resolve(),
    )
    print(f"run_dir={run_dir}")
    print(f"status={report['status']}")
    print(f"candidate_pair_count={report['candidate_pair_count']}")
    print(f"automated_issue_count={len(report['automated_issues'])}")
    return 0 if not report["automated_issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
