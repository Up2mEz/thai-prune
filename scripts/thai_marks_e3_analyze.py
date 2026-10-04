"""E3: verify a fetched e3 run and score the registered method (offline)."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import statistics
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from labbs2026.thai_marks.analysis import anchored_cer
from labbs2026.thai_marks.attribution import reference_lines
from labbs2026.thai_marks.confidence import CONSONANT_SET, aligned_pairs_full_page, clusters, label_clusters
from labbs2026.thai_marks.extract import extract_text
from labbs2026.thai_marks.loop_cut import variant_b
from labbs2026.thai_marks.order_free import mark_counts, prf
from labbs2026.thai_marks.reread_method import band_spans, choose_bands, flagged_lines, word_edits
from labbs2026.thai_marks.reread_probe import apply_edits
from labbs2026.thai_marks.t5_analysis import paired_bootstrap_delta_f1

TOKENIZER = ("Qwen/Qwen3-VL-2B-Instruct", "89644892e4d85e24eaac8bacfd4f463576704203")
CELL = "Full-page OCR"
_TOK = None


def _tok():
    global _TOK
    if _TOK is None:
        from transformers import AutoTokenizer
        _TOK = AutoTokenizer.from_pretrained(TOKENIZER[0], revision=TOKENIZER[1])
    return _TOK


def _offsets(raw: str, ids) -> list[tuple[int, int]]:
    from labbs2026.thai_marks.confidence import token_offsets
    return token_offsets(_tok(), raw, ids)


def _segment(text: str) -> list[str]:
    from pythainlp.tokenize import word_tokenize
    return word_tokenize(text, engine="newmm", keep_whitespace=True)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _page(job: dict) -> dict:
    """Method (c) for one page read; returns outputs, edits, cost and band-choice checks."""
    raw_full, page_scores, bands = job["raw"], job["scores"], job["bands"]
    stopped = variant_b({"raw_output": raw_full, "reached_max_new_tokens": False})
    offsets = _offsets(raw_full, page_scores["token_ids"])
    spans = band_spans()
    band_tok = {t: (b["raw_output"], _offsets(b["raw_output"], b["scores"]["token_ids"]),
                    b["scores"]["logprob"]) for t, b in bands.items()}
    lines = flagged_lines(stopped, offsets, page_scores["logprob"], clusters(stopped))
    used, edits, choice = set(), [], collections.Counter()
    for line in lines:
        chosen = choose_bands(line[0] / max(1, len(stopped)), spans)
        used |= set(chosen)
        # band-choice check: does the choice include the band read matching the line best?
        from labbs2026.thai_marks.decompose import align_anchored, edit_distance_from
        text = stopped[line[0]:line[1]]
        cers = {t: edit_distance_from(align_anchored(text, b[0])[0], text, b[0]) / len(text)
                for t, b in band_tok.items() if b[0]}
        if cers:
            best = min(cers, key=cers.get)
            choice["lines"] += 1
            choice["best_band_chosen"] += int(best in chosen)
        edits += word_edits(stopped, line, offsets, page_scores["logprob"],
                            [band_tok[t] for t in chosen if t in band_tok], _segment)
    final = apply_edits(stopped, edits)
    extra = job["e1_seconds"] + sum(bands[t]["seconds_generate"] + bands[t]["seconds_score"]
                                    for t in used if t in bands)
    return {"stopped": stopped, "final": final, "edits": edits, "bands_used": sorted(used),
            "extra_seconds": extra, "choice": dict(choice), "flagged_lines": len(lines)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="fetched e3 artifacts/<run_id>")
    parser.add_argument("--e1-run-dir", type=Path, required=True)
    parser.add_argument("--t5-run-dir", type=Path, required=True)
    parser.add_argument("--design-pages", type=Path, default=Path("configs/thai_marks/p_zoom_pages.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    root = args.run_dir
    if (root / "FAILURE.json").exists():
        raise SystemExit("run failed: " + (root / "FAILURE.json").read_text(encoding="utf-8"))
    for line in (root / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"checksum mismatch: {relative}")
    success = json.loads((root / "SUCCESS.json").read_text(encoding="utf-8"))

    bands: dict[str, dict[int, dict]] = collections.defaultdict(dict)
    for p in sorted(root.glob("e3/typhoon/**/records.jsonl")):
        for r in _jsonl(p):
            bands[r["id"]][r["tile"]] = r
    e1 = {r["case"]: r for p in sorted(args.e1_run_dir.glob("*/typhoon/*/records.jsonl")) for r in _jsonl(p)}
    t5 = [r for p in sorted((args.t5_run_dir / "t5" / "typhoon").glob("*/records.jsonl"))
          for r in _jsonl(p) if r["arm"] == "greedy" and r["task"] == CELL]
    design = {p["id"] for p in json.loads(args.design_pages.read_text(encoding="utf-8"))["pages"]}

    jobs, keys = [], []
    for r in sorted(t5, key=lambda r: (r["prompt_kind"], r["id"])):
        case = e1[f"{CELL}|{r['prompt_kind']}|{r['id']}"]
        jobs.append({"raw": r["raw_output"], "scores": case["scores"], "bands": bands.get(r["id"], {}),
                     "e1_seconds": case["seconds"]})
        keys.append(r)
    with ProcessPoolExecutor(6) as pool:
        results = list(pool.map(_page, jobs))

    out: dict = {"run": success["run_id"], "gpus": success["gpus"],
                 "bands_read": sum(len(v) for v in bands.values()),
                 "provenance": {"git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                                          text=True, check=True).stdout.strip(),
                                "rule": "docs/stage0/E3_FLAGGED_BAND_REREAD_DRAFT.md"},
                 "cells": {}}
    for prompt in ("BENCHMARK_QUESTION", "TYPHOON_CARD"):
        for subset in ("all", "design21", "other48"):
            idx = [i for i, r in enumerate(keys) if r["prompt_kind"] == prompt and (
                subset == "all" or (subset == "design21") == (r["id"] in design))]
            if not idx:
                continue
            a = [mark_counts(keys[i]["reference"], keys[i]["raw_output"], residual=True) for i in idx]
            b = [mark_counts(keys[i]["reference"], results[i]["stopped"], residual=True) for i in idx]
            c = [mark_counts(keys[i]["reference"], results[i]["final"], residual=True) for i in idx]
            ref = [" ".join(reference_lines(keys[i]["reference"])) for i in idx]
            cer = {name: statistics.fmean(anchored_cer(rf, extract_text(o)) for rf, o in zip(ref, outs))
                   for name, outs in (("b", [results[i]["stopped"] for i in idx]),
                                      ("c", [results[i]["final"] for i in idx]))}
            tally, kinds = collections.Counter(), collections.Counter()
            for i in idx:
                st, fi = results[i]["stopped"], results[i]["final"]
                if not results[i]["edits"]:
                    continue
                before = {x["start"]: x["error"] for x in label_clusters(st, aligned_pairs_full_page(keys[i]["reference"], st))}
                after_lab = label_clusters(fi, aligned_pairs_full_page(keys[i]["reference"], fi))
                shift = 0
                for s0, e0, new in sorted(results[i]["edits"]):
                    old = st[s0:e0]
                    kinds["same consonants" if [ch for ch in old if ch in CONSONANT_SET]
                          == [ch for ch in new if ch in CONSONANT_SET] else "consonants change"] += 1
                    old_err = [before[k] for k in before if s0 <= k < e0]
                    new_err = [x["error"] for x in after_lab if s0 + shift <= x["start"] < s0 + shift + len(new)]
                    shift += len(new) - (e0 - s0)
                    if not old_err or not new_err:
                        tally["unlabelled"] += 1
                    elif sum(new_err) < sum(old_err):
                        tally["fixed"] += 1
                    elif sum(new_err) > sum(old_err):
                        tally["broken"] += 1
                    else:
                        tally["unchanged_label"] += 1
            page_seconds = sum(keys[i]["seconds_generate"] for i in idx)
            extra = sum(results[i]["extra_seconds"] for i in idx)
            choice = collections.Counter()
            for i in idx:
                choice.update(results[i]["choice"])
            fb, fc = prf(b)["f1"], prf(c)["f1"]
            out["cells"][f"{prompt} / {subset}"] = {
                "pages": len(idx), "f1": {"a": prf(a)["f1"], "b": fb, "c": fc},
                "delta_c_minus_b": paired_bootstrap_delta_f1(c, b), "cer": cer,
                "edits": sum(len(results[i]["edits"]) for i in idx), **tally, "edit_kinds": dict(kinds),
                "flagged_lines": sum(results[i]["flagged_lines"] for i in idx),
                "band_choice": dict(choice),
                "extra_seconds_share": extra / max(1e-9, page_seconds),
                "bands_used_mean": statistics.fmean(len(results[i]["bands_used"]) for i in idx)}
    full = [out["cells"][f"{p} / all"] for p in ("BENCHMARK_QUESTION", "TYPHOON_CARD")]
    fixed = sum(c.get("fixed", 0) for c in full)
    broken = sum(c.get("broken", 0) for c in full)
    conditions = {
        "f1_rises_both_prompts": all(c["f1"]["c"] > c["f1"]["b"] for c in full),
        "fixed_at_least_twice_broken": fixed >= 2 * broken,
        "cer_not_worse": all(c["cer"]["c"] <= c["cer"]["b"] for c in full),
        "extra_time_at_most_50pct": all(c["extra_seconds_share"] <= 0.5 for c in full),
    }
    out["conditions"] = conditions
    out["verdict"] = "PASS" if all(conditions.values()) else "FAIL: " + ", ".join(k for k, v in conditions.items() if not v)
    out["examples"] = [{"id": keys[i]["id"], "prompt": keys[i]["prompt_kind"],
                        "edits": [(results[i]["stopped"][s:e], n) for s, e, n in results[i]["edits"][:8]]}
                       for i in range(len(keys)) if results[i]["edits"]][:30]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for name, c in out["cells"].items():
        d = c["delta_c_minus_b"]
        print(f"{name}: pages {c['pages']} F1 a {c['f1']['a']:.4f} b {c['f1']['b']:.4f} c {c['f1']['c']:.4f} "
              f"(c-b {d['delta']:+.4f} [{d['ci_low']:+.4f}, {d['ci_high']:+.4f}]) CER b {c['cer']['b']:.4f} c {c['cer']['c']:.4f} "
              f"edits {c['edits']} fixed {c.get('fixed', 0)} broken {c.get('broken', 0)} kinds {c['edit_kinds']} "
              f"extra time {c['extra_seconds_share']:.0%} bands/page {c['bands_used_mean']:.2f} choice {c['band_choice']}")
    print("conditions:", conditions)
    print("verdict:", out["verdict"])


if __name__ == "__main__":
    main()
