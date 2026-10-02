"""Fetch a T1/T2 run, verify its checksums, and write the registered summaries."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path

from labbs2026.thai_marks.analysis import score_t1_record, summarize_t1, summarize_t2

KERNEL_ID = "thanakritsamoena/labbs2026-thai-marks-t1-t2"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--kernel-id", default=KERNEL_ID,
                        help="owner/slug of the kernel to fetch (a parallel session's own slug)")
    args = parser.parse_args()

    if not args.skip_fetch:
        args.destination.mkdir(parents=True, exist_ok=True)
        subprocess.run(["kaggle", "kernels", "output", args.kernel_id, "-p", str(args.destination)],
                       check=True, capture_output=True)
    root = next(args.destination.rglob(args.run_id), None)
    if root is None or not root.is_dir():
        raise SystemExit(f"run directory {args.run_id} not found under {args.destination}")
    if (root / "FAILURE.json").exists():
        raise SystemExit("run failed: " + (root / "FAILURE.json").read_text(encoding="utf-8"))

    for line in (root / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if _sha256(root / relative) != digest:
            raise SystemExit(f"checksum mismatch: {relative}")

    report: dict = {"run_id": args.run_id, "status": "PRELIMINARY_PILOT_NOT_GATE_EVIDENCE"}
    greedy: dict[str, dict[str, str]] = {}
    for role in ("base", "typhoon"):
        t1 = _records(root / "t1" / role / "records.jsonl")
        if t1:
            report.setdefault("t1", {})[role] = {}
            for prompt in sorted({r["prompt_kind"] for r in t1}):
                rows = [r for r in t1 if r["prompt_kind"] == prompt]
                report["t1"][role][prompt] = summarize_t1([score_t1_record(r) for r in rows])
            greedy[role] = {r["id"]: r["raw_output"] for r in t1
                            if r["prompt_kind"] == "TYPHOON_CARD"}
            report["t1"][role]["manifest"] = json.loads(
                (root / "t1" / role / "manifest.json").read_text(encoding="utf-8"))
        t2 = _records(root / "t2" / role / "records.jsonl")
        if t2:
            report.setdefault("t2", {})[role] = summarize_t2(t2, greedy.get(role))
            report["t2"][role]["manifest"] = json.loads(
                (root / "t2" / role / "manifest.json").read_text(encoding="utf-8"))

    out = args.destination / f"{args.run_id}_report.json"
    with io.open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1)
    print(out)


if __name__ == "__main__":
    main()
