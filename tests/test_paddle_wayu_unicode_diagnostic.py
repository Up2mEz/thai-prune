from __future__ import annotations

from labbs2026.stage0.paddle_wayu_unicode_diagnostic import (
    _decode_diagnostic,
    summarize_records,
    synthetic_byte_fallback_diagnostic,
)


class FakeTokenizer:
    eos_token_id = 2
    unk_token_id = 0
    pieces = {
        2: "</s>",
        10: "A",
        237: "<0xE0>",
        197: "<0xB8>",
        142: "<0x81>",
        143: "<0xB9>",
        144: "<0x88>",
        145: "<0xB3>",
        146: "�",
    }

    def encode(self, text, add_special_tokens=False):
        assert not add_special_tokens
        if text == "A":
            return [10]
        if text == "�":
            return [146]
        raise AssertionError(text)

    def convert_tokens_to_ids(self, piece):
        return {value: key for key, value in self.pieces.items()}.get(piece, self.unk_token_id)

    def convert_ids_to_tokens(self, ids):
        return [self.pieces[item] for item in ids]

    def decode(self, ids, *, skip_special_tokens, clean_up_tokenization_spaces):
        assert skip_special_tokens
        assert not clean_up_tokenization_spaces
        payload = bytearray()
        output = []
        for item in ids:
            piece = self.pieces[item]
            if item == 2:
                continue
            if piece.startswith("<0x"):
                payload.append(int(piece[3:5], 16))
            else:
                if payload:
                    output.append(payload.decode("utf-8", errors="replace"))
                    payload.clear()
                output.append(piece)
        if payload:
            output.append(payload.decode("utf-8", errors="replace"))
        return "".join(output)


class FakeProcessor:
    def __init__(self):
        self.tokenizer = FakeTokenizer()

    def decode(self, ids, **kwargs):
        return self.tokenizer.decode(ids, **kwargs)


def test_decode_diagnostic_distinguishes_eos_and_cap():
    processor = FakeProcessor()
    eos = _decode_diagnostic({
        "call_index": 1,
        "model_role": "BASE",
        "model_id": "model",
        "revision": "rev",
        "generated_token_ids": [10, 2],
        "raw_output": "A",
    }, processor)
    cap = _decode_diagnostic({
        "call_index": 2,
        "model_role": "BASE",
        "model_id": "model",
        "revision": "rev",
        "generated_token_ids": [10] * 31 + [237],
        "raw_output": "A" * 31 + "\ufffd",
    }, processor)
    assert eos["observed_stop_class"] == "EOS"
    assert cap["observed_stop_class"] == "MAX_NEW_TOKENS"
    assert cap["processor_contains_ufffd"]


def test_summary_counts_valid_cap_output_and_decode_equivalence():
    processor = FakeProcessor()
    rows = [
        _decode_diagnostic({
            "call_index": 1,
            "model_role": "BASE",
            "model_id": "model",
            "revision": "rev",
            "generated_token_ids": [10] * 32,
            "raw_output": "A" * 32,
        }, processor),
        _decode_diagnostic({
            "call_index": 2,
            "model_role": "BASE",
            "model_id": "model",
            "revision": "rev",
            "generated_token_ids": [10, 2],
            "raw_output": "A",
        }, processor),
    ]
    summary = summarize_records(rows)["overall"]
    assert summary["output_count"] == 2
    assert summary["max_new_tokens_hit_count"] == 1
    assert summary["cap_reaching_valid_decode_count"] == 1
    assert summary["processor_tokenizer_mismatch_count"] == 0
    assert summary["processor_stored_mismatch_count"] == 0


def test_synthetic_incomplete_thai_bytes_produce_ufffd_with_and_without_cap():
    result = synthetic_byte_fallback_diagnostic(FakeProcessor())
    cases = [case for sample in result["samples"] for case in sample["cases"]]
    assert all(
        not next(case for case in sample["cases"] if case["case"] == "complete_bytes")["processor_contains_ufffd"]
        for sample in result["samples"]
    )
    assert any(case["termination"] == "MAX_NEW_TOKENS" and case["processor_contains_ufffd"] for case in cases)
    assert any(case["termination"] == "EOS" and case["processor_contains_ufffd"] for case in cases)
    assert all(case["processor_equals_tokenizer"] for case in cases)
    assert result["literal_ufffd_case"]["token_ids"] == [146]
    assert result["literal_ufffd_case"]["processor_contains_ufffd"]
