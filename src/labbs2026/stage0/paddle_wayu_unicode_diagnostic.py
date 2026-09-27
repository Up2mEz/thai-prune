"""Open-calibration-only Unicode decoder diagnostics for Paddle/Wayu S0."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable


DECODE_KWARGS = {
    "skip_special_tokens": True,
    "clean_up_tokenization_spaces": False,
}
MAX_NEW_TOKENS = 32
TAIL_TOKEN_COUNT = 8


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def eos_ids(tokenizer: Any) -> set[int]:
    value = tokenizer.eos_token_id
    if value is None:
        return set()
    if isinstance(value, int):
        return {value}
    return {int(item) for item in value}


def _decode_diagnostic(
    row: dict[str, Any],
    processor: Any,
    *,
    max_new_tokens: int = MAX_NEW_TOKENS,
    tail_token_count: int = TAIL_TOKEN_COUNT,
) -> dict[str, Any]:
    token_ids = [int(item) for item in row["generated_token_ids"]]
    tokenizer = processor.tokenizer
    processor_output = processor.decode(token_ids, **DECODE_KWARGS)
    tokenizer_output = tokenizer.decode(token_ids, **DECODE_KWARGS)
    endings = eos_ids(tokenizer)
    reached_cap = len(token_ids) == max_new_tokens
    ended_by_eos = bool(token_ids and token_ids[-1] in endings)
    return {
        "call_index": int(row["call_index"]),
        "model_role": row["model_role"],
        "model_id": row["model_id"],
        "revision": row["revision"],
        "generated_token_count": len(token_ids),
        "generated_token_ids": token_ids,
        "token_pieces": tokenizer.convert_ids_to_tokens(token_ids),
        "eos_token_ids": sorted(endings),
        "ended_by_eos": ended_by_eos,
        "reached_max_new_tokens": reached_cap,
        "observed_stop_class": (
            "EOS" if ended_by_eos else "MAX_NEW_TOKENS" if reached_cap else "NO_EOS_BELOW_CAP_UNKNOWN"
        ),
        "processor_decode": processor_output,
        "tokenizer_decode": tokenizer_output,
        "stored_raw_output": row["raw_output"],
        "processor_equals_tokenizer": processor_output == tokenizer_output,
        "processor_equals_stored": processor_output == row["raw_output"],
        "processor_contains_ufffd": "\ufffd" in processor_output,
        "tokenizer_contains_ufffd": "\ufffd" in tokenizer_output,
        "stored_contains_ufffd": "\ufffd" in row["raw_output"],
        "tail_token_ids": token_ids[-tail_token_count:],
        "tail_token_pieces": tokenizer.convert_ids_to_tokens(token_ids[-tail_token_count:]),
    }


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_role[row["model_role"]].append(row)

    def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        count = len(rows)
        cap = [row for row in rows if row["reached_max_new_tokens"]]
        ufffd = [row for row in rows if row["processor_contains_ufffd"]]
        return {
            "output_count": count,
            "token_length_distribution": {
                str(key): value
                for key, value in sorted(Counter(row["generated_token_count"] for row in rows).items())
            },
            "ended_by_eos_count": sum(row["ended_by_eos"] for row in rows),
            "max_new_tokens_hit_count": len(cap),
            "max_new_tokens_hit_rate": len(cap) / count if count else None,
            "ufffd_count": len(ufffd),
            "ufffd_rate": len(ufffd) / count if count else None,
            "cap_reaching_valid_decode_count": sum(not row["processor_contains_ufffd"] for row in cap),
            "cap_reaching_valid_decode_rate": (
                sum(not row["processor_contains_ufffd"] for row in cap) / len(cap) if cap else None
            ),
            "processor_tokenizer_mismatch_count": sum(not row["processor_equals_tokenizer"] for row in rows),
            "processor_stored_mismatch_count": sum(not row["processor_equals_stored"] for row in rows),
        }

    return {
        "overall": summary(records),
        "by_model_role": {role: summary(rows) for role, rows in sorted(by_role.items())},
    }


def _byte_fallback_ids(tokenizer: Any, text: str) -> list[int]:
    pieces = [f"<0x{value:02X}>" for value in text.encode("utf-8")]
    ids = [int(tokenizer.convert_tokens_to_ids(piece)) for piece in pieces]
    if tokenizer.unk_token_id is not None and any(item == tokenizer.unk_token_id for item in ids):
        raise RuntimeError(f"tokenizer lacks required byte-fallback pieces: {pieces}")
    if tokenizer.convert_ids_to_tokens(ids) != pieces:
        raise RuntimeError(f"byte-fallback token round-trip mismatch: {pieces} -> {ids}")
    return ids


def _synthetic_case(name: str, ids: list[int], processor: Any, termination: str) -> dict[str, Any]:
    tokenizer = processor.tokenizer
    processor_output = processor.decode(ids, **DECODE_KWARGS)
    tokenizer_output = tokenizer.decode(ids, **DECODE_KWARGS)
    return {
        "case": name,
        "termination": termination,
        "token_ids": ids,
        "token_pieces": tokenizer.convert_ids_to_tokens(ids),
        "processor_decode": processor_output,
        "tokenizer_decode": tokenizer_output,
        "processor_contains_ufffd": "\ufffd" in processor_output,
        "tokenizer_contains_ufffd": "\ufffd" in tokenizer_output,
        "processor_equals_tokenizer": processor_output == tokenizer_output,
    }


def synthetic_byte_fallback_diagnostic(processor: Any) -> dict[str, Any]:
    tokenizer = processor.tokenizer
    endings = eos_ids(tokenizer)
    if len(endings) != 1:
        raise RuntimeError(f"expected one EOS token id, got {sorted(endings)}")
    eos = next(iter(endings))
    safe_ids = tokenizer.encode("A", add_special_tokens=False)
    if len(safe_ids) != 1 or "\ufffd" in tokenizer.decode(safe_ids, **DECODE_KWARGS):
        raise RuntimeError("could not establish one-token valid synthetic prefix")
    literal_ufffd_ids = [int(item) for item in tokenizer.encode("\ufffd", add_special_tokens=False)]
    literal_ufffd_case = _synthetic_case(
        "literal_replacement_character_tokenization",
        literal_ufffd_ids,
        processor,
        "COMPLETE_SEQUENCE_NO_EOS",
    )

    samples = []
    for text in ("ก", "่", "ำ"):
        byte_ids = _byte_fallback_ids(tokenizer, text)
        if len(byte_ids) != 3:
            raise RuntimeError(f"expected three UTF-8 byte tokens for {text!r}: {byte_ids}")
        cases = [
            _synthetic_case("complete_bytes", byte_ids, processor, "COMPLETE_SEQUENCE_NO_EOS"),
            _synthetic_case("complete_bytes_then_eos", byte_ids + [eos], processor, "EOS"),
            _synthetic_case("one_byte_no_eos", byte_ids[:1], processor, "SYNTHETIC_TRUNCATION"),
            _synthetic_case("two_bytes_no_eos", byte_ids[:2], processor, "SYNTHETIC_TRUNCATION"),
            _synthetic_case("one_byte_then_eos", byte_ids[:1] + [eos], processor, "EOS"),
            _synthetic_case("two_bytes_then_eos", byte_ids[:2] + [eos], processor, "EOS"),
            _synthetic_case(
                "cap32_ends_after_one_byte",
                safe_ids * (MAX_NEW_TOKENS - 1) + byte_ids[:1],
                processor,
                "MAX_NEW_TOKENS",
            ),
            _synthetic_case(
                "cap32_ends_after_two_bytes",
                safe_ids * (MAX_NEW_TOKENS - 2) + byte_ids[:2],
                processor,
                "MAX_NEW_TOKENS",
            ),
        ]
        samples.append(
            {
                "text": text,
                "unicode_codepoints": [f"U+{ord(char):04X}" for char in text],
                "utf8_hex": [f"{value:02X}" for value in text.encode("utf-8")],
                "byte_fallback_token_ids": byte_ids,
                "byte_fallback_token_pieces": tokenizer.convert_ids_to_tokens(byte_ids),
                "cases": cases,
            }
        )
    return {
        "synthetic_only": True,
        "research_images_used": False,
        "model_inference_used": False,
        "eos_token_id": eos,
        "safe_prefix_token_id": safe_ids[0],
        "safe_prefix_piece": tokenizer.convert_ids_to_tokens(safe_ids)[0],
        "literal_ufffd_case": literal_ufffd_case,
        "samples": samples,
    }


def build_diagnostic(
    s0_artifact_dir: Path,
    processor_loader: Callable[[str, str], Any],
    *,
    transformers_version: str,
) -> dict[str, Any]:
    artifact = s0_artifact_dir.resolve()
    if "attempt4" in str(artifact).lower() or "locked-panel" in str(artifact).lower():
        raise ValueError("diagnostic input must be an S0 open-calibration artifact, never a locked artifact")

    raw_path = artifact / "raw_outputs.jsonl"
    model_path = artifact / "model_revision_manifest.json"
    environment_path = artifact / "environment_manifest.json"
    rows = load_jsonl(raw_path)
    manifest = json.loads(model_path.read_text("utf-8"))
    source_environment = json.loads(environment_path.read_text("utf-8"))
    if len(rows) != 1520:
        raise RuntimeError(f"expected 1520 S0 outputs, got {len(rows)}")
    if source_environment["environment"]["transformers"] != transformers_version:
        raise RuntimeError(
            "diagnostic Transformers version differs from S0: "
            f"{transformers_version} != {source_environment['environment']['transformers']}"
        )

    processors: dict[str, Any] = {}
    model_identity = []
    for model in manifest["models"]:
        role = model["role"]
        if model["requested_revision"] != model["resolved_revision"]:
            raise RuntimeError(f"S0 model revision mismatch for {role}")
        processor = processor_loader(model["model_id"], model["resolved_revision"])
        processors[role] = processor
        model_identity.append(
            {
                "role": role,
                "model_id": model["model_id"],
                "revision": model["resolved_revision"],
                "processor_class": type(processor).__name__,
                "tokenizer_class": type(processor.tokenizer).__name__,
                "eos_token_id": processor.tokenizer.eos_token_id,
            }
        )

    diagnostics = [_decode_diagnostic(row, processors[row["model_role"]]) for row in rows]
    synthetic = {
        role: synthetic_byte_fallback_diagnostic(processor)
        for role, processor in sorted(processors.items())
    }
    all_synthetic_cases = [
        case
        for result in synthetic.values()
        for sample in result["samples"]
        for case in sample["cases"]
    ]
    synthetic_cap_ufffd = any(
        case["termination"] == "MAX_NEW_TOKENS" and case["processor_contains_ufffd"]
        for case in all_synthetic_cases
    )
    synthetic_noncap_ufffd = any(
        case["termination"] != "MAX_NEW_TOKENS" and case["processor_contains_ufffd"]
        for case in all_synthetic_cases
    )
    summary = summarize_records(diagnostics)

    return {
        "schema_version": 1,
        "scope": "S0_OPEN_CALIBRATION_AND_TOKENIZER_ONLY_SYNTHETIC_DIAGNOSTIC",
        "governance": {
            "attempt4_scientific_outputs_opened": False,
            "attempt4_failure_location_mapped_to_scientific_factors": False,
            "locked_images_generated": False,
            "model_inference_performed": False,
            "scientific_design_modified": False,
            "attempt5_created_or_submitted": False,
        },
        "source": {
            "artifact_dir": str(artifact),
            "raw_outputs_sha256": sha256_file(raw_path),
            "model_revision_manifest_sha256": sha256_file(model_path),
            "environment_manifest_sha256": sha256_file(environment_path),
            "source_environment": source_environment,
        },
        "diagnostic_environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "transformers": transformers_version,
        },
        "frozen_decode_contract": {
            "max_new_tokens": MAX_NEW_TOKENS,
            **DECODE_KWARGS,
        },
        "models": model_identity,
        "s0_summary": summary,
        "s0_outputs": diagnostics,
        "synthetic_tokenizer_diagnostic": synthetic,
        "hypothesis_evaluation": {
            "hypothesis": (
                "U+FFFD can be generated because max_new_tokens terminates generation at a "
                "token/byte boundary that leaves the decoded byte-fallback sequence incomplete."
            ),
            "classification": "SUPPORTED_MECHANISTICALLY",
            "evidence": {
                "synthetic_cap_terminated_incomplete_byte_sequences_produce_ufffd": synthetic_cap_ufffd,
                "synthetic_noncap_incomplete_byte_sequences_produce_ufffd": synthetic_noncap_ufffd,
                "s0_cap_hits": summary["overall"]["max_new_tokens_hit_count"],
                "s0_cap_hits_with_valid_decode": summary["overall"]["cap_reaching_valid_decode_count"],
                "s0_ufffd_occurrences": summary["overall"]["ufffd_count"],
            },
            "limitation": (
                "This establishes a possible tokenizer mechanism only; sealed Attempt-4 token tails "
                "were not inspected, so it does not identify the Attempt-4 trigger."
            ),
        },
        "root_cause_classification": "E. MULTIPLE_PLAUSIBLE_CAUSES_REMAIN",
        "next_action_classification": "B. SCIENTIFIC_PROTOCOL_AMENDMENT_REQUIRED",
        "terminal_state": "SCIENTIFIC_PROTOCOL_AMENDMENT_PENDING_HUMAN_REVIEW",
    }


def write_diagnostic(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
