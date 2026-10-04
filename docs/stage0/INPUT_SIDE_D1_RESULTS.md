# INPUT_SIDE_D1 — results (Track D, gap G2: patch phase)

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** 69 Fine-grained
calibration items, the same as FIND_VS_READ_F1. Registration:
`docs/stage0/INPUT_SIDE_D1_REGISTRATION.md` with addendum 1 (the window is
extended 64 px below the box so no shift clips it). Authorization:
`docs/DECISION_LOG.md` 2026-10-04b. Direction and mechanism, not magnitude:
exact counts, no interval.

| | |
|---|---|
| run | `kaggle-input-side-d1-9f51ed7d83f0`, commit `9f51ed7`, 2×T4, fp16 both models |
| smokes | `kaggle-input-side-d1-4290f823c924-smoke2` (exposed the clipping flaw), `kaggle-input-side-d1-9f51ed7d83f0-smoke2` (after the fix) |
| failures | 0 of 966 generations (69 items × 7 shifts × 2 models); checksums verified; no image in any output |
| markup audit | `scripts/audit_markup.py`: no HTML tag in any of the 14 model × shift cells; a few Markdown bullets / bold / one code fence in base outputs; **0.0% of Thai characters removed** by either normalization in every cell |
| analysis | `scripts/input_side_analyze.py` (registered; consonant flips added to the code before reporting, as §6 requires) |

## 1. Answers found per shift

| model | D0 | D4 | D8 | D12 | D16 | D32 | D64 |
|---|---|---|---|---|---|---|---|
| typhoon | 63 | 65 | 67 | 67 | 65 | 68 | 65 |
| base | 56 | 55 | 56 | 58 | 58 | 58 | 57 |

(of 69). Finding itself moves by a few items with the window's position and
edge context — e.g. at `D32` one Typhoon answer reads a line just below the box.

## 2. Primary outcome — flips against `D0`

Marks (and consonants) scored in both `D0` and `Dd` (answer found, base
consonant read correctly) whose status differs. Counts flips / scored in both,
with the rate.

### Typhoon (primary)

| | D4 | D8 | D12 | D16 (merge) | **D32 (control)** | **D64 (control)** |
|---|---|---|---|---|---|---|
| TONE | 2/89 (2.2%) | 3/87 (3.4%) | 4/86 (4.7%) | 3/88 (3.4%) | 2/88 (2.3%) | 2/84 (2.4%) |
| UPPER | 0/114 | 1/110 | 1/108 | 4/109 (3.7%) | 1/111 | 2/111 (1.8%) |
| LOWER | 0/34 | 0/34 | 0/32 | 0/32 | 0/34 | 0/31 |
| consonants | 27/813 (3.3%) | 26/801 (3.2%) | 32/793 (4.0%) | 17/796 (2.1%) | 18/804 (2.2%) | 21/787 (2.7%) |

Tone marks scored in all of D0–D12 whose status is not constant: **3 of 84**.

### Base (reference)

| | D4 | D8 | D12 | D16 | D32 (control) | D64 (control) |
|---|---|---|---|---|---|---|
| TONE | 6/57 (10.5%) | 8/60 (13.3%) | 7/61 (11.5%) | 8/65 (12.3%) | 6/65 (9.2%) | 7/61 (11.5%) |
| UPPER | 7/73 (9.6%) | 10/75 (13.3%) | 7/73 (9.6%) | 7/81 (8.6%) | 6/78 (7.7%) | 9/79 (11.4%) |
| LOWER | 1/19 | 3/20 | 2/16 | 1/22 | 2/21 | 0/20 |
| consonants | 56/651 (8.6%) | 78/677 (11.5%) | 61/653 (9.3%) | 55/723 (7.6%) | 55/706 (7.8%) | 54/664 (8.1%) |

Tone marks scored in all of D0–D12 not constant: 11 of 51.

Structure-aware normalization gives the same counts in every cell.

## 3. Reading, against §6 (stated in advance)

- **Typhoon: no evidence of a phase effect larger than a few marks, on boxed
  single-line crops.** *(Wording revised 2026-10-05 after Up2mEz's review,
  `collab/messages/20261004T1254Z_Up2mEz_to_PELY334_review-d1-result.md`; first
  version: "grid phase does not decide marks".)* Patch-phase shifts flip 2–4
  tone marks against 2 for each phase-neutral control — a difference of one or
  two marks, which §6 does not read as an effect. **Consonants move the same
  way** (3.2–4.0% at 4/8/12 vs 2.2–2.7% at the controls; pooled 85/2,407 =
  3.5% vs 39/1,591 = 2.5% — the flips share marks across arms, so not read as
  an interval or an effect), so whatever small
  sensitivity sub-patch shifts add is not specific to marks. Lower vowels never
  flip. The merge-pairing shift (16) flips 4 upper vowels against 1–2 at the
  controls: a handful, noted, not read as an effect.
- **Base: readings are unstable to any small input change.** Every shift,
  the controls included, flips ~8–13% of scored characters, marks and
  consonants alike (§6 last row). Phase cannot be singled out on the base.
- **For the remedy question**: a phase-aware input remedy (reading at several
  phases) is not supported for Typhoon by this test. Typhoon's remaining mark
  errors in the crop (F1's reading ceiling: 7/93 tone marks wrong at page
  scale) are not explained by where the grid falls.

## 4. What this result does not show

- Not magnitudes: ~85 tone marks scored per comparison; flip counts in single
  digits for Typhoon.
- Not horizontal phase, scale (G3, with P-ZOOM), or page-level OCR — only
  boxed crops of Fine-grained items.
- The controls change position and up to 64 px of context together; D1 cannot
  separate those two.
- `D0` is not pixel-identical to F1's `CROP_SAME_SCALE` (the window carries
  64 px more below the box, addendum 1); comparisons with F1 are by item, not
  by pixel.
- Nothing about other models; Typhoon's absolute scores remain exposed to
  possible benchmark contamination (Decision Log 2026-09-27).

## 5. Directions

1. Deprioritise phase-aware input handling as a Typhoon remedy candidate
   (first version: "drop"). Power is limited: in F1 only 7 of 93 Typhoon tone
   marks are wrong at page scale, so among ~88 scored marks only a few can
   change status, and D1 rules out only effects larger than a handful of
   marks. G2 in the architecture note concerns dense page lines, where a mark
   sits among neighbours in the same patch row; D1 tested the cleaner case of
   one short line, so a page-level effect is not excluded.
2. The base's 8–13% flip rate under tiny shifts suggests that multi-view
   reading with voting (P-ZOOM-2's perturbation control; arXiv:2509.09722)
   could help the base; Typhoon is too stable for that to matter much here.
3. Typhoon's remaining crop errors are rare tone marks (`๊`, `๋`) and `้`/`่`
   swaps (F1 §3b): a mark-level re-scoring of the few legal variants (the
   project plan's §4 method) remains the direct candidate, pending the T2
   rerun.
