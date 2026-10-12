"""W4 condition 3: does the decode-time stop reproduce the offline cut? (CPU only, calibration only)

For every W4 model and prompt, the archived calibration outputs are tokenized
with the model's own tokenizer at its pinned revision, and greedy decoding is
replayed under `model_survey.stop.LoopStoppingCriteria`'s rule: stop after the
first token whose decoded prefix holds a run, then cut it. The result is
compared character for character with `loop_cut.variant_b` on the full output.

Recorded outputs keep text, not token ids, so the replay re-encodes the text.
Where decoding the re-encoded ids does not give the text back, the item is
reported as not replayable rather than compared. Writes one JSON file with no
output or reference text, and refuses to overwrite it.
"""

from __future__ import annotations

import argparse
import gzip
import json
import subprocess
from pathlib import Path

from labbs2026.model_survey.stop import K, K_LONG, replay
from labbs2026.thai_marks.loop_cut import variant_b

DATA = Path("docs/stage0/data")
# (role, model_id, revision, archive, prompts): W4's models and prompts, from their calibration runs
MODELS = [
    ("typhoon", "typhoon-ai/typhoon-ocr1.5-2b", "9c8a8fa14905041d793f1e4e922312147956dcc0",
     "T1_OUTPUTS_a44199c29759.json.gz", ["BENCHMARK_QUESTION"]),
    ("base", "Qwen/Qwen3-VL-2B-Instruct", "89644892e4d85e24eaac8bacfd4f463576704203",
     "T1_OUTPUTS_a44199c29759.json.gz", ["BENCHMARK_QUESTION"]),
    ("wayu", "wayu-ai/wayu-paxa-ocr-zero", "af0204b4f334a6d5068b6bac2b3738932d6e289b",
     "M1_OUTPUTS_3431d9f9dccf.json.gz", ["OCR_NATIVE"]),
    ("pathumma", "nectec/Pathumma-llm-vision-3.0.0-re", "08bb11dcabf509ac3fa3ac0014ecd44eadb9729b",
     "M5_OUTPUTS_8252b99e735d.json.gz", ["CARD_PROMPT", "BENCHMARK_QUESTION"]),
    ("qwen3vl4b", "Qwen/Qwen3-VL-4B-Instruct", "ebb281ec70b05090aa6165b016eac8ec08e71b17",
     "M1_OUTPUTS_3431d9f9dccf.json.gz", ["BENCHMARK_QUESTION"]),
    ("paddle", "PaddlePaddle/PaddleOCR-VL-1.6", "c5630abae1d940eafe0697512a0325494b02ab42",
     "M1_OUTPUTS_3431d9f9dccf.json.gz", ["OCR_NATIVE"]),
    ("sealion", "aisingapore/Qwen-SEA-LION-v4-4B-VL", "d0734aa1b8113fce90997a83c1e4afe2c37c6205",
     "M6A_OUTPUTS_3ee076494466.json.gz", ["BENCHMARK_QUESTION"]),
    ("deepseek", "deepseek-ai/DeepSeek-OCR-2", "aaa02f3811945a91062062994c5c4a3f4c0af2b0",
     "M6B_OUTPUTS_afe5126bedd7.json.gz", ["CARD_PROMPT"]),
]


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--roles", default="", help="comma-separated subset (default: all)")
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    from transformers import AutoTokenizer

    wanted = [r for r in args.roles.split(",") if r]
    result: dict = {
        "kind": "W4 condition 3: decode-time stop vs offline cut, replayed on calibration outputs",
        "git_sha": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "rule": {"k": K, "k_long": K_LONG, "offline": "thai_marks.loop_cut.variant_b"},
        "cells": {},
    }
    for role, model_id, revision, archive, prompts in MODELS:
        if wanted and role not in wanted:
            continue
        tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        records = json.loads(gzip.open(DATA / archive, "rt", encoding="utf-8").read())["records"][role]

        def decode(ids):
            return tokenizer.decode(list(ids), skip_special_tokens=True)

        for prompt in prompts:
            rows = [r for r in records if r["prompt_kind"] == prompt]
            cell = {"model": f"{model_id}@{revision[:12]}", "archive": archive, "outputs": len(rows),
                    "looping": 0, "replayed": 0, "equal": 0, "not_equal": [],
                    "not_replayable": [], "fired_on_non_looping": []}
            for r in rows:
                offline = variant_b(r)
                loops = offline != r["raw_output"]
                ids = tokenizer.encode(r["raw_output"], add_special_tokens=False)
                if decode(ids) != r["raw_output"]:
                    cell["not_replayable"].append(r["id"])
                    continue
                out = replay(ids, decode, offline)
                if not loops:
                    if out["stopped_at"] is not None:
                        cell["fired_on_non_looping"].append(r["id"])
                    continue
                cell["looping"] += 1
                cell["replayed"] += 1
                if out["equal"]:
                    cell["equal"] += 1
                else:
                    cell["not_equal"].append({"id": r["id"], **out})
            result["cells"][f"{role} | {prompt}"] = cell
            print(role, prompt, {k: (len(v) if isinstance(v, list) else v) for k, v in cell.items()
                                 if k not in ("model", "archive")}, flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(args.out)


if __name__ == "__main__":
    main()
