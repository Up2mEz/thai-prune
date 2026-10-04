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

## 9. Result (2026-10-04)

Runs: P-ZOOM-2 `kaggle-thai-marks-t6-6a7840fe40d4-typhoon` (105 reads, 1.02 GPU-hours) and P-ZOOM-3
`kaggle-thai-marks-t6-deea2ee8846f-typhoon` (84 reads, 0.73 GPU-hours), main account, no failed
read, checksums verified, fp16, greedy; scored by `scripts/thai_marks_pzoom2_analyze.py` at git
`e6b1c93` (rules of §3-§4, committed before any output was opened). The pzoom budget used this week:
0.55 + 1.02 + 0.73 = 2.30 of 3 hours. Calibration split, Typhoon only, 21 pages, 71 absent lines
(387 marks), `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

**Registered readings.**

| reading | result |
|---|---|
| stack (`repeat` equal to the stored T1 output) | `baseline_reproduced`: **21 of 21 pages byte for byte**; churn 0.0% |
| stack signature of the two sessions | equal (model revision, fp16, torch 2.14.0+cu130, transformers 5.12.0, Tesla T4, resolved generation); the T1 manifest differs only in not having logged its resolved generation |
| instrument (`bands100` control marks as text) | 99.3% (floor 80%): passes |
| zoom effect `D` = `bands` − `bands100` | **0.0 points**; label `zoom_not_distinguishable` |

`D` needs two caveats. (1) Its page-bootstrap interval is degenerate, [0.0, 0.0], so it cannot be
read as precision: the per-page text marks of the two views are equal on all 21 pages. The only lines
whose text status differs are three on one page (`908E11C8`: two lost, 10 + 6 marks; one gained, 16
marks), which cancel exactly. At line level 3 of 71 absent lines are discordant. (2) This is not the
"low power" case the label's wording guards against: the two views simply recover the same lines.
Sensitivity (reported, never used for the label): `D` = −0.8 / +3.6 / +3.6 / −0.3 points at cutoffs
0.15 / 0.25 / 0.30 and with other lines not claiming first. Read anywhere (text or figure): −4.7
points [−12.6, +0.3]; figure-only share 16.8% (1.0×) → 12.1% (1.85×): at 1.85× fewer lines are only
described inside a figure and more are not found at all. The markup-shift flag is false.

**Also reported.**

| view | content scale | absent marks as text | figure only | not found | net vs baseline [page bootstrap] | churn vs baseline | control marks as text |
|---|---|---|---|---|---|---|---|
| baseline = `repeat` | 1.0 (identical input) | 50.6% | 16.5% | 32.8% | 0 | **0.0%** | 96.9% |
| `pad` | 0.93 | 47.8% | 19.9% | 32.3% | −2.8 [−7.4, 0.0] | 11.1% | 97.8% |
| `scale90` | 0.90 | 56.1% | 18.6% | 25.3% | +5.4 [−11.4, +20.4] | 14.2% | 86.4% |
| `bands100` (3 full-width bands) | 1.0 | **58.7%** | 16.8% | 24.5% | **+8.0 [+0.6, +22.8]** | 19.4% | 99.3% |
| `bands` (same bands) | 1.85 | 58.7% | 12.1% | 29.2% | +8.0 [+0.6, +22.8] | 19.4% | 97.1% |

- **Identical input gives identical output; any change of the image does not.** `repeat` churn is
  0.0%; a 7% rescale with a margin (`pad`) or a 10% shrink (`scale90`) flips 11 to 14% of the absent
  marks across the text / not-text boundary while the net stays small (−2.8, +5.4); the band crops
  flip 19.4%. A comparison of two single reads at the 10-point level is therefore noisy by design.
- **Reading in bands recovers more (crop, not zoom).** `bands100` against the baseline: +8.0 points
  (50.6% → 58.7%): 12 lines gained (53 marks), 9 lost (22 marks); 6 pages better, 13 equal, 2 worse;
  leave-one-page-out +3.7 to +10.5; across the scorer variants +2.8 to +9.1. The largest single
  contribution is page `AF432B6A` (+18 marks, the advertising inset, which is not infographic text).
  Control lines are not lost (99.3%).
- **Cost.** 63 band reads at page scale against 21 whole-page reads: generated tokens 40,438 vs
  26,374 (+53%), visual tokens 53,235 vs 47,264 (+13%), generation time 1,552 s vs 1,029 s (+51%).
  The 1.85× bands carry 182,754 visual tokens (3.9× the page) for the same text recovery. Reads that
  hit `max_new_tokens`: `bands100` 3 of 63, `bands` 2 of 63, `scale90` 1 of 21, `pad` 0, `repeat` 0.
  Recorded visual tokens equal `round(h/32) × round(w/32)` on all 189 reads.
- **P-ZOOM-2's rule as registered:** `no_gain_from_views` (`N` 7.0, `Z` 13.7, `Z − N` 6.7 points
  [−2.3, +21.5]). Not a zoom result (§1), and it shows the gap the review named: `Z ≥ 10` is labelled
  "no gain" because `N` is small.
- **Union of reads** (descriptive; any extra read raises it): baseline 50.6%; + `pad`, `scale90`
  60.5%; + `bands` 64.3%; all five 74.2%.

**What the data show, what is inference, what is unknown.**

- *Shown (these pages, this model):* enlarging the same crops by 1.85× changes the text Typhoon
  recovers by about zero points; reading the page as three full-width bands recovers about 8 more
  points of the marks it left out than reading it whole, without losing ordinary lines, at about
  50% more decode time; and the stack reproduces its own stored reads exactly.
- *Inference, not shown:* that the gain comes from cropping (a smaller context per read) rather than
  from re-sampling, since `pad` and `scale90` also move the recovery by −3 to +5 points and the
  band net's interval starts at +0.6. The CI is wide, the scorer carries inflations of 1 to 2 points
  that favour tiled reads (§8), and 12 gained against 9 lost lines is not much.
- *Unknown:* surplus text. The bands overlap by 15%, so a concatenation repeats text; order-free v2
  precision was not charged here. Whether the effect holds on pages Typhoon reads whole without
  omissions (these 21 were chosen because it left lines out), on other pages of the benchmark, or
  for another model. Whether the lines that remain missing (24.5% not found, 16.8% only inside a
  figure) are reachable by anything training-free.
- *The P-ZOOM question as originally put* ("can Typhoon read the text it leaves out of graphics if
  shown larger?"): within the trained size, showing it larger did not help. Whether a re-read
  method built on the bands is worth its cost is a next draft, not something this round decides.
