"""Fetch a completed region-OCR run, verify its artifacts, and build the report.

Verification runs before analysis, not after: a run whose checksums do not
reconcile is not analysed at all rather than analysed with a warning attached.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any

from labbs2026.region_ocr.report import build_report


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(kernel_id: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["kaggle", "kernels", "output", kernel_id, "-p", str(destination)],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[-2000:])


def verify(artifact_dir: Path) -> dict[str, Any]:
    """Reconcile every file against the run's own checksum manifest."""
    checksums = artifact_dir / "checksums.sha256"
    if not checksums.exists():
        raise RuntimeError(f"no checksums.sha256 under {artifact_dir}")
    success = artifact_dir / "SUCCESS.json"
    if not success.exists():
        failure = artifact_dir / "FAILURE.json"
        detail = failure.read_text("utf-8")[:800] if failure.exists() else "no FAILURE.json"
        raise RuntimeError(f"run did not succeed: {detail}")

    declared = json.loads(success.read_text("utf-8"))
    if declared.get("checksums_sha256") != _sha256(checksums):
        raise RuntimeError("checksums.sha256 does not match the hash declared in SUCCESS.json")

    mismatched: list[str] = []
    checked = 0
    for line in checksums.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        target = artifact_dir / relative
        if not target.exists() or _sha256(target) != expected:
            mismatched.append(relative)
        checked += 1
    if mismatched:
        raise RuntimeError(f"{len(mismatched)} artifact(s) failed verification: {mismatched[:5]}")
    return {"files_verified": checked, "success": declared}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel-id", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--budgets", default="75,50,25")
    parser.add_argument("--resamples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260920)
    parser.add_argument("--skip-fetch", action="store_true")
    args = parser.parse_args()

    if not args.skip_fetch:
        fetch(args.kernel_id, args.destination)

    candidates = sorted(args.destination.rglob("checksums.sha256"))
    if not candidates:
        raise RuntimeError(f"no run artifacts found under {args.destination}")
    artifact_dir = candidates[0].parent
    verification = verify(artifact_dir)

    observations = [
        json.loads(line)
        for line in io.open(artifact_dir / "observations.jsonl", encoding="utf-8")
        if line.strip()
    ]
    manifest = json.loads((artifact_dir / "run_manifest.json").read_text("utf-8"))
    report = build_report(
        observations,
        budgets=tuple(args.budgets.split(",")),
        resamples=args.resamples,
        seed=args.seed,
        execution_failures=int(manifest.get("execution_failures", 0)),
    )
    report["verification"] = verification
    report["run_manifest"] = {
        k: manifest[k] for k in manifest
        if k in ("run_id", "git_sha", "cuda_device", "wall_seconds",
                 "peak_cuda_allocated_bytes", "completed_observations", "workload")
    }
    out = artifact_dir / "registered_report.json"
    with io.open(out, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)

    print(f"verified {verification['files_verified']} files")
    print(f"observations {report['observations']}  failures {report['execution_failures']}")
    for name in ("primary", "secondary"):
        section = report[name]
        print(f"-- {name}: {section['regions']} regions / {section['clusters']} clusters")
        for budget, did in section["did"].items():
            extra = f" p_holm={did['p_holm']:.4f}" if "p_holm" in did else ""
            print(f"   DiD_{budget}: {did['estimate']:+.4f} "
                  f"[{did['ci_low']:+.4f}, {did['ci_high']:+.4f}]{extra}")
    print(f"report written to {out}")


if __name__ == "__main__":
    main()
