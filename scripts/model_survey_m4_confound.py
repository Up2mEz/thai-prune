"""MODEL_SURVEY_M4 confound checks (Up2mEz's review, 2026-10-11): is the AUROC Wayu's confidence or the escape's forcing?

Exploratory, after the results; CPU only, no new run. Reads the M4 run's
per-token scores (local, `runs/`) and M3's archived `E` outputs, rebuilds
exactly the windows and labels of `model_survey_m4_analyze.py`, and writes:

1. the per-window table (item, window position, label, `s_mean`, forced
   share, `s_mean` over unforced tokens, distance from the escape, length);
   no reference text and no output text;
2. AUROC, with the registered item bootstrap, of: `s_mean` (must reproduce the
   registered value); `s_mean` over unforced tokens only; minus the forced
   share; `s_mean` on windows with no forced token; and two model-free
   baselines, minus the distance from the nearest preceding escape point and
   minus the window length in tokens;
3. the same scores' AUROC over pairs from the same page only.

Refuses to overwrite its output.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

import yaml

from labbs2026.model_survey.m4 import (
    escape_points,
    item_bootstrap_auroc,
    label,
    validate,
    window_forcing,
    within_item_auroc,
    window_scores,
    windows,
)

CONFIG = Path("configs/model_survey/m4.yaml")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True, help="the run's artifact directory (holds m4/)")
    parser.add_argument("--registered", type=Path, required=True, help="the committed M4 scores JSON")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    config = yaml.safe_load(CONFIG.read_text("utf-8"))
    validate(config)
    a = config["analysis"]
    width, max_cer, label_task = int(a["window_min_chars"]), float(a["label_max_cer"]), a["label_task"]
    boot = {"resamples": int(config["scoring"]["bootstrap"]["resamples"]),
            "seed": int(config["scoring"]["bootstrap"]["seed"])}

    for line in (args.run_root / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((args.run_root / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")
    scored: dict[str, dict] = {}
    for path in sorted((args.run_root / "m4").glob("shard-*/records.jsonl")):
        for line in path.read_text("utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                scored[r["id"]] = r
    archive_path = Path(config["scoring_pass"]["outputs_archive"])
    archive = json.loads(gzip.open(archive_path, "rt", encoding="utf-8").read())

    table = []
    for r in sorted(archive["records"][config["scoring_pass"]["outputs_arm"]], key=lambda r: r["id"]):
        if r["task"] != label_task or not (r["escapes"] or r["final_cut"]):
            continue
        s, p, text = scored[r["id"]], r["greedy_prefix_chars"], r["raw_output"]
        points = escape_points(r) or [p]
        spans = windows(text, p, len(text), width)
        for k, (w, f) in enumerate(zip(window_scores(spans, s["offsets"], s["logprob"], s["entropy"]),
                                       window_forcing(spans, s["offsets"], s["logprob"], s["agrees"]))):
            kind, cer = label(text[w["start"]:w["end"]], s["reference"], max_cer)
            if kind == "no_letter" or w["s_mean"] is None:
                continue
            since = max([q for q in points if q <= w["start"]] or [p])
            table.append({"id": r["id"], "window": k, "start": w["start"], "end": w["end"], "label": kind,
                          "cer": round(cer, 4), "n_tokens": w["n_tokens"], "s_mean": round(w["s_mean"], 5),
                          "forced": f["forced"], "forced_share": round(f["forced_share"], 5),
                          "s_mean_unforced": None if f["s_mean_unforced"] is None else round(f["s_mean_unforced"], 5),
                          "chars_from_escape": w["start"] - since, "chars_from_first_escape": w["start"] - p})

    def rows(score, keep=lambda w: True) -> dict[str, list]:
        out: dict[str, list] = {}
        for w in table:
            if keep(w) and score(w) is not None:
                out.setdefault(w["id"], []).append((score(w), w["label"] == "read"))
        return out

    checks = {
        "s_mean": rows(lambda w: w["s_mean"]),
        "s_mean_unforced_tokens": rows(lambda w: w["s_mean_unforced"]),
        "minus_forced_share": rows(lambda w: -w["forced_share"]),
        "s_mean_windows_with_no_forced_token": rows(lambda w: w["s_mean"], lambda w: w["forced"] == 0),
        "minus_chars_from_escape": rows(lambda w: -w["chars_from_escape"]),
        "minus_chars_from_first_escape": rows(lambda w: -w["chars_from_first_escape"]),
        "minus_n_tokens": rows(lambda w: -w["n_tokens"]),
    }
    result = {k: item_bootstrap_auroc(v, **boot) for k, v in checks.items()}
    within = {k: within_item_auroc(v) for k, v in checks.items()}
    registered = json.loads(args.registered.read_text("utf-8"))["auroc"]["s_mean"]["auroc"]
    if abs(result["s_mean"]["auroc"] - registered) > 1e-9:
        raise SystemExit(f"windows do not reproduce the registered AUROC ({result['s_mean']['auroc']} vs {registered})")
    forced = {lab: [w["forced_share"] for w in table if w["label"] == lab] for lab in ("read", "invented")}
    out = {"claim_level": config["claim_level"], "kind": "exploratory, after results (Up2mEz's review 2026-10-11)",
           "run_id": scored[next(iter(scored))].get("run_id") or args.run_root.name,
           "git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                     check=True).stdout.strip(),
           "outputs_archive": {"path": str(archive_path),
                               "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest()},
           "forced_definition": "a token that is not the teacher-forced argmax (escape-forced, or an fp16 tie)",
           "registered_s_mean_auroc_reproduced": True, "auroc": result,
           "auroc_within_page": within,
           "forced_share_by_label": {lab: {"windows": len(v), "mean": sum(v) / len(v),
                                           "with_any_forced": sum(x > 0 for x in v)} for lab, v in forced.items()},
           "windows": table}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: [v["auroc"], v["ci95"], v["items"], v["positive"], v["negative"]] for k, v in result.items()},
                     indent=1))
    print(json.dumps({k: [v["auroc"], len(v["items"]), v["pairs"]] for k, v in within.items()}, indent=1))


if __name__ == "__main__":
    main()
