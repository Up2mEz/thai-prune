# P-ZOOM-3 — controls that let the P-ZOOM-2 views be read as zoom or as something else

**Status: `APPROVED` 2026-10-04 (`DECISION_LOG.md` 2026-10-04b), by the assistant within the pzoom budget; reversible.**
Written 2026-10-04, **before any P-ZOOM-2 or P-ZOOM-3 tile output was read** (see §6 for exactly what
had been seen). Typhoon only, calibration split, 21 pages. It evaluates no method.

## 1. Why a third round

An independent review of the code, the analysis and the write-ups (four reviewers, workflow run
`wf_9f91ee64-a6b`; three finished) recomputed P-ZOOM's numbers exactly and then found that the
P-ZOOM-2 design cannot be read as a test of zoom (details and the P-ZOOM errata are in
`P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md` §10; I re-ran the cutoff check myself and reproduced it):

1. **Bands change more than zoom.** P-ZOOM-2's `bands` are cropped *and* read at 1.85× *and* are
   wider than the 1,800 px the model was trained at (19 of 21 pages). `pad` and `scale90` are
   near-copies of the whole-page read. `Z − N` therefore measures how decorrelated the band read is
   from the baseline, not what zoom adds. Rule 2 of P-ZOOM-2 (`zoom_adds_beyond_perturbation`) can
   fire for a view that recovers *fewer* absent marks than the baseline.
2. **The baseline is a past read.** The T1 outputs came from an earlier run whose resolved decoding
   was not logged. A difference from it is "a change of input plus a change of run". No run has
   repeated an input unchanged, so run-to-run drift of the stack is unmeasured.
3. **Gain is gross.** It ignores lost marks, has no null calibration, and is dominated by a few long
   lines; P-ZOOM's own reading flips when one line's cutoff moves (0.20 → 0.25).

## 2. Reads (Typhoon, `TYPHOON_CARD`, greedy as T1, same 21 pages, fp16): 84

| view | image fed | purpose |
|---|---|---|
| `repeat` | the T1 whole-page input unchanged (`resize_policy`) | noise floor: same image as the stored T1 read; any difference is drift of the stack |
| `bands100` | P-ZOOM-2's 3 full-width bands, 15% overlap, same crops, read at page scale (zoom 1.0) | crop without zoom |

Together with P-ZOOM-2's `bands` (zoom 1.85), the pair `bands` − `bands100` differs in **one**
thing: the scale at which the same crops are read. `bands100` width is that of the page read (at most
1,800 px), inside the model's trained size.

## 3. Measures, fixed before any output is read (`p_zoom2_analysis.analyze_controlled`)

Lines and scorer as P-ZOOM §3 and §7, at the registered cutoff `READ_ELSEWHERE_CER = 0.2`.

- **Stack check**: pages whose `repeat` output equals the stored T1 output byte for byte, of 21.
  Also the churn of `repeat` against the baseline (marks of absent lines on the other side of
  `text`).
- **Text share** of absent marks per view, **net** against the baseline, and the **churn**, each
  with a 95% interval from a paired bootstrap over the 21 pages (seed 20261004, 2,000 resamples).
- **Zoom effect** `D` = text share of `bands` − text share of `bands100`, with its bootstrap
  interval.
- **Crop effect** = text share of `bands100` − baseline (reported, no rule).
- **Control**: share of control marks `bands100` finds as text.
- **Read anywhere and figure share** (added 2026-10-04 before any output was opened, after a
  review noted that enlarging a chart can change whether Typhoon transcribes or describes it):
  the contrast `bands` − `bands100` on text-or-figure and on figure only, each with its interval;
  `text_gain_is_markup_shift` is true when `D ≥ 10` points but the read-anywhere contrast is
  under 5 points (text gained mostly where figures were lost). It qualifies a `zoom_helps`;
  it does not change the label.
- **Stack of the two reads** (added likewise): `bands` comes from the P-ZOOM-2 session (git
  `6a7840f`) and `bands100`, `repeat` from the P-ZOOM-3 session (git `deea2ee`), so `D` subtracts
  reads from two Kaggle sessions. The manifests' model revision, dtype, torch, transformers,
  CUDA device and resolved generation config must be equal across them, else `stack_differs`; the
  same signature of the T1 manifest is reported, not gating.
- **Visual-token check**: for every read, recorded visual tokens against
  `round(h/32) × round(w/32)` of the size read; a mismatch would mean the processor resized it.
- **Interval half-width of `D`**, to be quoted with every `D`.
- **Sensitivity** (reported, never used for a label): `D`, its interval, the read-anywhere contrast
  and the baseline share at cutoffs 0.15, 0.25, 0.30, and with other reference lines not claiming
  stretches first (`claim_other_lines=False`).
- Also reported: P-ZOOM-2's registered `analyze()` output unchanged (`N`, `Z`, `Z − N`, union
  shares, its reading), reads that reach `max_new_tokens`, tokens, visual tokens, seconds.

## 4. Readings, fixed in advance (`controlled_reading`, `analyze_controlled`)

Thresholds are judgements (10 points = 39 marks, which one 49-mark line can supply; 80% control
floor; 18 of 21 pages), not derived from data.

1. **Stack.** `repeat` identical to T1 on ≥ 18 of 21 pages ⇒ `baseline_reproduced`: the stored
   baseline can be used as a reference read. Otherwise `stack_drift`: every difference from T1 in
   P-ZOOM and P-ZOOM-2 mixes input and run; read them against the churn of `repeat`, and the
   stored baseline is not a clean reference.
2. **Instrument.** `bands100` finds < 80% of control marks ⇒ `instrument_fails_control`; no zoom
   reading is made. If the two sessions' stack signatures differ ⇒ `stack_differs`; no zoom reading.
3. **Zoom effect on the same crops.**
   - `zoom_helps`: `D ≥ +10` points and the 95% interval lies above 0;
   - `zoom_hurts`: `D ≤ −10` points and the interval lies below 0;
   - `zoom_not_distinguishable`: otherwise. This is **inconclusive**, not "zoom does nothing": with
     21 pages the interval is wide, and a difference smaller than about its half-width cannot be
     told from zero. Every `D` is quoted with that half-width.

P-ZOOM-2's rule (`reading()`) is computed and reported as registered, but any statement about zoom
uses the label above. Consequences, each a *next draft*, never a run: `zoom_helps` ⇒ a registered
re-read with order-free v2 precision charged, and a replication at a larger sample; `zoom_hurts` ⇒
the bands' extra scale or width is harmful for this model, which says nothing yet about
zoom within the trained size; `zoom_not_distinguishable` ⇒ no conclusion either way. The union rows
of P-ZOOM-2 are descriptive: any extra read raises a union, so they support no lever without a
same-read-count comparison.

## 5. Limits that stay whatever the outcome

21 pages, 71 absent lines, 387 marks, Typhoon only, `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. The 387
marks are not all graphics (`P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md` §10). A statement about zoom is a
statement about these crops at this scale for this model, not about zoom in general. The scale of
`bands` is 1.85×, beyond the model's trained width: if `bands` loses to `bands100` that may be the
out-of-distribution size rather than zoom as such. Input-resolution change only; no visual-token
pruning or merging is involved.

## 6. What had been seen before this was written (disclosure)

- P-ZOOM's own outputs and all of §9's numbers.
- The first 70 characters of each of the 10 reads of the P-ZOOM-2 smoke (2 pages), the
  per-read sizes, tokens, seconds and `<figure>` counts. No scoring.
- Of the full P-ZOOM-2 run: integrity only (checksums, 105 records, no failed read, 1.02 GPU-hours)
  and, after the review, per-read metadata (image size read, visual tokens: they match the prediction
  on all 105 reads). No output text opened, nothing scored.
- The P-ZOOM-3 smoke (2 pages, 8 reads): sizes, tokens and seconds, and that the `repeat` output
  equals the stored T1 output byte for byte on both pages. Nothing else.
- The review's findings (below, §8), including that the 2x2 grid's vertical seam makes P-ZOOM's
  label an instrument artifact; bands are full width, so `bands` and `bands100` share no seam.

## 7. Cost

84 reads: `repeat` is 21 whole-page reads (T1: 48 s median each), `bands100` 63 band reads at page
scale (shorter than the zoomed bands). Estimated 0.5 to 0.7 GPU-hours. P-ZOOM used 0.55 and P-ZOOM-2
1.02 of this week's 3-hour pzoom budget; this round brings it to about 2.2. The smoke runs on the
secondary account first.

## 8. Review findings that shaped this draft, and what was left alone

From the second review (`wf_9f91ee64-a6b`), each then given to one skeptic (`wf_6607262d-c34`;
eight verdicts, all confirmed, the skeptics barred from the two full runs). Numbers and details are
in `P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md` §10b. In short, for the contrast `D` of this round:

- The seam artifact (high) hits P-ZOOM's 2x2 grid only; `bands` and `bands100` are full width and
  share their crops, so a vertical seam is in neither.
- Claim order, overlap double credit, short verbatim credit, figure claims and nested figures are
  low: each moves a share by at most a few points on the first run, and affects `bands` and
  `bands100` alike, so they largely cancel in `D`. They are why `D` is quoted with an interval and
  why the sensitivity variants are reported.
- Re-checked by me: 8 of the 71 absent lines (9 marks) are shorter than the 8 characters
  `find_elsewhere` needs, so they are always `not_found`; marks per line are very skewed; visual
  tokens equal `round(h/32) × round(w/32)` on all reads of P-ZOOM-2 and P-ZOOM-3; the "3 placeholder
  pages are a subset of the 21" statement of P-ZOOM §2 is wrong (2 of 3).
- *Left as registered:* the scorer (changing it now would split P-ZOOM's registered numbers from
  these); the sensitivity variants above are reported instead.
