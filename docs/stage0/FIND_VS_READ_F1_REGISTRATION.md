# FIND_VS_READ_F1 — registration (Track C)

**Status: `APPROVED`**, `docs/DECISION_LOG.md` entry 2026-10-04 (PELY334 in
session; Up2mEz by merging PR #34). Written before any F1 output exists. Track C
agreed by Up2mEz in
`collab/messages/20261003T1810Z_Up2mEz_to_PELY334_track-c-yes-with-edits.md`
(yes, with five edits, all built in below). Plan:
`docs/exec-plans/active/FIND_VS_READ_PLAN.md`. Parameters:
`configs/find_vs_read/f1.yaml`. Claim level of every result:
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

**Question.** When a Thai mark is wrong in a boxed-region answer, is it lost
because the model had to **find** the boxed text in the whole image, because
of the **scale** at which the text reached it, or does the model fail to
**read** it even when handed exactly the region?

**Primary model: Typhoon OCR 1.5** (the objective is its remaining mark gaps);
the base is reported as a cheap reference.

**What F1 can and cannot do.** The calibration items hold 105 tone marks,
131 upper and 39 lower vowels in total; error counts per arm will be single
digits. F1 tests **direction and mechanism, not magnitude**: the primary
outcome is exact counts, and no conclusion below depends on an interval
excluding zero.

## 1. Fixed inputs

| | |
|---|---|
| models | `Qwen/Qwen3-VL-2B-Instruct@89644892e4d85e24eaac8bacfd4f463576704203`, `typhoon-ai/typhoon-ocr1.5-2b@9c8a8fa14905041d793f1e4e922312147956dcc0` |
| benchmark | `typhoon-ai/ThaiOCRBench@ca610d1ab330` (CC-BY-SA-4.0), task `Fine-grained text recognition` (206 items) |
| items | T1's seeded rule (`labbs2026.thai_marks.split.calibration_ids`, seed 20260927, 30% per (task, category) stratum; the subset does not depend on other tasks) → **69 calibration items**, run in `Id` order; locked 137, never touched |
| references | median 18 characters (max 64) |
| question | **one** template for all 206 items: `แบ่งความยาวและความสูงของรูปภาพออกเป็น 1000 ส่วน แล้วช่วยดึงข้อความที่อยู่ในพิกัด [x1, y1, x2, y2] ของรูปภาพออกมาให้หน่อย` |
| crop prompt | `ช่วยดึงข้อความของรูปภาพออกมาให้หน่อย`, SHA-256 `45078cf08e63c50260c2456ee5ced9ccb1af0abae5a3e49ce8c0c78561f558d5`, both models: the same template with its two coordinate clauses (`แบ่ง…1000 ส่วน แล้ว`, `ที่อยู่ในพิกัด [ … ]`) removed, so whole-image and crop prompts differ only in the box clauses. Checked by the submit script and the worker |
| precision | fp16; fp32 only if the first item's logits are non-finite; recorded |
| decoding | greedy, passed explicitly (`do_sample=false`, `num_beams=1`, `repetition_penalty=1.0`, `no_repeat_ngram_size=0`); `max_new_tokens=512`, far above any reference, so an answer that dumps the page shows as such |
| hardware | Kaggle 2×T4, one model per GPU |

## 2. Geometry (pinned; `labbs2026.find_vs_read.geometry`)

- **Coordinates.** `[x1, y1, x2, y2]` (order checked by cropping real items),
  0–1000 of the image width and height; pixel position `x · W / 1000`,
  `y · H / 1000` as floats.
- **Prepared page** (`prepare_page`): T1's `resize_policy` (long side to
  1,800 px if either side exceeds 300 px, LANCZOS — up or down), then the
  processors' own size rule (`smart_resize`, factor 32, 65,536 ≤ pixels ≤
  16,777,216, bicubic), applied once; the processor then leaves it unchanged
  (tested).
- **Margin.** 0.25 × box height, on every side (boxes are tight; Thai marks sit
  above and below; checked on real items).
- **Page-scale crop rectangle** (`crop_rect`): box on the prepared page, plus
  margin, snapped **outward** to the 32-px grid (floor for left/top, ceil for
  right/bottom), clamped to the page.
- **Rescaled-crop rectangle** (`native_rect`): box on the **original** image,
  plus margin, floored/ceiled to whole pixels, clamped; no grid snapping.

## 3. Arms (every item, both models, same loaded model, this order)

| arm | image | prompt | role |
|---|---|---|---|
| `WHOLE` (a) | prepared page | item question | reference |
| `CROP_SAME_SCALE` (c) | page-scale rectangle cut from the prepared page; below 65,536 px padded right/bottom with white to ≥ 256 × 256, **never resized** | crop prompt | same pixels, magnification and patch/token alignment as (a) |
| `CROP_RESCALED` (b) | rescaled-crop rectangle cut from the **original** image, then `prepare_page` applied to it as if it were a page (usually an enlargement) | crop prompt | the crop as a plain OCR request would see it |
| `WHOLE_MARKED` | prepared page with the page-scale rectangle outlined in red (3 px on its border) | item question | secondary: does a drawn box help following |

Contrasts: **(a)→(c) finding** (same pixels, the page context and the need to
find removed); **(c)→(b) magnification** (same region, larger); (a)→(b) both;
`WHOLE_MARKED` vs (a) secondary.

**Recorded geometry per item** (no image is ever written — CC-BY-SA-4.0):
source size, page size, page scale, both rectangles, whether the page-scale
crop fell under the pixel floor (padded), the rescaled crop's size and scale,
the magnification of (b) relative to (a), and per arm the SHA-256 of the exact
pixels given to the model.

## 4. Scoring

Both strings normalized with T1's registered `normalize_text` (primary);
`output_diagnostics.structure.structural_normalize` as a sensitivity.

1. **Best window** (`find_vs_read.scoring.best_window`): the substring of the
   output with minimum edit distance to the reference (semi-global
   alignment), so the answer is located inside a longer output.
2. **Mark fates** (`mark_fates`) on the window: per reference mark, its class
   (TONE, UPPER, LOWER), fate (correct / deleted / same-class / other) and
   whether its base consonant was read correctly — the same alignment and base
   rule as T1's `mark_decomposition` (tested to agree). **Only marks with a
   correctly read base are scored**; this is what removes wrong-line answers
   from mark rates. No cause-label filter is used (Up2mEz edit 3).
3. **Localisation failure**: an output with no base-correct mark although the
   reference has marks. Reported per arm and model.
4. **Descriptive only**: found rate (window CER ≤ 0.5) with its chance
   baseline (each reference against the next item's output), exact rate,
   characters outside the window, `max_new_tokens` hits, seconds, visual
   tokens.

## 5. Primary outcome — paired mark-level fates, exact counts

For each model (Typhoon first), each contrast in §3 and each mark class: over
the reference marks whose base is read correctly **in both arms**, the counts
correct→correct, **correct→wrong**, **wrong→correct**, wrong→wrong; plus the
marks scored in only one arm and in neither. Counts, not rates; no bootstrap.

## 6. What each pattern would mean, stated in advance

Read on Typhoon first, tone marks first; "more" means a clear majority of the
changed marks, judged on the exact counts.

| pattern | reading |
|---|---|
| (a)→(c): many localisation failures in (a) disappear, and among marks scored in both, wrong→correct ≈ correct→wrong | finding, not reading, is what loses marks in the whole image; remedies should target localization (prompting, marking, region routing) |
| (a)→(c): wrong→correct clearly exceeds correct→wrong on marks scored in both | the same pixels are read better without the page: context or attention costs marks even when the text is found; points to input-side or attention-level remedies, not decoding |
| (a)→(c): correct→wrong clearly exceeds wrong→correct | page context **helps** the marks (F1 cannot separate context from finding; reported as such) |
| (a)→(c): few changes either way and few localisation failures | at this resolution, reading itself is the bottleneck |
| (c)→(b): wrong→correct clearly exceeds correct→wrong | magnification recovers marks that are present at page scale but under-resolved; relevant to P-ZOOM and gap G3 |
| (c)→(b): no change | scale is not the limit for these regions |
| `WHOLE_MARKED` vs (a): fewer localisation failures | a drawn box helps coordinate following — a cheap prompt-side lever (cf. Up2mEz's G1) |

Base results are read the same way and reported beside Typhoon's, never
pooled with them.

## 7. Budget, smoke, stopping

Smoke first: `--smoke 2` (the first two calibration items, both models, all
four arms), inspected for dtype, failures, geometry records (pixel-floor
padding, magnification), output format and time per item. Cap: **2
T4-hours** for the 69 items (four short-answer arms); the smoke gives the
estimate. If over, only the first items in `Id` order that fit are run —
decided before any full-run output, recorded.

## 8. Not in scope

The locked split; Text recognition and Full-page OCR; prompts other than §1;
any scale other than the two in §3 (a fuller scale sweep is P-ZOOM's and gap
G3's); patch-phase manipulation (track D, proposed separately); any claim
beyond these two checkpoints of one architecture family.

---

## Addendum 1, 2026-10-04 — after the smoke, before the full run

No full-run output exists. The only F1 outputs are the engineering smoke
`kaggle-find-vs-read-f1-ff50c65e3152-smoke2` (first 2 calibration items, both
models, all four arms): 0 failures, fp16, checksums verified, no image in the
outputs, geometry recorded (one page-scale crop under the pixel floor and
padded; magnification of `CROP_RESCALED` over the page 1.28× and 2.69×).
Engineering observations only, not evidence.

**1. Scoring rule — a mark is scored only where the answer was found.** In the
smoke, Typhoon's `WHOLE` answered with the image's dimensions
(`ความยาวของรูปภาพ: 1000.0 …`); the best window (§4.1), searched in that
unrelated answer, landed on `ามยา` and matched a base consonant by chance, so
one upper vowel was scored as an error. The base's `WHOLE` on another item gave
the window `แบบของข้อความ` with two marks scored. In the (a)→(c) contrast such
marks become "wrong→correct" and bias the finding comparison toward "the crop
reads better". So, replacing §4.2's scoring condition for the **primary**
outcome (§5): a mark is scored in an arm only if its base consonant is read
correctly **and** that arm's answer is found (window CER ≤ 0.5, the threshold
fixed in §4.4 before any output). Answers not found are localisation failures;
all their marks are unscored. The rule as first registered (base-correct only)
is reported beside it as a sensitivity (`rule="base_only"`). Everything else in
§5–§6 stands.

**2. Reported per arm:** answers not found although the reference has marks
(`not_found_with_reference_marks`), next to §4.3's localisation failures.

**3. Exploratory, not registered as an outcome: possible reference errors.**
On one smoke item the reference reads `แยกสำลี บิ๊กซีรามฯ เอดะมอลล์ราม` while
every Typhoon arm reads `แยกลำสาลี บิ๊กซีรามฯ เดอะมอลล์ราม`. Items where both
crop arms return the same found window and it differs from the reference are
listed (`reference_disagreements`) for human inspection. Scores are never
changed because of this list.

**4. Observed, no change:** with the whole image, the coordinate-system clause
of the question (`แบ่ง…1000 ส่วน`) was misread as a question about the image —
Typhoon answered with image dimensions, the base with its own coordinates and
meta-text. The crop prompt does not carry that clause. This is part of what
(a)→(c) measures, and is reported with the results.

---

## Addendum 2, 2026-10-04 — a fifth arm, before the full run

Suggested by Up2mEz
(`collab/messages/20261004T0605Z_Up2mEz_to_PELY334_f1-addendum1-ok-pr38-track-d-review-s1-results.md`).
No full-run output exists.

The smoke showed the question's leading coordinate-system clause
`แบ่งความยาวและความสูงของรูปภาพออกเป็น 1000 ส่วน แล้ว` (SHA-256
`c6380cc6a8819b9df4ff63edbc8ffbd39f67a299eb6ced180f6e517bd9dd4f40`, present at
the start of all 206 questions) derailing both models in `WHOLE`, while the
crop prompt lacks it. So (a)→(c) as first registered mixes **finding** with
**following that clause**.

**Added arm `WHOLE_NOCLAUSE`:** the prepared page with the item question minus
only that clause — `ช่วยดึงข้อความที่อยู่ในพิกัด [x1, y1, x2, y2] ของรูปภาพออกมาให้หน่อย`.
It differs from the crop prompt only in the box clause `ที่อยู่ในพิกัด [ … ]`
(tested), and from `WHOLE` only in the coordinate-system clause.

**Added contrasts** (same primary outcome and rule as §5 and addendum 1):
`WHOLE_NOCLAUSE` vs `WHOLE` — the cost of the coordinate-system clause;
`CROP_SAME_SCALE` vs `WHOLE_NOCLAUSE` — finding, with that clause removed.

**Reading, stated in advance.** If (a)→(c)'s gains largely vanish in
`WHOLE_NOCLAUSE`→(c), the whole-image losses came from the clause, not from
finding. §6 row 1 is read on `WHOLE_NOCLAUSE`→(c) as well as on (a)→(c), and
any difference between the two is reported. Budget unchanged in practice
(one more short-answer arm; the smoke timing leaves ample room under 2
T4-hours).
