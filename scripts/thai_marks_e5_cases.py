"""Build the E5 synthetic cases (`docs/stage0/E5_SYNTHETIC_OMISSION_DRAFT.md`): pages and line views, deterministic.

Run with matplotlib >= 3.11 (Thai text layout): uv run --with matplotlib python scripts/thai_marks_e5_cases.py --out e5_cases.json
The JSON holds the images (PNG, base64), the references and the factor levels; it is attached to the
Kaggle run as a dataset. No benchmark image or text is involved.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import random
from pathlib import Path

from labbs2026.thai_marks import synthetic_pages as sp
from labbs2026.thai_marks import thai_sentences

FONT = Path("assets/fonts/noto/NotoSansThai-Regular.ttf")
LINE_COUNTS = (4, 10, 18)
FONT_PX = (24, 32, 44)
PAGES_PER_CELL = 6
LINES_PER_PAGE = 3
SEED = 20261012


def _png(image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--text", choices=("words", "sentences"), default="words",
                        help="words: E5 (random dictionary words); sentences: E5b (templated phrases)")
    parser.add_argument("--no-line-views", action="store_true", help="pages only (E5b)")
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; results are never overwritten")
    vocab = sp.vocabulary()
    measure = sp.measurer(str(FONT))
    cases, n_pages = [], 0
    for count in LINE_COUNTS:
        for px in FONT_PX:
            for k in range(PAGES_PER_CELL):
                seed = SEED + 1000 * count + 10 * px + k
                lines = (sp.compose_lines(seed, count, px, vocab, measure) if args.text == "words"
                         else thai_sentences.compose_sentence_lines(seed, count, px, measure))
                page, boxed = sp.render_page(lines, px, str(FONT))
                page_id = f"L{count}-S{px}-{k}"
                base = {"page": page_id, "lines": count, "font_px": px, "seed": seed}
                cases.append({**base, "case": f"{page_id}|page", "kind": "page",
                              "reference": "\n".join(lines), "image_png_b64": _png(page)})
                rng = random.Random(seed)
                for idx in ([] if args.no_line_views else sorted(rng.sample(range(count), LINES_PER_PAGE))):
                    crop, canvas = sp.line_views(page, boxed[idx])
                    for kind, image in (("line_tight", crop), ("line_masked", canvas)):
                        cases.append({**base, "case": f"{page_id}|{kind}|{idx}", "kind": kind,
                                      "line_index": idx, "reference": boxed[idx].text,
                                      "box": list(boxed[idx].box), "image_png_b64": _png(image)})
                n_pages += 1
    payload = {"design": "docs/stage0/E5_SYNTHETIC_OMISSION_DRAFT.md", "seed": SEED, "pages": n_pages,
               "line_counts": LINE_COUNTS, "font_px": FONT_PX, "cases": cases}
    if args.text == "sentences":  # the E5 (words) payload stays byte-identical to the registered one
        payload = {**payload, "design": "docs/stage0/E5B_MEANINGFUL_TEXT_DRAFT.md", "text": args.text}
    text = json.dumps(payload, ensure_ascii=False)
    args.out.write_text(text, encoding="utf-8")
    print({"cases": len(cases), "pages": n_pages, "bytes": len(text.encode("utf-8")),
           "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})


if __name__ == "__main__":
    main()
