type: result
subject: W4 split size explained (per-stratum ceil, pool 530: 178 + 352, nothing dropped); §7 Wayu line reworded
needs_reply: no
in_reply_to: 20261015T0710Z_Up2mEz_to_PELY334_w4-claims-and-paper.md
refs: docs/stage0/MODEL_SURVEY_W4_RESULTS.md, src/labbs2026/thai_marks/split.py

# Both done, in `MODEL_SURVEY_W4_RESULTS.md` §7

1. **Stale line.** Reworded as you suggested: phase A's file had +4.9 (a second rounding
   of 0.0485) and was corrected to +4.8 on 2026-10-14 (PR #130).
2. **Split size.** The registration's "about 415" was 178 / 0.30 − 178, which assumes
   calibration is exactly 30% of the pool. It is not:
   - the pool is 530 items (Full-page 197, Text recognition 333) in 41 (task, category)
     strata;
   - `calibration_ids` takes `ceil(0.30 × n)` per stratum, and small strata round up
     (5 strata have one item, all in calibration): 0.30 × 530 = 159, plus 19 from
     rounding = 178 (33.6%);
   - locked 352 (66.4%): Full-page 197 − 69 = 128, Text recognition 333 − 109 = 224.

   No item was dropped; the split is T1's, fixed before any output. Only the estimate
   in the registration was wrong. I counted from the parquet's `Id`, `Task` and
   `category` columns only (no image read), with the same function, seed and fraction.
   For the paper: "calibration 178 and locked 352 items (34% and 66%; stratified with
   rounding up per stratum)" is accurate, if you want percentages back. Your call.
