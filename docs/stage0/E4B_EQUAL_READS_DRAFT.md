# E4b — the same number of different reads: whole page or masked bands?

**Status: `APPROVED` by the researcher in session on 2026-10-12** ("ทำ E4b E5"), written **before any E4b output
exists**. Typhoon only, calibration split, the 21 P-ZOOM pages. Evaluates no method. Claim level
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. Decision Log 2026-10-12f (gaps). Follows E4a
(`E4A_MASKED_BAND_DRAFT.md` §7).

## 1. Question

E4a gave the label `competing_content` (`masked_bands` finds 58.9% of the omitted marks, the whole page 50.6%), and
then disclosed why that label is not a mechanism: `masked_bands` is **three reads** counted as found if any read finds
the line, the whole page is **one**. A post-hoc union of three whole-page reads (`repeat`, `pad`, `scale90`, no crop,
no masking, from older sessions) found 60.5%. E4b removes the difference in number of reads, in one session:

> When the whole page gets as many different reads as the masked bands, do the masked bands still recover more of the
> omitted lines?

If yes, taking the other lines away helps beyond the effect of reading more than once. If no, "read it more than once
with a slightly different image" explains the gain on these pages, and nothing here says the other lines compete.

## 2. Reads (Typhoon, `TYPHOON_CARD`, greedy as T1, same 21 pages, fp16): 168

| view | image fed | reads |
|---|---|---|
| `repeat` | the T1 whole-page input unchanged | 21 |
| `pad` | the page on a 4% white margin (P-ZOOM-2) | 21 |
| `scale90` | the page, then scaled to 0.9 (P-ZOOM-2) | 21 |
| `pad12` | the page on a 12% white margin | 21 |
| `scale75` | the page, then scaled to 0.75 | 21 |
| `masked_bands` | E4a: whole page, all but one of three bands painted white, `resize_policy` | 63 |

All in **one session**. Code and config: `configs/thai_marks/p_zoom5.yaml`, `tiling.view_images` (kinds `whole`,
`pad`, `scale`, `masked`; unchanged since P-ZOOM-2/E4a), run with `--tests t6 --views-config
configs/thai_marks/p_zoom5.yaml`. 2×T4, about 1.5 GPU-hours, own quota.

`pad12` and `scale75` are added because `pad` and `scale90` are near-copies of the page, and a masked band is a much
more different image. Without them, a gain for the masked bands could come from different reads being less correlated,
not from competing content. They are larger perturbations in the same family, chosen before any output.

## 3. Arms and measures, fixed before any output is read (`e4b_analysis`)

Lines, selection and scorer as E4a (`p_zoom2_analysis`, `READ_ELSEWHERE_CER` 0.2): the share of the omitted lines'
marks that the reads find as text; a line counts as found by a set of reads if any read in the set finds it.

- **W3** = `repeat` + `pad` + `scale90`: three whole-page reads (the same three as the post-hoc union).
- **M3** = the three `masked_bands` reads.
- **W5** = W3 + `pad12` + `scale75`.
- **D1 = M3 − W3**: the equal-read-count contrast, the registered comparison. 95% paired bootstrap over the 21 pages
  (seed 20261012, 2,000 resamples).
- **D2 = M3 − W5**: the masked bands against more whole-page reads than they have.
- **Single reads:** the text share of each whole-page view alone and its control share.
- **Read curve (descriptive):** whole-page union share against the number of reads (mean over all subsets of the
  five whole-page views of each size).
- **Stack check:** `repeat` equals the stored T1 output byte for byte (pages identical, of 21).
- **Control:** control lines found as text per view; floor 80% (P-ZOOM's).
- **Cost:** reads, generated and visual tokens per view; loops per view.

## 4. Readings, fixed in advance

A contrast is *material* when its 95% interval excludes 0 and its estimate is at least 5 points (a judgement).

| outcome (D1 = M3 − W3) | reading |
|---|---|
| D1 material, positive | `masking_adds_beyond_read_count`: at three reads each, the masked bands recover more than whole-page reads. Taking the other lines away helps beyond reading more than once. |
| D1 interval below 0 and estimate ≤ −5 | `whole_page_reads_recover_more`: whole-page reads recover more than masked bands at equal read count. The E4a gain is not explained by competing content. |
| otherwise | `read_count_accounts_for_gain`: at equal read count, masked bands are not shown to recover more. This does not say they recover the same. |
| control share under 80% in W3 or `masked_bands` | the label gets the suffix `_qualified`. |

D2 and the read curve are reported and **not read** for mechanism. `pad12` and `scale75` under the control floor are
listed and leave W5 qualified (W3 and D1 do not use them).

Whatever the outcome, n = 21 pages and about 24 omitted lines make it **direction, not magnitude**. No outcome is
called "equivalent".

## 5. What this does not decide

- Even a `masking_adds_beyond_read_count` outcome would not say the model "cannot see" the line. It would say that
  with the same pixels and fewer other lines, the line is written more often.
- The three masked reads and the three whole-page reads are different in other ways than the content they hold: a
  line sits in one or two bands but in all three whole-page reads. D1 does not separate those.
- It does not say anything about other models, other pages, or the locked split.
- No remedy is proposed; reading several perturbed whole pages and merging them is **not** evaluated as a method
  (it costs three reads and no merge rule is registered).

## 6. Cost and stopping

Smoke first (two pages), then the full run on 2×T4. No read is repeated to change a result; a failed read is listed and
the contrasts say how many pages each uses.
