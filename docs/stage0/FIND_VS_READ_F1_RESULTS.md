# FIND_VS_READ_F1 — results (Track C)

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** 69 Fine-grained
calibration items. Registration: `docs/stage0/FIND_VS_READ_F1_REGISTRATION.md`
with addenda 1 (marks scored only in found answers) and 2 (`WHOLE_NOCLAUSE`).
Authorization: `docs/DECISION_LOG.md` 2026-10-04. F1 tests **direction and
mechanism, not magnitude**: the primary outcome is exact counts, and no reading
below rests on an interval.

| | |
|---|---|
| run | `kaggle-find-vs-read-f1-7209a2101bf1`, commit `7209a21`, 2×T4, fp16 both models |
| smoke | `kaggle-find-vs-read-f1-ff50c65e3152-smoke2` |
| failures | 0 of 690 item × arm × model generations; checksums verified; no image in any output |
| analysis | `scripts/find_vs_read_analyze.py`, as registered |
| geometry | page-scale crops under the pixel floor (padded, not resized): **40 / 69**; `CROP_RESCALED` magnification over the page: median **2.23×** (0.63–13.0×); page scale median 1.21 |

Arms: (a) `WHOLE` = page + question; `WHOLE_NOCLAUSE` = page + question minus
the coordinate-system clause; `WHOLE_MARKED` = page with the box drawn +
question; (c) `CROP_SAME_SCALE` = the region at page scale, same pixels and
token grid; (b) `CROP_RESCALED` = the region prepared as a page (usually
enlarged). All crops use the same prompt.

## 1. Did the model answer with the boxed text? (per arm)

"Found" = the reference matches a window of the answer with CER ≤ 0.5; the
chance rate (each reference against another item's answer) is 0.000–0.014 for
every arm, so found answers are not coincidences.

| model | `WHOLE` | `WHOLE_NOCLAUSE` | `WHOLE_MARKED` | `CROP_SAME_SCALE` | `CROP_RESCALED` |
|---|---|---|---|---|---|
| **typhoon** found | **7.2%** | 33.3% | 7.2% | **98.6%** | 94.2% |
| typhoon exact | 5.8% | 26.1% | 4.3% | 58.0% | **69.6%** |
| base found | 56.5% | 72.5% | 52.2% | 85.5% | 82.6% |
| base exact | 11.6% | 15.9% | 11.6% | 14.5% | 15.9% |
| base answers hitting 512 tokens | 8 | 7 | 12 | 1 | 6 |

Items whose answer was not found although the reference has marks
(Typhoon / base, of 65): `WHOLE` 60 / 28, `WHOLE_NOCLAUSE` 43 / 18,
`WHOLE_MARKED` 60 / 32, `CROP_SAME_SCALE` 1 / 9, `CROP_RESCALED` 4 / 12.

## 2. Primary outcome — paired mark fates, marks scored in both arms

A mark is scored in an arm when its base consonant is read correctly and the
answer is found (addendum 1). Counts: correct→correct / **correct→wrong** /
**wrong→correct** / wrong→wrong.

### Typhoon (primary)

| contrast | TONE | UPPER | LOWER |
|---|---|---|---|
| (a)→(c) finding | 10 / 0 / 0 / 0 | 15 / 0 / 0 / 0 | 4 / 0 / 0 / 0 |
| `WHOLE_NOCLAUSE`→(c) finding, no clause | 29 / **1** / 0 / 0 | 50 / 0 / 0 / 0 | 11 / 0 / 0 / 0 |
| (c)→(b) magnification | 80 / 0 / **4** / 3 | 112 / 2 / 2 / 2 | 33 / 0 / 0 / 0 |
| `WHOLE_NOCLAUSE` vs (a) clause | 7 / 0 / 0 / 0 | 12 / 0 / 0 / 0 | 4 / 0 / 0 / 0 |
| `WHOLE_MARKED` vs (a) drawn box | 6 / 0 / 0 / 0 | 10 / 0 / 0 / 0 | 4 / 0 / 0 / 0 |

Marks scored only in the crop arm vs `WHOLE` (TONE / UPPER / LOWER): 83 / 106 /
31 — the marks of answers the whole-image run never gave.

### Base (reference)

| contrast | TONE | UPPER | LOWER |
|---|---|---|---|
| (a)→(c) finding | 25 / **6** / 1 / 5 | 37 / 4 / 6 / 1 | 9 / 1 / 1 / 0 |
| `WHOLE_NOCLAUSE`→(c) | 38 / **6** / 3 / 5 | 47 / 6 / 7 / 3 | 13 / 1 / 1 / 0 |
| (c)→(b) magnification | 42 / 6 / 6 / 11 | 54 / 4 / 5 / 8 | 15 / 0 / 0 / 2 |
| `WHOLE_NOCLAUSE` vs (a) | 34 / 1 / 1 / 3 | 46 / 3 / 2 / 6 | 14 / 0 / 1 / 0 |
| `WHOLE_MARKED` vs (a) | 23 / 1 / 0 / 3 | 29 / 2 / 1 / 3 | 10 / 0 / 0 / 0 |

### Sensitivities

- **Structure-aware normalization**: every count above is unchanged.
- **Base-correct-only rule** (as first registered, before addendum 1): Typhoon
  (a)→(c) would show TONE wrong→correct 4 and UPPER 14 — all from marks scored
  inside answers that were **not** found (the chance-window bias the smoke
  exposed). The primary rule removes them; on found answers there is nothing
  to fix. Base counts move by one or two marks; directions unchanged.

## 3. Reading the patterns (registration §6 and addendum 2, stated in advance)

**Typhoon.**

- **Finding, not reading, is what loses marks in the whole image.** In `WHOLE`,
  60 of 65 answers never give the boxed text; in the crop, 1. Where Typhoon did
  answer with the boxed text in the whole image, its marks are already right
  (TONE 29 of 30 scored-in-both marks correct in both arms; the crop broke one,
  fixed none). §6 row 1.
- **The coordinate clause explains part of the finding failure, not most.**
  Removing `แบ่ง…1000 ส่วน แล้ว` raises Typhoon's found rate from 7% to 33%
  (smoke: the clause made it answer with image dimensions); the rest of the
  gap to 99% remains with the clause removed (addendum 2's reading: the gains
  of (a)→(c) do **not** vanish in `WHOLE_NOCLAUSE`→(c)).
- **A drawn box does not help** (7.2% found, as `WHOLE`).
- **Magnification**: tone marks wrong at page scale and right when enlarged 4,
  the reverse 0, of 87 scored in both (7 → 3 wrong). The direction favours
  enlargement, on four marks — too few to call an effect; relevant to P-ZOOM
  and G3, not a result on its own.

**Base.**

- Cropping also fixes most localisation failures (28 → 9 not found), but among
  marks scored in both, **the crop breaks more tone marks than it fixes**
  (6 vs 1 against `WHOLE`, 6 vs 3 against `WHOLE_NOCLAUSE`). §6 row 3: page
  context appears to help the base's tone marks — F1 cannot separate context
  from finding here, and the counts are small.
- Magnification changes nothing net (6 vs 6 tone marks) and makes 6 answers
  run to the token limit.

## 4. Exploratory, not registered

- **Possible reference errors** (both crop arms read the same found text, which
  differs from the reference). Typhoon: 3 — `0276BD3F` (`…เอดะมอลล์ราม` vs the
  sign's `…เดอะมอลล์ราม`), `630C37FF` (`จุดรับของสมนาคุณ` vs `รับของสมนาคุณ`),
  `8FA11DB5` (`ม.เกษตร` vs `ม.เกษตรฯ`). Base: 8, but most are the base's own
  consistent misreads (e.g. `เอออ่าทรบงกุม`), so for the base this heuristic
  mostly lists model errors, not reference errors. Scores were not changed.
- **The task's question template is itself a large part of Typhoon's
  difficulty.** Fine-grained ships the box in the question; parsing it and
  reading the crop (no training, no model change) takes Typhoon from 7% to 99%
  found and 6% to 58–70% exact on these items.

## 4b. Markup audit of the raw outputs (`scripts/audit_markup.py`)

Checked before reporting, per model and arm (69 outputs each): no HTML tag in
any arm except two Typhoon `WHOLE_NOCLAUSE` outputs, which are Typhoon
reciting its own `TYPHOON_CARD` instructions (`Extract all text from the
image. Instructions: …`, tags quoted from that text) — correctly scored as
not found. The base's `WHOLE_MARKED` answers are chatty Markdown (headings,
bullets, bold, code fences in 6–8 outputs), which the best-window scoring
reads through. **No Thai character is removed by either normalization in any
arm (0.0%)**, so no count above is driven by format.

## 5. What this result does not show

- Not magnitudes: 69 items, ~100 tone marks, error counts in single digits.
- Not that cropping is a fix for page-level OCR: the box is given by this task
  (an oracle box); Full-page OCR and Text recognition have no box.
- Not a separation of "finding" from "page context": `CROP_SAME_SCALE` removes
  both; the base's tone result could be either.
- Not anything about other prompts, other tasks, or the locked split; Typhoon's
  absolute scores remain exposed to possible benchmark contamination
  (Decision Log 2026-09-27).

## 6. Directions (proposals, each would need its own registration)

1. **Region routing for Typhoon on boxed tasks**: parse the box, read the crop
   with the plain prompt. On these items it is the single largest lever seen in
   this project's tracks (found 7% → 99%). Natural next test: any other
   ThaiOCRBench task whose questions carry a box, on its calibration items
   only.
2. **Question-following on Text recognition (Up2mEz's G1)**: the coordinate
   clause effect here (7% → 33%) suggests prompt wording alone moves Typhoon's
   localisation; worth reading next to G1.
3. **Magnification for tone marks**: the 4-vs-0 direction in (c)→(b) belongs
   with P-ZOOM's question; a larger item set would be needed.
4. **D1 (patch phase)** runs on exactly these crops; its `D0` reproduces
   `CROP_SAME_SCALE`.
