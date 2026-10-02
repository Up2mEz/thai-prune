# P-ZOOM — can Typhoon read the text it leaves out of graphics, if it is shown larger?

**Status: `DRAFT`, not authorized.** Written 2026-10-03. A mechanism probe on
the calibration split, Typhoon only (one new factor per round). It evaluates
no method and supports no claim beyond "the text is / is not readable by
Typhoon when enlarged".

## 1. Why this, for Typhoon

- On full pages, order-free (`ORDER_FREE_MARK_METRIC_DRAFT.md` §7), Typhoon
  misses 3.9% (BQ) / 5.5% (TC) of reference marks. Mark misreads are 1.5% of
  marks, and T2 found ~1.3 points of mark-level headroom inside text Typhoon
  produces: re-scoring marks cannot close the gap.
- Whole lines absent are 2.3% of marks (BQ) and concentrate in graphics
  (`TYPHOON_FAILURE_PROFILE.md` §2d). On the 3 calibration pages where
  Typhoon (BQ) wrote an image placeholder, **26% of their marks are absent**
  (166 marks; 1.0% of all calibration marks).
- Typhoon's own report names infographics its weakest category (ROUGE-L
  0.527 vs Gemini 2.5 Pro 0.677; arXiv 2601.14722, Table 4).
- T3: at a skipped graphics line the image barely supports the line (+1 to +2
  nats, against −9 to −10 at ordinary transitions): the evidence does not
  reach the decision at page scale.
- On Text recognition crops, Typhoon with its own prompt gets 96.5% of marks
  right: it reads small regions well when they are the whole input.
- Enlarging the region a VLM must read is a known training-free lever for
  small details (Zhang et al., ICLR 2025, "MLLMs Know Where to Look").

Two explanations remain, with different consequences:

- **Resolution/attention limit**: shown larger, Typhoon reads the text. A
  graphics-aware re-read (locate graphic regions, read them enlarged, insert
  at the placeholder) is then worth building.
- **Policy**: Typhoon was trained to describe figures (`<figure>`), not to
  transcribe them, and does so on a crop too. Then the fix is a prompt or
  routing question, or beyond training-free reach.

## 2. Probe

Pages: the calibration Full-page pages on which Typhoon (BQ) left a line with
Thai marks absent (`whole_line_causes == "line_missing"`; 21 pages, 71 lines,
387 marks; the 3 placeholder pages are a subset). No locked-split page.

Inputs per page, fixed before the run: the page split into a 2×2 grid of
tiles with 15% overlap, each tile read at the processor's normal pixel budget
(so text is ~2× larger in tokens than on the page). Typhoon at the pinned
revision, greedy, `TYPHOON_CARD` prompt (its own contract), same generation
settings as T1, recorded in the manifest. 21 × 4 = 84 reads.

## 3. Measures, fixed before the run

- For every absent line: is it found in any tile read
  (`attribution.find_elsewhere`, ≥ 8 characters, CER < 0.2)? Share of
  absent lines and of their marks recovered; marks of recovered lines read
  correctly.
- Same for a control set: lines Typhoon *did* read on the page (sampled 2 per
  page, seeded 20261003), to see whether tiling also loses text.
- How often tile reads put the absent text inside `<figure>` (removed by
  extraction) instead of as text: the policy explanation.

## 4. Readings fixed in advance

- **≥ 50% of absent marks recovered as text**: resolution/attention limit;
  next is a registered method (graphic-region localization + enlarged
  re-read + insertion), scored with order-free v2 mark P/R/F1 so surplus text
  is charged.
- **Mostly inside `<figure>` on tiles too**: policy; next is a prompt for
  crops, or the question is left to the Typhoon team.
- **Neither**: the text is beyond Typhoon at this resolution; P-ZOOM stops.

## 5. Cost

84 tile reads plus model load, one T4 session, under 2 GPU-hours. New code:
tiling in `src/` with tests; the worker gains a `t4` test reading image
variants. Infrastructure change, so the smoke runs on the secondary account
first.

## 6. Implementation choices made while building it (2026-10-03, still DRAFT)

The draft left these open; each is fixed here before any output exists.

- **Tile geometry.** `tiling.tile_boxes`: equal tiles, side `ceil(length / (2 − 0.15))`,
  neighbours overlapping by 15% of a tile; tiles cut from the source pixels, then
  read through the unchanged `runtime.resize_policy` (long side 1800 px). A source
  pixel is therefore about 1.85× larger than at page scale (`tiling.zoom_factor`,
  recorded on every read), not exactly 2×. The number of visual tokens per read stays
  about the same: this is an input-resolution change, not a token-count change.
- **Pages.** `scripts/thai_marks_pzoom_select.py` froze them from Typhoon's T1 records into
  `configs/thai_marks/p_zoom_pages.json` (sha256 in `p_zoom.yaml`): 21 pages, 71 absent
  lines, 387 marks — the draft's counts, reproduced. Lines are stored as indices into
  `attribution.reference_lines`, never as text. The worker refuses a page outside the
  calibration split.
- **Control lines (§3).** A line Typhoon's output kept (cause `None`), of 8+ characters
  (`find_elsewhere` cannot find shorter ones) and carrying at least one Thai mark; two per
  page, ranked by `sha256("20261003:<id>:<index>")`. 42 lines.
- **Prompt and generation.** `TYPHOON_CARD`; the generation kwargs of `t1` (greedy,
  `max_new_tokens` 3072), recorded in the manifest like T1. fp16, as T1.
- **Guards.** `t4` runs Typhoon only, refuses the other session's default kernel slug, and
  `--submit` is refused while `p_zoom.yaml` is not `APPROVED`.
- **Not built yet.** The offline scorer for the §3 measures. It must be written, with tests,
  before the first output is read, so that the readings in §4 stay fixed in advance.

## 7. Scorer, and a gap in §4 found before any tile output (2026-10-03)

The scorer is `src/labbs2026/thai_marks/p_zoom_analysis.py` (tests included), run by
`scripts/thai_marks_pzoom_analyze.py`. Per selected line: `text` (found in a tile's extracted
text by `attribution.find_elsewhere`), `figure_only` (found only in what a tile wrote inside
`<figure>`), `not_found`. All other reference lines claim their stretch of a tile first, absent
lines last, so a stretch that reads another line (near-identical captions, repeated lines) is
not credited twice — the rule `attribution` applies with the page alignment, rebuilt for tiles.

**Checks on real data, run offline on Typhoon's existing full-page outputs scored as one "tile":**

| output scored | absent marks as text | control marks as text |
|---|---|---|
| `BENCHMARK_QUESTION` full page (selected them as absent) | 6.7% (2 of 71 lines) | 98.7% (40 of 42) |
| `TYPHOON_CARD` full page | **50.6%** (24 lines), 16.5% inside `<figure>` | 96.9% |

Chance level (lines scored against another page's reads): 1 of 113 lines. Before the claim
rule, the first row was 24.8% instead of 6.7%: lines read twice were credited twice.

**The gap.** The tiles use `TYPHOON_CARD`, but the absent lines were selected on the
`BENCHMARK_QUESTION` read. On the same 21 pages, the whole-page `TYPHOON_CARD` read — no
zoom — already recovers half of the absent marks as text. §4's "≥ 50% recovered ⇒
resolution/attention limit" would therefore fire without any zoom, crediting the tile step for
what the prompt does. This is the draft's reading rule failing its own purpose, caught
because the baseline exists in T1 and costs no GPU.

**Reading rule, amended before any tile output (the researcher can reverse it):**

- baseline = the same pages read whole with `TYPHOON_CARD` (T1 records, same model revision and
  generation settings), scored identically;
- `resolution_attention_limit` needs tiles ≥ 50% of absent marks as text **and** a gain of at
  least 15 points over that baseline (marks of lines tiles recover and the whole-page read does
  not, as a share of absent marks); the 15 points are a judgement, not derived from data;
- tiles ≥ 50% but gain < 15 points ⇒ `prompt_not_zoom`: the prompt, not the zoom, did it;
- else `policy` if figure-only lines hold ≥ 50% of absent marks, else
  `beyond_typhoon_at_this_resolution`.

The three measures of §3 are reported unchanged, plus the gain and loss against the baseline and
the scorer check above. Control lines are lost-or-kept by tiling as §3 says; their ceiling is
the 96.9–98.7% above, not 100%.
