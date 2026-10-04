# P-ZOOM — can Typhoon read the text it leaves out of graphics, if it is shown larger?

**Status: `APPROVED` 2026-10-03 for smoke then full run (`DECISION_LOG.md` 2026-10-03d), with the amendment of §7.** Written 2026-10-03. A mechanism probe on
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
387 marks; the 3 placeholder pages are a subset [wrong, found 2026-10-04: 2 of the 3 matching
outputs are in this list]). No locked-split page.

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

## 8. Smoke result and how loops are handled (2026-10-03, before the full run)

Smoke on the secondary account, `--limit 1` (page `048AEF1B`, 4 tiles), run
`kaggle-thai-marks-t4-76165db98ea8-typhoon-smoke1`, git `76165db`: SUCCESS, no failed reads,
checksums verified, fp16, greedy settings as T1 (resolved config in the manifest). Tiles are
599x799 px read at 1349x1799, `zoom_factor` 1.85, 2,352 visual tokens each. 218 s wall for four
reads including 24 s setup. Observed, not a result: two tiles wrote graphics as `<figure>`
descriptions, one tile repeated one word until `max_new_tokens` (3072; 122 s).

**Loops.** A read that reaches `max_new_tokens` is kept as it is and counted
(`reached_max_new_tokens`, reported with the summary). It is not re-run and no loop guard is
added: that would be a second factor in this round, and loop decoding is T5's question. Text
a loop displaces is simply not found; the repeated surplus is not charged because recovery is
scored per reference line, not per output character. The consequence is that recovery is a
lower bound wherever tiles loop, and the reading must say so.

**Cost.** At the smoke's rate (about 25 s for an ordinary tile, 120 s for a looped one) the 84
reads take about 1 to 1.5 GPU-hours on one T4 session, inside the 2-hour limit of
`DECISION_LOG.md` 2026-10-03d.

## 9. Result (2026-10-03)

Run `kaggle-thai-marks-t4-0b2d191e31c5-typhoon` (git `0b2d191`, main account, kernel
`labbs2026-thai-marks-pzoom`): 84 reads, no failed read, checksums verified, fp16, greedy as T1,
33 min wall = 0.55 GPU-hours, 45,609 tokens generated, 3 reads reached `max_new_tokens`, 47
reads contain a `<figure>`. Scored by `scripts/thai_marks_pzoom_analyze.py` with the thresholds
of §4 and §7, fixed before the run. Calibration split, Typhoon only,
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

**Registered measures (absent lines: 71 lines, 387 marks):**

| | lines | marks | share of marks |
|---|---|---|---|
| found as text in a tile | 28 | 185 | **47.8%** |
| found only inside `<figure>` | 14 | 49 | 12.7% |
| not found | 29 | 153 | 39.5% |
| whole page, `TYPHOON_CARD`, no zoom (baseline) | 24 text [corrected 2026-10-04, was 31: that was its not-found count] | 196 text | 50.6% text |

Marks of recovered lines read correctly: 100% (absent), 96% (control). Tiles recover 87 marks
(22.5%) the whole-page read does not, and lose 98 marks (25.3%) it reads. Chance level: 1 of 113
lines. Scorer check on the `BENCHMARK_QUESTION` page read: 6.7% of absent marks, 98.7% of control.

**Reading by the rule fixed in advance: `beyond_typhoon_at_this_resolution`.** Tiles reach 47.8%,
under the 50% line; figure-only lines hold 12.7%, far under the policy line. By that rule P-ZOOM
stops: no graphics-aware re-read is registered. [See §10: the label is applied as written, but it
overstates what the data show.]

**What this does and does not show.**

- The 47.8% is 2.2 points under the line, 11 marks less than the whole-page read's 196 [corrected
  2026-10-04, was 5]. One line would flip it (§10). The rule was fixed to be applied as written; it should not be read as
  a clean "no".
- Tiles carry only 40.2% of the control *marks* as text (25 of 42 control lines, 59.5%; ceiling
  96.9% of marks on the whole page) [wording corrected 2026-10-04: 40.2% is mark-weighted, not a
  per-line rate]. The 2×2 grid cuts wide lines in two, and `find_elsewhere` needs the whole
  line in one tile. *Post hoc:* control lines not found have median length 96 characters, found
  ones 32. Absent lines are short and their length does not separate found (median 23) from not
  found (26). [Retracted 2026-10-04: the original sentence here concluded that the cut does not
  explain the absent misses; a line-length median does not answer a mark-weighted question, see
  §10.] The tile step does lose ordinary text, as §3's control was meant to show.
- Loops do not explain it (3 of 84 reads; absent recovery 48.3% on pages with a looped tile,
  47.6% on the others).
- *Post hoc, not registered:* the union of the whole-page read and the tiles holds 73.1% of the
  absent marks as text (50.6% + 22.5%). Gains and losses are of similar size (22.5% and 25.3%);
  part of both is sensitivity of the read to any change of the image, which one read per
  condition cannot separate from the effect of zoom. [Corrected 2026-10-04: this said
  "read-to-read variability of one greedy decode". Repeating an identical input reproduced the
  stored output byte for byte on the 2 pages of the P-ZOOM-3 smoke (I checked) and, a reviewer says,
  on an earlier replicate (4 of 4, not re-checked), so decode noise may be near zero; P-ZOOM-3's `repeat` view measures it on 21 pages.]
- Zoom is therefore neither shown to reveal the text nor ruled out as a way to add some of it.
  What the data support is narrower than first written (§10): the pooled tile share of the lines
  Typhoon left out of the page read is 47.8%, 12.7% of those marks go into `<figure>` descriptions
  instead of text, and the data cannot tell 47.8% from 50%.

## 10. Errata and independent review (2026-10-04)

An independent review (four reviewers, `wf_9f91ee64-a6b`; three finished before a session limit
stopped the rest) recomputed every headline number of §9 from the raw records: 47.8%, 12.7%, 39.5%,
50.6%, gain 22.5% (87 marks), loss 25.3% (98 marks), control 40.2%, union 73.1%, 1 of 113 chance,
loops 48.3% / 47.6% all reproduce. It found three wrong figures in my write-up (corrected in place
above, marked) and the following problems with what the numbers were taken to mean. None is
resolved by the data in hand; each is carried into `P_ZOOM3_CONTROLS_DRAFT.md`.

- **One line decides the registered reading.** Line 60 of page `8F33EBB9` (282 characters, 49
  marks, 12.7% of all absent marks and half of the 98 lost marks) is found by the whole-page read and
  sits in a tile at `elsewhere_cer` 0.28, just over the inherited 0.2 cutoff, so it scores
  `not_found`. Scored as found, tiles reach 60.5% and the rule returns `resolution_attention_limit`.
  With the cutoff at 0.25 the label also flips; chance stays at 1 of 113 at 0.30. A page-bootstrap
  gives the tile share a standard deviation of about 12 points; P(share ≥ 50%) is about 43%. The
  claim above that the seam cut does not explain the absent misses is therefore retracted: the cut
  is plausibly why that long line fails.
- **The label overstates.** `beyond_typhoon_at_this_resolution` is the fall-through of a rule that
  has no branch for "the whole-page read already recovers most of it". The baseline recovers 50.6%
  without zoom, so most of these marks are within Typhoon's reach at page scale under
  `TYPHOON_CARD`. "P-ZOOM stops" means only that no re-read method is registered on this evidence;
  it is not a finding that the text is unreadable.
- **The gain criterion is gross, not net.** Gain (87 marks) is the lines tiles recover and the
  whole-page read does not; it ignores the 98 marks lost. Under exchangeability two reads of the same
  process would show about equal gain and loss, here (22.5% + 25.3%) / 2. A gain of 15 points has
  no null calibration. A third of the gain is also figure-wrapper changes, not newly found text.
- **The 387 marks are not only graphics.** They are every line with marks that
  `whole_line_causes` called `line_missing`: infographic text, but also mastheads, an advertising
  inset and two body paragraphs (`TYPHOON_FAILURE_PROFILE.md` §2d). "Text it leaves out of
  graphics" in §1 and §9 is an inference, and the subgroup split promised in `DECISION_LOG.md`
  2026-10-03 was not made.
- **The baseline is a past read.** The T1 outputs came from an earlier run whose resolved
  decoding was not logged. Differences between a view and the baseline are "a change of input plus a
  change of run".
- **Scope.** 21 pages, 71 lines. Mark-weighted pooling lets a few long lines dominate; the sign of
  the net effect changes with the unit.

### 10b. Findings of the second review (2026-10-04), each re-checked by a skeptic

The second review's findings were then each given to one skeptic told to reproduce or refute it
(`wf_6607262d-c34`, eight verdicts, all confirmed; the skeptics were barred from the P-ZOOM-2/-3 full
runs). On the first P-ZOOM run's data, exploratory and not registered:

- **The 2x2 grid's vertical seam makes the registered label an artifact (high).** `find_elsewhere`
  credits a line only if it sits whole in one tile. Four absent lines (26 marks) read exactly or
  almost exactly in two adjacent tiles, each half in one, are scored `not_found`
  (`8F33EBB9`:0, `F1D97B10`:1, `6BA97DBE`:0, `9BBB9DB3`:4; the last needs a CER of 0.065, not 0.06).
  Crediting them: tiles 47.8% → 54.5% as text (52.5% on the three strictest), gain 22.5% → 24.0%,
  loss 98 → 78 marks, and the rule returns `resolution_attention_limit`. The margin is 9 marks;
  `8F33EBB9`:0 alone supplies 12. The same seam search finds 0 of 113 lines on other pages (not
  chance). It recovers only 72 of the 324 missing control marks (a quarter of that gap; the rest
  are long multi-row paragraphs). The 2x2 geometry itself leaves an overlap strip of about 8% of the
  page width, not 15%, so a line spanning the strip is whole in neither tile.
  **Net: P-ZOOM's first run supports neither label. The registered
  `beyond_typhoon_at_this_resolution` and the seam-credited `resolution_attention_limit` both
  depend on an instrument choice, and "P-ZOOM stops" rested on the first.** The full-width bands
  of P-ZOOM-2/-3 have no vertical seam, so this does not reach them.
- **Claim order (low).** The mechanism is real (a kept near-twin line can claim an absent line's
  stretch) but moved 0 marks net on the first run; at most 4 marks were claim-blocked, both
  legitimate twin blocks. The review's "187 vs 185" is an artifact of its alternative ordering. A
  latent exposure for P-ZOOM-2 is one 22-mark line (`C065E1E9`:44, "รูปที่ 10" next to "รูปที่ 9"),
  about 28 marks (7.2 points) with a second pair.
- **Overlap strips crediting one physical line twice (low).** 1 mark (0.26 points) on the first
  run, not the 5 first claimed.
- **Short verbatim lines credited from running text no other line claimed (low).** Inflates tile
  text by 4 to 7 marks (1.0 to 1.8 points) on the first run; the registered reading is unchanged.
- **Figure claims (low).** Non-selected lines do not compete for `<figure>` stretches: figure-only
  falls 49 → 34 marks, 12.7% → 8.8%, one line (`95979273`:11); text outcomes unchanged.
- **Nested `<figure>` (low).** Real nested figures: 0 of 440 reads; latent only.
- **fp16 on the bands (low).** No non-finite or degenerate read in any unblinded fp16 run; the
  worst case is a ceiling on a risk with no support. The review's remark that the 80% floor would
  catch it is wrong for the controlled reading: the floor there is computed on `bands100`.
- **Decode noise (low).** Identical inputs reproduced the stored output on 4 of 4 (smoke replicate)
  and 2 of 2 reads (the P-ZOOM-3 repeat-vs-T1 smoke), so run-to-run noise looks near zero; drift of
  the stack since T1 is unmeasured, not observed.
- **The log's wording of the amended rule was loose.** `DECISION_LOG.md` 2026-10-03d and -e said
  "+15 points over that baseline". The rule is gross: tiles ≥ 50% as text **and** a gain of ≥ 15
  points, where gain ignores lost marks. Tiles could meet it with no net advantage; the entries now
  say so.
