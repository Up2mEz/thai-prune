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
