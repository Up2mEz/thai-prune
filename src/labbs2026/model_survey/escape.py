"""MODEL_SURVEY_M3 — loop escape: decode past a loop instead of stopping at it.

M2 found that T5b's stop recovers most of what Wayu's loops cost, but not the
text the loop never reached: on the 18 Full-page pages where greedy Wayu looped,
it read about a fifth of the reference marks. M3 asks whether that text is
recoverable by decoding past the loop, with the image, prompt and decoding
otherwise unchanged.

**Escape.** Greedy decoding, M1's settings. While decoding, T5b's variant-B
rule (`thai_marks.loop_cut`, Decision Log 2026-10-03e) is checked on the output
every `every` tokens. When a run completes its 8th copy (6th for long units):

1. decoding rolls back to the first token boundary at or after the end of the
   run's first copy, where the model chose to start a second copy;
2. from there on, the run's unit (compared without whitespace) may neither be
   started again right at that point, in any tokenization, nor be completed
   again anywhere later in the output;
3. decoding continues.

The constraint acts on the greedy choice: candidates are taken in score order
and each one that would break it is set to −inf, until the best remaining one
keeps it (`TOP_K` candidates are checked). After `max_escapes` escapes, the next
run is stopped as in B (cut at its first copy). Decoding work per item is capped
at `max_total_steps` tokens, discarded ones included.

**Control built in.** The watch only stops a generation, and no constraint
exists before the first rollback. So an output in which no run completes is
greedy's output token for token, and an escaped output starts with greedy's
output up to the first rollback.
"""

from __future__ import annotations

import re
import time
from typing import Any, Callable

from labbs2026.thai_marks.loop_cut import loop_onset

STOP_K, STOP_K_LONG = 8, 6          # loop_cut.variant_b's
# A run completed since the last check lies within the last
# 6 copies × 400 characters (variant B's longest unit) plus one check's tokens.
WATCH_WINDOW_CHARS = 2600
TOP_K = 64                          # candidates checked against the constraint per step
TAIL_TOKENS = 192                   # decoded tail used for the completion check
START_WINDOW = 8                    # tokens after a rollback within which the start check applies
_WS = re.compile(r"\s+")


def strip_ws(text: str) -> str:
    return _WS.sub("", text)


def rollback_index(tokens: list[int], chars: int, decode: Callable[[list[int]], str]) -> int:
    """The smallest i with `len(decode(tokens[:i])) >= chars`, else `len(tokens)`.

    Binary search; decoded length grows with i. Rolling back to the first token
    boundary at or after a character position keeps everything before it, so a
    token that straddles the end of a run's first copy is kept whole.
    """
    lo, hi = 0, len(tokens)
    while lo < hi:
        mid = (lo + hi) // 2
        if len(decode(tokens[:mid])) >= chars:
            hi = mid
        else:
            lo = mid + 1
    return lo


def watch_fires(text: str) -> bool:
    """Whether variant B's rule finds a completed run in the recent part of `text`."""
    return loop_onset(text[-WATCH_WINDOW_CHARS:], STOP_K, STOP_K_LONG) is not None


def starts_unit(since_boundary: str, piece: str, unit_key: str) -> bool:
    """Whether `piece` extends the text after a run's first copy further into another copy.

    Whitespace is ignored. Applies only while the text after the first copy is
    still a prefix of the unit (the model has not yet deviated from it).
    """
    before = strip_ws(since_boundary)
    if not unit_key.startswith(before):
        return False
    after = strip_ws(since_boundary + piece)
    return after != before and (unit_key.startswith(after) or after.startswith(unit_key))


def completes_unit(tail: str, piece: str, unit_key: str) -> bool:
    """Whether appending `piece` to `tail` completes a new occurrence of the unit (whitespace ignored)."""
    before = strip_ws(tail)
    return (before + strip_ws(piece)).count(unit_key) > before.count(unit_key)


class EscapeState:
    """The constraints added by escapes, one per escape."""

    def __init__(self) -> None:
        # (rollback position in output tokens, end of the run's first copy in output characters, unit key)
        self.rollbacks: list[tuple[int, int, str]] = []

    def add(self, position: int, boundary_chars: int, unit: str) -> None:
        key = strip_ws(unit)
        if key:
            self.rollbacks.append((position, boundary_chars, key))

    def violates(self, position: int, piece: str, *, text: Callable[[], str], tail: str) -> bool:
        """Whether emitting `piece` at output `position` breaks a constraint.

        `text()` is the decoded output so far; `tail` is the decoded recent
        output (`TAIL_TOKENS` tokens). The start check looks at the first
        `START_WINDOW` tokens after a rollback; the completion check applies
        everywhere after it.
        """
        for start, boundary, key in self.rollbacks:
            if position < start:
                continue
            if position - start <= START_WINDOW and starts_unit(text()[boundary:], piece, key):
                return True
            if completes_unit(tail, piece, key):
                return True
        return False


def _criteria(decode: Callable[[list[int]], str], base: int, every: int):
    """A `StoppingCriteria` that stops when `watch_fires` on the output decoded so far."""
    import torch
    from transformers import StoppingCriteria

    class LoopWatch(StoppingCriteria):
        def __init__(self) -> None:
            self.fired = False
            self.calls = 0

        def __call__(self, input_ids, scores, **kwargs):
            self.calls += 1
            if self.calls % every == 0 and watch_fires(decode(input_ids[0, base:].tolist())):
                self.fired = True
            return torch.full((input_ids.shape[0],), self.fired, dtype=torch.bool, device=input_ids.device)

    return LoopWatch()


def _constraint(decode: Callable[[list[int]], str], base: int, state: EscapeState, pieces: dict[int, str]):
    """A `LogitsProcessor` enforcing `state` on the greedy choice (batch size 1)."""
    import torch
    from transformers import LogitsProcessor

    class EscapeConstraint(LogitsProcessor):
        def __call__(self, input_ids, scores):
            if not state.rollbacks:
                return scores
            output = input_ids[0, base:].tolist()
            position = len(output)
            tail = decode(output[-TAIL_TOKENS:])
            whole: list[str] = []

            def text() -> str:
                if not whole:
                    whole.append(decode(output))
                return whole[0]

            for token in torch.topk(scores[0], TOP_K).indices.tolist():
                if token not in pieces:
                    pieces[token] = decode([token])
                if not state.violates(position, pieces[token], text=text, tail=tail):
                    break
                scores[0, token] = float("-inf")
            return scores

    return EscapeConstraint()


def extend_inputs(inputs: dict[str, Any], kept: list[int]) -> dict[str, Any]:
    """The prompt inputs with `kept` output tokens appended as text (same image, same prompt)."""
    if not kept:
        return inputs
    import torch

    ids = inputs["input_ids"]
    extra = torch.tensor([kept], dtype=ids.dtype, device=ids.device)
    out = dict(inputs)
    out["input_ids"] = torch.cat([ids, extra], dim=-1)
    out["attention_mask"] = torch.cat([inputs["attention_mask"], torch.ones_like(extra)], dim=-1)
    for key in ("mm_token_type_ids", "token_type_ids"):
        if key in inputs:
            out[key] = torch.cat([inputs[key], torch.zeros_like(extra)], dim=-1)
    return out


def generate_with_escape(model, processor, image, prompt: str, *, generation: dict, device: str,
                         max_escapes: int, every: int, max_total_steps: int) -> dict[str, Any]:
    """Greedy transcription with loop escape; the record extends `thai_marks.runtime.generate`'s.

    `generation` is `generation_kwargs(...)` (+ `use_cache`); its
    `max_new_tokens` caps the kept output. Extra fields: `escapes` (one entry
    per rollback), `final_cut` (a run after the last escape was stopped as in
    B), `total_steps` (tokens decoded, discarded ones included),
    `step_cap_hit`, `generate_calls`, and `greedy_prefix_chars` /
    `greedy_prefix_tokens` (the part of the output that is greedy's: up to the
    first rollback, or all of it when there was none).
    `seconds_per_generated_token` is per decoded token.
    """
    import torch
    from transformers import LogitsProcessorList, StoppingCriteriaList

    from labbs2026.thai_marks import runtime

    def decode(ids: list[int]) -> str:
        return processor.decode(ids, skip_special_tokens=True)

    runtime._sync(device)
    started = time.perf_counter()
    inputs = runtime.prompt_inputs(processor, image, prompt, device)
    prepared = time.perf_counter()
    base = int(inputs["input_ids"].shape[-1])
    visual = int((inputs["input_ids"] == model.config.image_token_id).sum().item())
    if str(device).startswith("cuda"):
        torch.cuda.reset_peak_memory_stats(device)
    limit = int(generation["max_new_tokens"])
    state, pieces = EscapeState(), {}
    kept: list[int] = []
    escapes: list[dict[str, Any]] = []
    steps = calls = 0
    final_cut = step_cap_hit = False
    greedy_prefix_chars = greedy_prefix_tokens = None
    while True:
        budget = min(limit - len(kept), max_total_steps - steps)
        if budget <= 0:
            step_cap_hit = steps >= max_total_steps
            break
        watch = _criteria(decode, base, every)
        with torch.inference_mode():
            produced = model.generate(
                **extend_inputs(inputs, kept), **{**generation, "max_new_tokens": budget},
                stopping_criteria=StoppingCriteriaList([watch]),
                logits_processor=LogitsProcessorList([_constraint(decode, base, state, pieces)]))
        calls += 1
        new = produced[0][base + len(kept):].tolist()
        steps += len(new)
        kept += new
        if not watch.fired:
            step_cap_hit = steps >= max_total_steps and len(kept) < limit
            break
        text = decode(kept)
        onset = loop_onset(text, STOP_K, STOP_K_LONG)
        if onset is None:      # the window saw a run the whole text does not hold: cannot happen
            raise RuntimeError("loop watch fired without a run in the output")
        start, unit = onset
        cut = rollback_index(kept, start + unit, decode)
        if greedy_prefix_chars is None:
            greedy_prefix_chars, greedy_prefix_tokens = len(decode(kept[:cut])), cut
        if len(escapes) >= max_escapes:
            kept = kept[:cut]
            final_cut = True
            break
        unit_text = text[start:start + unit]
        state.add(cut, start + unit, unit_text)
        escapes.append({"at_step": steps, "onset_chars": start, "unit_chars": unit, "unit": unit_text,
                        "rollback_tokens": cut, "discarded_tokens": len(kept) - cut})
        kept = kept[:cut]
    runtime._sync(device)
    finished = time.perf_counter()
    output = decode(kept)
    return {
        "raw_output": output,
        "generated_tokens": len(kept),
        "reached_max_new_tokens": len(kept) >= limit,
        "visual_tokens": visual,
        "prompt_tokens": base,
        "seconds_processor": prepared - started,
        "seconds_generate": finished - prepared,
        "seconds_per_generated_token": (finished - prepared) / max(1, steps),
        "peak_bytes": int(torch.cuda.max_memory_allocated(device)) if str(device).startswith("cuda") else None,
        "escapes": escapes, "final_cut": final_cut, "total_steps": steps, "step_cap_hit": step_cap_hit,
        "generate_calls": calls,
        "greedy_prefix_chars": len(output) if greedy_prefix_chars is None else greedy_prefix_chars,
        "greedy_prefix_tokens": len(kept) if greedy_prefix_tokens is None else greedy_prefix_tokens,
    }
