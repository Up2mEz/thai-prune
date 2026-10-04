"""E2 offline probe: do P-ZOOM re-reads fix the misreads E1 flags? (no inference)."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path

from labbs2026.thai_marks.confidence import (
    aligned_pairs_full_page,
    cluster_scores,
    label_clusters,
    token_offsets,
)
from labbs2026.thai_marks.reread_probe import view_status

TOKENIZER = ("Qwen/Qwen3-VL-2B-Instruct", "89644892e4d85e24eaac8bacfd4f463576704203")
PROMPT = "TYPHOON_CARD"
CELL = "Full-page OCR"


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e1-run-dir", type=Path, required=True)
    parser.add_argument("--t5-run-dir", type=Path, required=True)
    parser.add_argument("--tiles", type=Path, required=True, help="P-ZOOM t4 records.jsonl")
    parser.add_argument("--views", type=Path, required=True, help="P-ZOOM-2 records.jsonl")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(TOKENIZER[0], revision=TOKENIZER[1])
    scores = {r["case"]: r["scores"] for p in sorted(args.e1_run_dir.glob("*/typhoon/*/records.jsonl"))
              for r in _jsonl(p)}
    t5 = {r["id"]: r for p in sorted((args.t5_run_dir / "t5" / "typhoon").glob("*/records.jsonl"))
          for r in _jsonl(p) if r["arm"] == "greedy" and r["task"] == CELL and r["prompt_kind"] == PROMPT}

    reads: dict[str, dict[str, list[str]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in _jsonl(args.tiles):
        reads[r["id"]]["tiles"].append(r["raw_output"])
    for r in _jsonl(args.views):
        reads[r["id"]][r["view"]].append(r["raw_output"])
    pages = sorted(reads)

    # Flag threshold: the E1 gate's 5%, over every labelled cluster of the cell (all 69 pages).
    clusters_by_page: dict[str, list[dict]] = {}
    ref_by_page: dict[str, dict] = {}
    for pid, r in t5.items():
        if r["reached_max_new_tokens"]:
            continue
        raw, s = r["raw_output"], scores[f"{CELL}|{PROMPT}|{pid}"]
        pairs = aligned_pairs_full_page(r["reference"], raw)
        labelled = label_clusters(raw, pairs)
        clusters_by_page[pid] = cluster_scores(labelled, token_offsets(tok, raw, s["token_ids"]),
                                               s["logprob"], s["entropy"])
        ref_by_page[pid] = {p[2]: (p[0], p[1]) for p in pairs}
    all_s = sorted(c["s_min"] for cs in clusters_by_page.values() for c in cs)
    threshold = all_s[int(0.95 * len(all_s))]

    table: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    examples = []
    for pid in pages:
        for c in clusters_by_page.get(pid, []):
            if c["s_min"] < threshold:
                continue
            line, ref_index = ref_by_page[pid][c["start"]] if c["start"] in ref_by_page[pid] else (None, None)
            if line is None:
                continue
            kind = "error" if c["error"] else "correct"
            for view in ("tiles", "bands", "pad", "scale90"):
                status = view_status(line, ref_index, reads[pid][view])
                table[f"{kind}|{view}"][status] += 1
            if c["error"] and len(examples) < 30:
                examples.append({"id": pid, "ref": line[max(0, ref_index - 5):ref_index + 6],
                                 "status": {v: view_status(line, ref_index, reads[pid][v])
                                            for v in ("tiles", "bands", "pad", "scale90")}})
    summary = {}
    for view in ("tiles", "bands", "pad", "scale90"):
        e, k = table[f"error|{view}"], table[f"correct|{view}"]
        summary[view] = {"flagged_errors": sum(e.values()), "fixed": e["right"],
                         "fix_rate": e["right"] / max(1, sum(e.values())), "errors_not_found": e["not_found"],
                         "flagged_correct": sum(k.values()), "broken": k["wrong"],
                         "break_rate": k["wrong"] / max(1, sum(k.values())),
                         "correct_not_found": k["not_found"]}
    control = (summary["pad"]["fix_rate"] + summary["scale90"]["fix_rate"]) / 2
    def reading() -> str:
        for zoom in ("bands", "tiles"):
            z = summary[zoom]
            if z["fix_rate"] >= 0.30 and z["fix_rate"] - control >= 0.15 and z["broken"] < z["fixed"]:
                return f"zoom_fixes_misreads ({zoom})"
        if max(summary[v]["fix_rate"] for v in summary) >= 0.30:
            return "any_reread_fixes"
        return "reread_does_not_fix"
    out = {"provenance": {"git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                                    text=True, check=True).stdout.strip(),
                          "rule": "docs/stage0/E2_REREAD_FIXES_MISREADS_DRAFT.md",
                          "inputs_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                            for p in (args.tiles, args.views)}},
           "pages": len(pages), "flag_threshold_s_min": threshold, "summary": summary,
           "control_fix_rate": control, "reading": reading(), "examples": examples}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("pages", "flag_threshold_s_min", "control_fix_rate", "reading")}, indent=1))
    for view, s in summary.items():
        print(view, s)
    for e in examples[:15]:
        print("  ", e["id"], repr(e["ref"]), e["status"])


if __name__ == "__main__":
    main()
