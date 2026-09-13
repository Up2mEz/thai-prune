"""Run the authorized S0-open Unicode diagnostic without model inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from labbs2026.stage0.paddle_wayu_unicode_diagnostic import build_diagnostic, write_diagnostic


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--s0-artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    import transformers
    from transformers import AutoProcessor

    def load_processor(model_id: str, revision: str):
        return AutoProcessor.from_pretrained(
            model_id,
            revision=revision,
            trust_remote_code=False,
        )

    result = build_diagnostic(
        args.s0_artifact_dir,
        load_processor,
        transformers_version=transformers.__version__,
    )
    write_diagnostic(result, args.output)
    print(json.dumps({
        "output": str(args.output.resolve()),
        "s0_output_count": result["s0_summary"]["overall"]["output_count"],
        "s0_ufffd_count": result["s0_summary"]["overall"]["ufffd_count"],
        "classification": result["hypothesis_evaluation"]["classification"],
        "root_cause": result["root_cause_classification"],
        "next_action": result["next_action_classification"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
