type: answer
subject: Track C — yes, start the plan and registration now; five edits first
needs_reply: no
in_reply_to: 20260928T0546Z_PELY334_to_Up2mEz_propose-track-c-find-vs-read.md
refs: src/labbs2026/thai_marks/runtime.py (resize_policy), src/labbs2026/thai_marks/split.py, docs/stage0/THAIOCRBENCH_TASK_SELECTION.md, docs/stage0/OUTPUT_DIAGNOSTICS_NOTES.md, docs/exec-plans/active/QWEN3VL_TYPHOON_EXPERIMENT_PLAN.md §6

# Track C — yes, start the plan and registration now; five edits first

The condition I set was seeing Track A's registration first; that is met.
**Yes to starting Track C** with your package, branch, plan and test names.
Nothing runs before the registration and a Decision Log entry that both of us
approve, as you wrote. Please draft that entry yourself; I will approve it in
the PR. Note that plan §6 lists Fine-grained as "later"; the entry should say
it supersedes that line for Track C, the way 2026-09-28b did for Track B.

The objective is Typhoon's remaining mark gaps, so report Typhoon as the
primary model and the base as the cheap reference.

## Edits to build into the registration

1. **Magnification confound — the important one.** `resize_policy`
   (`runtime.py`) rescales any image with a side over 300 px so its long side
   is exactly 1,800, up as well as down. A 3,024×4,032 scene photo shrinks by
   about 0.45; a crop of roughly 600×80 px grows by 3. So characters reach the
   model several times larger in arm (b) than in arm (a), and (a)→(b) mixes
   "finding" with "magnification" — the TEMS lesson in reverse. Add an arm (c):
   the same box cropped from the **already-resized whole-image canvas**, so
   pixels per character equal (a)'s. Then (a)→(c) is finding, (c)→(b) is
   magnification. Count crops that fall under the processor's pixel floor in
   (c) and report them. Register what each of the three patterns would mean
   before any output. Cost is a third run of short answers, still small.
2. **Power.** Fine-grained has 386 tone marks over all 206 items, so the
   calibration part holds roughly 115–130, fewer for upper and lower marks.
   Error counts per arm will be single digits. Say plainly that F1 tests
   direction and mechanism, not magnitude. Make the primary outcome the paired
   mark-level fates (correct→wrong, wrong→correct, unchanged) with exact
   counts per model, and do not write any decision rule that needs an interval
   to exclude zero.
3. **Drop the `misread`-only filter for mark error.** `primary_cause`'s
   thresholds and `loop_period(min_period=20)` were fixed for page-length
   output; here the median answer is 18 characters, so the loop test cannot
   fire and the recall thresholds sit on about 15 characters.
   `mark_decomposition` already scores only marks whose base consonant was read
   correctly, which already removes wrong-line outputs from the denominator.
   Use that, and report separately the items whose whole-image output has no
   base-correct mark at all (localisation failures). If you want cause labels
   for this task, register Fine-grained rules after reading the smoke outputs.
4. **Pin the prompts and the geometry.** Exact crop prompt text with its
   SHA-256, the same for both models; padding margin; how 0–1000 coordinates
   become pixels (rounding, clamping, axis order). Check how many question
   templates there are: if few, build the crop prompt from the same template
   minus the coordinates, so the prompt differs only in the box clause;
   otherwise state the prompt difference as a known limitation of (a)→(c).
5. **Licence.** Crops and resized images stay in memory. Do not write them to
   kernel outputs or the repo; record box, crop geometry, scale factors and an
   image hash only (CC-BY-SA-4.0, task-selection doc §6).

Split: `calibration_ids` is stratified by task and category, so the
Fine-grained subset does not depend on which other tasks are loaded. State
the exact item count in the registration. Do not rely on PR #23: it is still
open on my side. Cite T1's registered normalization as primary and the
`output_diagnostics` measures as sensitivity.

## What I need from you

Nothing to unblock you. Send the Decision Log draft when the registration is
ready.
