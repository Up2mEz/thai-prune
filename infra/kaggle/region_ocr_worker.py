"""Kaggle bootstrap for one region-OCR pruning submission.

Thin by design: it pins the environment, proves the checkout is exactly the
commit that was registered, locates the TEMS dataset mounted by Kaggle, and then
hands control to the repository's own run module. All scientific logic lives in
the repository so that what runs remotely is what was reviewed locally.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RUN_SPEC_B64 = "__LABBS_RUN_SPEC_B64__"


def _atomic_json(path: Path, value) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _run(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-3000:]
        raise RuntimeError(f"command failed ({command[0]}): {detail}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scan_for_metadata(root: Path, metadata_sha256: str) -> tuple[Path, Path] | None:
    for candidate in sorted(root.rglob("*.csv")):
        try:
            if _sha256(candidate) == metadata_sha256:
                images = candidate.parent
                if any(images.glob("*.jpg")):
                    return candidate, images
                for nested in sorted(images.rglob("*.jpg")):
                    return candidate, nested.parent
                raise RuntimeError(f"metadata found at {candidate} but no images beside it")
        except OSError:
            continue
    return None


def _locate_dataset(root: Path, metadata_sha256: str, extract_to: Path) -> tuple[Path, Path]:
    """Find the corpus by content, not by folder name.

    Kaggle derives the mount path from the dataset title, which is easy to change
    by accident, so the metadata CSV is matched by hash instead: a renamed or
    substituted dataset fails loudly rather than running on the wrong corpus.

    The dataset is uploaded as a single archive because uploading five thousand
    individual files is slow and fails part-way, so any archive present is
    extracted first and the same content check is then applied to the result.
    """
    found = _scan_for_metadata(root, metadata_sha256)
    if found:
        return found

    import zipfile

    for archive in sorted(root.rglob("*.zip")):
        extract_to.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(extract_to)
        found = _scan_for_metadata(extract_to, metadata_sha256)
        if found:
            return found

    raise RuntimeError(f"corpus metadata with sha256 {metadata_sha256} not found under {root}")


def main() -> None:
    if RUN_SPEC_B64.startswith("__LABBS_"):
        raise RuntimeError("worker was not prepared with a run specification")
    spec = json.loads(base64.b64decode(RUN_SPEC_B64).decode("utf-8"))
    artifact_dir = Path(spec["output_root"]) / spec["run_id"]
    artifact_dir.mkdir(parents=True, exist_ok=False)
    phase = "source_checkout"
    try:
        source = Path(spec["source_dir"])
        source.mkdir(parents=True, exist_ok=False)
        _run(["git", "init"], source)
        _run(["git", "remote", "add", "origin", spec["repository_url"]], source)
        _run(["git", "fetch", "--depth", "1", "origin", spec["remote_ref"]], source)
        _run(["git", "checkout", "--detach", spec["git_sha"]], source)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=source, check=True, capture_output=True, text=True
        ).stdout.strip()
        if head != spec["git_sha"]:
            raise RuntimeError("checked-out Git SHA does not match submission")

        expected = dict(spec["expected_file_hashes"])
        for relative, expected_hash in expected.items():
            if _sha256(source / relative) != expected_hash:
                raise RuntimeError(f"source hash mismatch: {relative}")
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=source, check=True, capture_output=True, text=True
        ).stdout.strip()
        if status:
            raise RuntimeError("checked-out source tree is not clean")

        phase = "dataset_discovery"
        metadata_csv, images_dir = _locate_dataset(
            Path(spec["dataset_root"]),
            spec["dataset_metadata_sha256"],
            Path("/tmp/labbs2026-corpus"),
        )

        phase = "environment_sync"
        _run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
              "--no-input", f"uv=={spec['uv_bootstrap_version']}"], source)
        _run([sys.executable, "-m", "uv", "sync", *spec["uv_sync_args"],
              "--python", spec["python_version"]], source)
        if spec.get("transformers_override_lock"):
            _run([sys.executable, "-m", "uv", "pip", "install", "--python",
                  str(source / ".venv/bin/python"), "-r",
                  str(source / spec["transformers_override_lock"])], source)
        for relative, expected_hash in expected.items():
            if _sha256(source / relative) != expected_hash:
                raise RuntimeError(f"source changed after environment sync: {relative}")

        phase = "region_ocr_run"
        remote_spec = dict(spec)
        remote_spec["resolved_metadata_csv"] = str(metadata_csv)
        remote_spec["resolved_images_dir"] = str(images_dir)
        remote_spec["artifact_dir"] = str(artifact_dir)
        spec_path = Path("/tmp/labbs2026-region-ocr-spec.json")
        _atomic_json(spec_path, remote_spec)
        _run([str(source / ".venv/bin/python"), "-m",
              "labbs2026.region_ocr.remote", "--remote-spec", str(spec_path)], source)

        phase = "checksums"
        lines = []
        for path in sorted(p for p in artifact_dir.rglob("*") if p.is_file()):
            lines.append(f"{_sha256(path)}  {path.relative_to(artifact_dir).as_posix()}")
        (artifact_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
        _atomic_json(artifact_dir / "SUCCESS.json", {
            "schema_version": 1,
            "run_id": spec["run_id"],
            "git_sha": spec["git_sha"],
            "checksums_sha256": _sha256(artifact_dir / "checksums.sha256"),
        })
    except BaseException as exc:
        message = re.sub(r"(?i)(token|key|password)=\S+", r"\1=<redacted>", str(exc))
        if not (artifact_dir / "FAILURE.json").exists():
            _atomic_json(artifact_dir / "FAILURE.json", {
                "schema_version": 1,
                "run_id": spec.get("run_id"),
                "phase": phase,
                "exception_type": type(exc).__name__,
                "message": message[:2000],
            })
        raise


if __name__ == "__main__":
    main()
