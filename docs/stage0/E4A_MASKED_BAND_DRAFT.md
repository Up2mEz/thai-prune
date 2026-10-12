# E4a — masked bands: is the omitted text lost to competing content, or to image size?

**Status: `APPROVED` by the researcher in session on 2026-10-12** ("ทำสิ่งที่ต้องทำเพิ่มข้อ 2, 3, 5"), written
**before any E4a output exists**. Typhoon only, calibration split, the 21 P-ZOOM pages. Evaluates no method.
Claim level `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. Decision Log 2026-10-12c (gaps).

## 1. Question

The paper can say that lines are *absent from the output*. It cannot say whether Typhoon fails to see them or sees
them and does not write them (`LIT_REVIEW_OMISSION_2026-10-12.md`). Known so far, on the same pages:

- reading three full-width bands at page scale (`bands100`) recovers about 8 points more of the omitted marks than
  the whole page (P-ZOOM-3);
- enlarging the bands 1.85× adds nothing (P-ZOOM-3);
- a band is **both** a smaller image (fewer visual tokens) **and** a page with fewer competing lines.

E4a separates those two. `masked_bands` keeps a band's pixels where they were and paints everything else white. The
image is as large as the whole page, at the same scale, with the same visual-token count. Only the content of the
other two bands is missing. This adapts Monkey's same-pixel comparison (Li et al., CVPR 2024) and the crop-versus-box
design of Dolphin (Feng et al., ACL Findings 2025).

## 2. Reads (Typhoon, `TYPHOON_CARD`, greedy as T1, same 21 pages, fp16): 147

| view | image fed | reads |
|---|---|---|
| `repeat` | the T1 whole-page input unchanged | 21 |
| `bands100` | three full-width bands, 15% overlap, page scale | 63 |
| `masked_bands` | the whole page, all but one band painted white, then `resize_policy` | 63 |

All three run in **one session**, so no contrast subtracts reads from two sessions (the defect P-ZOOM-3 corrected).
Code: `tiling.view_images` kind `masked` (tested: same size as `whole`, tile pixels kept, the rest white);
config `configs/thai_marks/p_zoom4.yaml`; run with `--tests t6 --views-config configs/thai_marks/p_zoom4.yaml`.
2×T4, 1–2 GPU-hours, own quota.

## 3. Measures, fixed before any output is read

Lines, selection and scorer as P-ZOOM-3 (`p_zoom2_analysis`, `READ_ELSEWHERE_CER` 0.2): the share of the omitted
lines' marks that a view finds as text.

- **Text share** of omitted marks per view, with a 95% paired bootstrap over the 21 pages (seed 20261012, 2,000
  resamples).
- **C1 = `masked_bands` − `repeat`**: removing competing content with size, scale and token count held fixed.
- **C2 = `bands100` − `repeat`**: the crop effect, to check it reproduces P-ZOOM-3's +8 points.
- **C3 = `bands100` − `masked_bands`**: what is left of the crop effect after the content has been removed, that is,
  what the smaller image adds.
- **Control:** the share of the control lines (lines read in the whole-page read) that each view finds as text.
- **Stack check:** `repeat` against the stored T1 output byte for byte (pages identical, of 21).
- **Cost:** reads, generated and visual tokens per view; loops (`reached_max_new_tokens`) per view.

## 4. Readings, fixed in advance

A contrast is *material* when its 95% interval excludes 0 and its estimate is at least 5 points. The 5 points are a
judgement, not derived from data.

| outcome | reading |
|---|---|
| C1 material | Competing content matters: with the same image size and token count, fewer lines in view recover omitted text. The omitted lines are readable, and they lose to the other lines. |
| C1 not material, C2 material, C3 material | The crop effect comes from the smaller image (fewer visual tokens or a different input size), not from fewer lines. |
| C1 and C3 both material | Both contribute. The shares are reported, not attributed. |
| C1 not material and C2 not material | The crop effect of P-ZOOM-3 did not reproduce in this session; the stack check says whether run-to-run drift explains it. No reading of mechanism. |
| control share of `masked_bands` under 80% (P-ZOOM's floor) | `masked_bands` is damaging ordinary reading; its readings are marked as qualified. |

Whatever the outcome, n = 21 pages and about 24 omitted lines make it **direction, not magnitude**. No outcome is
called "equivalent".

## 5. What this does not decide

- It does not say the model "cannot see" a line. A line that is recovered in `masked_bands` was seen in the whole page
  too, in the sense that its pixels were the same; the whole-page read left it out. That supports "does not write it
  under competition", and it is a statement about this model and these pages.
- A line that is **not** recovered in either view is a candidate for "cannot read at this resolution". E4a does not
  test that.
- No remedy is proposed. P-BAND already showed that reading bands as a method lowers whole-page F1.

## 6. Cost and stopping

Smoke first (two pages, secondary account), then the full run on 2×T4. No read is repeated to change a result; a
failed read is listed and the contrasts say how many pages each uses.

## 7. Result (2026-10-12)

Run `kaggle-thai-marks-t6-ddad6b7569b2-typhoon-x2` (git `ddad6b7`), 147 reads, 0 failures, checksums verified,
2×T4, fp16, 1.21 GPU-hours (shards 2,435 s and 1,939 s). Scored by `scripts/thai_marks_e4a_analyze.py`
(`docs/stage0/data/E4A_SUMMARY_ddad6b7569b2.json`). Smoke first (2 pages, 0 failures; masked reads had the whole
page's visual-token count, 2,352 per read).

| view | omitted marks found as text | control marks as text | reads | generated tokens | visual tokens | loops |
|---|---|---|---|---|---|---|
| `repeat` | 50.6% | 96.9% | 21 | 26,374 | 47,264 | 0 |
| `bands100` | 58.7% | 99.3% | 63 | 40,438 | 53,235 | 3 |
| `masked_bands` | 58.9% | 96.9% | 63 | 37,610 | 141,792 | 2 |

- **Stack check:** `repeat` equals the stored T1 output on 21 of 21 pages.
- **C1** (`masked_bands` − `repeat`): **+8.3 points** [+0.7, +23.3].
- **C2** (`bands100` − `repeat`): +8.0 [+0.4, +22.6]. This reproduces P-ZOOM-3's +8.0.
- **C3** (`bands100` − `masked_bands`): −0.3 [−11.7, +8.1].
- Lines whose status differs between the two band views: 6 of 71 omitted lines.

**Registered label (§4): `competing_content`** (C1 material, C3 not). The control share of `masked_bands` is 96.9%,
above the floor.

### What the label does not show (disclosed before anything is written about it)

The registered contrast compares **three reads** (the three bands, a line counts as found if any read finds it)
with **one** whole-page read. The design did not include a control that gives the whole page the same number of
different reads. A post-hoc check on the stored P-ZOOM-2/-3 reads (**exploratory, not registered**, a different
session): the union of `repeat`, `pad` and `scale90`, three whole-page reads with no crop and no masking, finds
**60.5%** of the omitted marks. That equals `bands100` (58.7%) and `masked_bands` (58.9%).

So the gain in both band views is at least as well explained by "more than one different read of the page" as by
"fewer competing lines". E4a as registered cannot tell the two apart; the formal label should not be quoted as a
mechanism. What E4a does show: the band gain is not due to the smaller image or its token count (C3 ≈ 0 with
identical reads of 3× the tokens), and it reproduces.

**Next step, if wanted (a new registration):** the same session with the same number of reads of each kind: three
different whole-page perturbations against the three masked bands, compared as unions and read by read.

n = 21 pages, 71 omitted lines: direction, not magnitude.
