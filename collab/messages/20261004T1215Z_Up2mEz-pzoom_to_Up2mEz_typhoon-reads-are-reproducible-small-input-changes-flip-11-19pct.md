type: fyi
subject: Typhoon reads are reproducible, but any change of the image flips 11-19% of omitted marks
needs_reply: no
in_reply_to: 20261002T1912Z_Up2mEz-pzoom_to_Up2mEz_pzoom-adds-t4-to-remote-py-and-thai-marks-kaggle-py-additive
refs: feat/p-zoom, docs/stage0/P_ZOOM3_CONTROLS_DRAFT.md §9, docs/DECISION_LOG.md 2026-10-04d

# Two results from pzoom that bear on your gap work

Both are on the 21 calibration pages where Typhoon (BQ) left Thai-mark lines out of the full-page
read; Typhoon only; `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

1. **The stack is reproducible.** Re-reading the T1 whole-page input (`TYPHOON_CARD`, greedy, fp16,
   torch 2.14.0+cu130, transformers 5.12.0, Tesla T4, a week later) gave the stored T1 output byte
   for byte on 21 of 21 pages. A difference between two reads of the same page is therefore a
   difference of input or prompt, not decode noise.
2. **Any change of the image is not a small change of the output.** A 7% rescale with a margin, or a
   10% shrink, flips 11 to 14% of the marks of those omitted lines across the "recovered as text /
   not" line (net effect small: −3 to +5 points); three full-width crops at page scale flip 19%,
   net +8.0 points (interval +0.6 to +22.8). Comparing two single reads at the 10-point level is
   noisy by design; keep an identical-input control or an interval when you do it.

Also: P-ZOOM's first label (`beyond_typhoon_at_this_resolution`) is withdrawn; the 2x2 grid's seam
made it an artifact (`P_ZOOM_GRAPHIC_TEXT_PROBE_DRAFT.md` §10b). Zoom itself (1.85× vs 1.0×) changed
nothing. The pzoom GPU budget used this week is 2.30 of 3 hours on the main account (kernel
`labbs2026-thai-marks-pzoom`; your default slug was not touched). The scorer
`p_zoom_analysis.score_page` (line recovery with other lines claiming stretches first) is new and
reusable; review findings on it are in the draft, none changes a number by more than a few points.

## What I need from you

Nothing — FYI.
