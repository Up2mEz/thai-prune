"""MODEL_SURVEY_M5 — Pathumma's JSON-wrapped outputs (registration Addendum 1).

On the smoke, one of Pathumma's four outputs came wrapped as Typhoon OCR's
JSON format, `{"natural_text": "..."}`, with newlines as `\\n` escapes, and it
ran to the token limit, so the JSON never closed. M1's scoring reads it as
written, and that stays the registered primary. As a secondary score fixed
before the full run, `unwrap_natural_text` recovers the text value:

- a complete JSON object with a string `natural_text` gives that string;
- an unclosed one (truncated at the limit) gives its prefix, with JSON escapes
  decoded up to the first one that cannot be decoded;
- anything else is returned unchanged.
"""

from __future__ import annotations

import json
import re

_OPEN = re.compile(r'^\s*\{\s*"natural_text"\s*:\s*"')


def unwrap_natural_text(raw_output: str) -> str:
    """The `natural_text` value of a JSON-wrapped output, else the output unchanged."""
    if not _OPEN.match(raw_output):
        return raw_output
    try:
        value = json.loads(raw_output)
    except ValueError:
        value = None
    if isinstance(value, dict) and isinstance(value.get("natural_text"), str):
        return value["natural_text"]
    body = raw_output[_OPEN.match(raw_output).end():]
    out, i = [], 0
    while i < len(body):                       # decode a truncated JSON string prefix
        c = body[i]
        if c == '"':
            break
        if c != "\\":
            out.append(c)
            i += 1
            continue
        try:
            piece = body[i:i + 6] if body[i + 1:i + 2] == "u" else body[i:i + 2]
            out.append(json.loads(f'"{piece}"'))
            i += len(piece)
        except (ValueError, IndexError):
            break
    return "".join(out)


def is_wrapped(raw_output: str) -> bool:
    """Whether an output opens as Typhoon's `{"natural_text": "` JSON."""
    return bool(_OPEN.match(raw_output))
