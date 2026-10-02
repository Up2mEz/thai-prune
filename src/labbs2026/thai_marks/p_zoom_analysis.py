"""Offline scoring of the P-ZOOM tile reads (`P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md` §3-§4).

Everything here is fixed before any tile output exists. For each selected
reference line (absent lines and control lines, as frozen in
`configs/thai_marks/p_zoom_pages.json`) the question is whether some tile read
of the page contains it:

- `text`: found (`attribution.find_elsewhere`: 8+ characters, CER < 0.2, a
  stretch no other line already claimed) in a tile's extracted text;
- `figure_only`: not found as text, but found in what the tile wrote inside `<figure>`
  blocks, which extraction removes
  (the policy explanation);
- `not_found`: in neither.

Marks of a `text` line are then scored: how many of its reference marks are
read correctly in the matched stretch. The reading of the whole probe (§4) is
`reading()`, a pure function of the totals.
"""

from __future__ import annotations

import collections
import re

from labbs2026.thai_marks.attribution import MARKS, elsewhere_cer, find_elsewhere, reference_lines
from labbs2026.thai_marks.decompose import _fates_from, align_anchored
from labbs2026.thai_marks.extract import extract_text

# §4: "at least 50% of absent marks recovered as text" is the resolution/attention
# reading. "Mostly inside <figure>" is operationalized the same way: figure-only
# lines hold at least half of the absent marks (the draft does not number "mostly").
RECOVERY_THRESHOLD = 0.5
# Added 2026-10-03, before any tile output exists (see the draft's §7): on the same 21 pages the
# existing whole-page `TYPHOON_CARD` read already recovers about half of the absent marks as text,
# so "tiles recover >= 50%" cannot by itself credit zoom. The tile gain over that read must be at
# least this share of the absent marks. The 15 points are a judgement, not derived from data.
GAIN_THRESHOLD = 0.15
OUTCOMES = ("text", "figure_only", "not_found")


_FIGURE = re.compile(r"<figure\b[^>]*>(.*?)(?:</figure>|\Z)", re.DOTALL | re.IGNORECASE)


def figure_text(raw: str) -> str:
    """Only what a tile read wrote inside `<figure>` blocks (an unclosed one runs to the end).

    Matching against this, not against the whole text with figures kept, is what
    makes `figure_only` mean "written inside a figure": text outside figures would
    otherwise be found again and counted twice.
    """
    return extract_text("\n".join(_FIGURE.findall(raw)), keep_figures=True)


def _marks(line: str) -> list[int]:
    return [j for j, ch in enumerate(line) if ch in MARKS]


def _marks_correct(line: str, stretch_text: str) -> int:
    pairs, _, _ = align_anchored(line, stretch_text)
    fates, _ = _fates_from(pairs, line, stretch_text)
    return sum(fates.get(j) == "correct" for j in _marks(line))


def _locate(line: str, texts: list[str], used: list[set]) -> tuple[int, str] | None:
    """The tile whose text holds `line` best, and the matched stretch of that text."""
    best = None
    for tile, text in enumerate(texts):
        kind, stretch = find_elsewhere(line, text, used[tile])
        if kind is None:
            continue
        cer = elsewhere_cer(line, text)
        if best is None or cer < best[0]:
            best = (cer, tile, stretch)
    if best is None:
        return None
    _, tile, stretch = best
    used[tile].update(stretch)  # a stretch of a tile is credited to one line only
    return tile, "".join(texts[tile][i] for i in stretch)


def score_page(raw_reference: str, tile_outputs: list[str], absent: list[int],
               control: list[int]) -> dict:
    """Outcome of every selected line of one page against its tile outputs.

    `absent` and `control` are indices into `reference_lines(raw_reference)`.
    All reference lines are matched, the absent ones last, against one shared claim state
    per tile, so two lines cannot be credited from one stretch of a tile read.
    """
    lines = reference_lines(raw_reference)
    text = [extract_text(raw) for raw in tile_outputs]
    figure = [figure_text(raw) for raw in tile_outputs]
    used_text = [set() for _ in text]
    used_figure = [set() for _ in figure]
    kind_of = {**{i: "absent" for i in absent}, **{i: "control" for i in control}}
    # Every other reference line claims its stretch first, absent lines last: a stretch of a
    # tile that reads some other line (a near-identical caption, a repeated line) must not be
    # credited as the absent line too. This is the page-alignment `used` rule of
    # `attribution.find_elsewhere`, rebuilt for tiles, which cannot be aligned to the page.
    order = [i for i in range(len(lines)) if i not in set(absent)] + sorted(absent)
    rows = []
    for index in order:
        line = lines[index]
        found = _locate(line, text, used_text)
        if index not in kind_of:
            continue
        marks = len(_marks(line))
        row = {"line": index, "group": kind_of[index], "marks": marks, "chars": len(line),
               "outcome": "not_found", "tile": None, "marks_correct": 0}
        if found is not None:
            tile, stretch = found
            row.update(outcome="text", tile=tile, marks_correct=_marks_correct(line, stretch))
        else:
            in_figure = _locate(line, figure, used_figure)
            if in_figure is not None:
                row.update(outcome="figure_only", tile=in_figure[0])
        rows.append(row)
    rows.sort(key=lambda r: r["line"])
    return {"lines": rows}


def chance_rate(pages: list[dict]) -> dict:
    """How often a selected line is 'found' in the tile reads of a different page.

    `pages`: dicts with `reference`, `tile_outputs`, `absent`, `control`. Each page's
    lines are scored against the next page's tile outputs (cyclic); a rate near 0
    means the CER < 0.2 rule does not credit chance matches here.
    """
    if len(pages) < 2:
        return {"lines": 0, "found": 0, "rate": None}
    found = total = 0
    for k, page in enumerate(pages):
        other = pages[(k + 1) % len(pages)]
        scored = score_page(page["reference"], other["tile_outputs"], page["absent"], page["control"])
        total += len(scored["lines"])
        found += sum(r["outcome"] != "not_found" for r in scored["lines"])
    return {"lines": total, "found": found, "rate": found / total if total else None}


def summarize(page_scores: list[dict]) -> dict:
    """Totals per group (`absent`, `control`) over all pages, by outcome."""
    out = {}
    for group in ("absent", "control"):
        rows = [r for p in page_scores for r in p["lines"] if r["group"] == group]
        lines = collections.Counter(r["outcome"] for r in rows)
        marks = collections.Counter()
        for r in rows:
            marks[r["outcome"]] += r["marks"]
        total_marks = sum(r["marks"] for r in rows)
        read_correct = sum(r["marks_correct"] for r in rows if r["outcome"] == "text")
        out[group] = {
            "lines": len(rows), "marks": total_marks,
            "lines_by_outcome": {o: lines[o] for o in OUTCOMES},
            "marks_by_outcome": {o: marks[o] for o in OUTCOMES},
            "share_of_marks": {o: (marks[o] / total_marks if total_marks else None) for o in OUTCOMES},
            "marks_correct_in_text_lines": read_correct,
            "correct_share_of_recovered_marks": (read_correct / marks["text"] if marks["text"] else None),
        }
    return out


def compare_with_baseline(tile_scores: list[dict], baseline_scores: list[dict]) -> dict:
    """Absent-line marks that tiles recover and the zoom-free baseline does not, and the reverse.

    `baseline_scores`: `score_page` of the same pages read whole, same model and prompt
    (the existing T1 `TYPHOON_CARD` full-page reads). Pages and line indices must match.
    """
    gain = loss = total = 0
    if len(tile_scores) != len(baseline_scores):
        raise ValueError("tile and baseline scores cover different pages")
    for tiles, whole in zip(tile_scores, baseline_scores):
        if len(tiles["lines"]) != len(whole["lines"]):
            raise ValueError("tile and baseline scores cover different lines")
        for t, w in zip(tiles["lines"], whole["lines"]):
            if (t["line"], t["group"]) != (w["line"], w["group"]):
                raise ValueError("tile and baseline scores cover different lines")
            if t["group"] != "absent":
                continue
            total += t["marks"]
            gain += t["marks"] * (t["outcome"] == "text" and w["outcome"] != "text")
            loss += t["marks"] * (t["outcome"] != "text" and w["outcome"] == "text")
    baseline = summarize(baseline_scores)
    return {"baseline": baseline, "absent_marks": total,
            "gain_share": gain / total if total else None,
            "loss_share": loss / total if total else None}


def reading(summary: dict, comparison: dict) -> str:
    """§4 with the zoom-free baseline, a pure function of the totals.

    - `resolution_attention_limit`: tiles recover at least `RECOVERY_THRESHOLD` of the
      absent marks as text AND at least `GAIN_THRESHOLD` of them are lines the whole-page
      read of the same prompt did not recover (so the prompt alone does not explain it);
    - `policy`: otherwise, figure-only lines hold at least `RECOVERY_THRESHOLD` of them;
    - `prompt_not_zoom`: tiles reach the recovery threshold, but the whole-page read
      reaches nearly as much (gain under `GAIN_THRESHOLD`): the draft's 50% rule would
      have credited zoom for what `TYPHOON_CARD` alone does;
    - otherwise `beyond_typhoon_at_this_resolution`.
    """
    share = summary["absent"]["share_of_marks"]
    gain = comparison["gain_share"]
    if share["text"] is not None and share["text"] >= RECOVERY_THRESHOLD:
        return ("resolution_attention_limit" if gain is not None and gain >= GAIN_THRESHOLD
                else "prompt_not_zoom")
    if share["figure_only"] is not None and share["figure_only"] >= RECOVERY_THRESHOLD:
        return "policy"
    return "beyond_typhoon_at_this_resolution"


def assemble_pages(records: list[dict], pages: list[dict], tiles: int) -> list[dict]:
    """Group `t4` records by page, tile outputs in tile order.

    Raises unless every frozen page has exactly one record per tile and no record
    belongs to a page outside the frozen list: a partial run must not be scored
    as if it were the registered probe.
    """
    by_page: dict[str, dict[int, dict]] = collections.defaultdict(dict)
    for record in records:
        if record["tile"] in by_page[record["id"]]:
            raise ValueError(f"duplicate record for page {record['id']} tile {record['tile']}")
        by_page[record["id"]][record["tile"]] = record
    frozen = {page["id"] for page in pages}
    if set(by_page) - frozen:
        raise ValueError(f"records for pages outside the frozen list: {sorted(set(by_page) - frozen)}")
    assembled = []
    for page in pages:
        got = by_page.get(page["id"], {})
        if sorted(got) != list(range(tiles)):
            raise ValueError(f"page {page['id']}: tiles {sorted(got)}, expected 0..{tiles - 1}")
        assembled.append({
            "id": page["id"], "reference": got[0]["reference"],
            "tile_outputs": [got[t]["raw_output"] for t in range(tiles)],
            "absent": page["absent_lines"], "control": page["control_lines"],
        })
    return assembled
