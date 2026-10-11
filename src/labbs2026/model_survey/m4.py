"""MODEL_SURVEY_M4 — can Wayu's own confidence tell the text it read after a loop escape from text it invented?

M3's escape (`model_survey.escape`) read some of what Wayu's loops left unread
(+23 matched reference lines on Full-page; one page in full), but it also
wrote fluent text that is not on the page, so mark F1 did not move. M4 asks,
offline, whether Wayu's confidence in its own escaped text separates the two.
If it does, a filter can keep the reading and drop the invention.

**Scores.** One teacher-forced forward pass per M3 output: prompt and image,
then the output re-tokenized. For each token: its log-probability and the
entropy of the distribution. No new generation.

**Units.** Wayu's outputs carry no line breaks, so the unit is a *window*:
whitespace-separated phrases merged left to right until a window holds at
least `min_chars` non-space characters (a short remainder joins the window
before it). A window's scores are over the tokens overlapping it:
`s_mean` (mean log-probability, primary), `s_min` (lowest), `s_ent`
(mean entropy).

**Labels (Full-page only).** A window with a letter is `read` if its text
can be located in the page's reference at CER < `max_cer` (the window is
aligned whole against the best-matching stretch of the reference), otherwise
`invented`. On Text recognition the reference is often one part of a larger
image that Wayu transcribes whole, so "not in the reference" does not mean
"invented"; no labels there.

**Filter (fixed without labels).** The threshold is a low quantile of
`s_mean` over the windows of Wayu's ordinary text: outputs with no escape that
ended before `max_new_tokens`. After an escape, a window scoring below it is
dropped; the greedy prefix is never touched.
"""

from __future__ import annotations

import random
import re
from typing import Any, Sequence

from labbs2026.thai_marks.decompose import align_anchored, edit_distance_from
from labbs2026.thai_marks.extract import extract_text

LETTER = re.compile(r"[A-Za-zก-ฮ]")        # a Thai consonant or a Latin letter (as loop_cut)
_SPACE = re.compile(r"\s+")


def _squash(text: str) -> str:
    return _SPACE.sub(" ", text).strip()


def windows(text: str, start: int, end: int, min_chars: int) -> list[tuple[int, int]]:
    """`text[start:end]` cut into windows of whitespace-separated phrases, each >= `min_chars` non-space characters.

    Spans are (start, end) positions in `text`, phrases kept whole; a final
    remainder below `min_chars` joins the window before it (or stands alone if
    it is the only one).
    """
    phrases = [(start + m.start(), start + m.end()) for m in re.finditer(r"\S+", text[start:end])]
    out: list[list[int]] = []
    current: list[int] | None = None
    size = 0
    for a, b in phrases:
        if current is None:
            current, size = [a, b], 0
        current[1] = b
        size += b - a
        if size >= min_chars:
            out.append(current)
            current = None
    if current is not None:
        if out:
            out[-1][1] = current[1]
        else:
            out.append(current)
    return [(a, b) for a, b in out]


def window_scores(spans: Sequence[tuple[int, int]], offsets: Sequence[Sequence[int]],
                  logprobs: Sequence[float], entropies: Sequence[float]) -> list[dict[str, Any]]:
    """`s_mean`, `s_min`, `s_ent` and the token count of each window, over the tokens overlapping it."""
    out = []
    for a, b in spans:
        idx = [k for k, (s, e) in enumerate(offsets) if s < b and e > a]
        if not idx:
            out.append({"start": a, "end": b, "n_tokens": 0, "s_mean": None, "s_min": None, "s_ent": None})
            continue
        lp = [logprobs[k] for k in idx]
        out.append({"start": a, "end": b, "n_tokens": len(idx), "s_mean": sum(lp) / len(lp), "s_min": min(lp),
                    "s_ent": sum(entropies[k] for k in idx) / len(idx)})
    return out


def label(window_text: str, reference: str, max_cer: float) -> tuple[str, float | None]:
    """`read`, `invented` or `no_letter`, and the window's CER at its best place in the reference."""
    text = _squash(window_text)
    if not LETTER.search(text):
        return "no_letter", None
    ref = _squash(extract_text(reference))
    if not ref:
        return "invented", 1.0
    pairs, _, _ = align_anchored(text, ref)
    cer = edit_distance_from(pairs, text, ref) / len(text)
    return ("read" if cer < max_cer else "invented"), cer


def auroc(positive: Sequence[float], negative: Sequence[float]) -> float | None:
    """P(a positive scores above a negative), ties counted half (Mann-Whitney)."""
    if not positive or not negative:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in positive for n in negative)
    return wins / (len(positive) * len(negative))


def item_bootstrap_auroc(by_item: dict[str, list[tuple[float, bool]]], *, resamples: int,
                         seed: int) -> dict[str, Any]:
    """AUROC over all items' (score, is_positive) pairs, with a 95% interval resampling items."""
    def compute(ids: list[str]) -> float | None:
        rows = [x for i in ids for x in by_item[i]]
        return auroc([s for s, y in rows if y], [s for s, y in rows if not y])

    ids = sorted(by_item)
    rng = random.Random(seed)
    draws = sorted(d for d in (compute([rng.choice(ids) for _ in ids]) for _ in range(resamples)) if d is not None)
    rows = [x for i in ids for x in by_item[i]]
    return {"items": len(ids), "positive": sum(y for _, y in rows), "negative": sum(not y for _, y in rows),
            "auroc": compute(ids),
            "ci95": [draws[int(0.025 * len(draws))], draws[min(len(draws) - 1, int(0.975 * len(draws)))]]
            if draws else None, "valid_resamples": len(draws)}


def quantile(values: Sequence[float], q: float) -> float:
    """The `q` quantile by linear interpolation between order statistics."""
    data = sorted(values)
    if not data:
        raise ValueError("no values")
    pos = q * (len(data) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(data) - 1)
    return data[lo] + (data[hi] - data[lo]) * (pos - lo)


def filtered_output(text: str, prefix_chars: int, scored: Sequence[dict[str, Any]], tau: float) -> str:
    """The greedy prefix, then the post-escape windows whose `s_mean` is at least `tau`.

    Text between kept windows is kept as written; where a window was dropped,
    one space joins what is left.
    """
    out, last = text[:prefix_chars], prefix_chars
    for w in scored:
        if w["s_mean"] is None or w["s_mean"] < tau:
            continue
        gap = text[last:w["start"]]
        out += (gap + text[w["start"]:w["end"]]) if not gap.strip() else (" " + text[w["start"]:w["end"]])
        last = w["end"]
    return out


def validate(config: dict[str, Any]) -> list[list[tuple[str, int, int]]]:
    """Check the scoring pass, the analysis settings and the budget; return the GPU queues (unit, shard, shards)."""
    a = config["analysis"]
    if int(a["window_min_chars"]) < 1 or not 0 < float(a["label_max_cer"]) < 1:
        raise ValueError("analysis.window_min_chars must be >= 1 and label_max_cer in (0, 1)")
    if not 0 < float(a["threshold_quantile"]) < 1 or not 0 < float(a["agreement_floor"]) <= 1:
        raise ValueError("analysis.threshold_quantile must be in (0, 1) and agreement_floor in (0, 1]")
    if a["primary_score"] not in ("s_mean", "s_min", "s_ent"):
        raise ValueError("analysis.primary_score must be s_mean, s_min or s_ent")
    if a["label_task"] not in config["benchmark"]["tasks"]:
        raise ValueError("analysis.label_task must be one of the benchmark's tasks")
    if int(config["scoring_pass"]["chunk"]) < 1:
        raise ValueError("scoring_pass.chunk must be >= 1")
    shards = int(config["shards"])
    if shards < 1:
        raise ValueError("shards must be >= 1")
    return [[("score", k, shards)] for k in range(shards)]


def m4_commands(queues: list[list[tuple[str, int, int]]]) -> list[list[dict[str, Any]]]:
    """The worker's unit commands, one per shard."""
    from labbs2026.model_survey.plan import unit_command

    return [[unit_command("labbs2026.model_survey.remote_m4", f"m4_{name}_shard-{k}-of-{n}",
                          ["--shard", k, "--shards", n]) for name, k, n in queue] for queue in queues]
