# Track C — finding versus reading

**Status: `F1_DONE`** — results `docs/stage0/FIND_VS_READ_F1_RESULTS.md` (Decision Log 2026-10-04). Owner `PELY334`. Track agreed by
Up2mEz in `collab/messages/20261003T1810Z_Up2mEz_to_PELY334_track-c-yes-with-edits.md`
(yes, with five edits, built into the registration). Nothing runs before the
Decision Log entry (drafted, PR #34) is approved by both researchers;
`configs/find_vs_read/f1.yaml` stays `DRAFT_FOR_REVIEW` until then and the
submit script refuses it. Typhoon is the primary model; the base the cheap
reference.

| | |
|---|---|
| package | `src/labbs2026/find_vs_read/` |
| configs | `configs/find_vs_read/` |
| scripts / worker | `scripts/find_vs_read_kaggle.py`, `scripts/find_vs_read_analyze.py`, `infra/kaggle/find_vs_read_worker.py` |
| registration | `docs/stage0/FIND_VS_READ_F1_REGISTRATION.md` (`DRAFT_FOR_REVIEW`) |
| branch | `PELY334/find-vs-read` |

## 1. Question

On ThaiOCRBench *Fine-grained text recognition*, where every question gives a
box in 0–1000 coordinates, are the models' Thai mark errors caused by
**finding** the boxed text in a whole image, or by **reading** it? Feeds RQ-A
(evidence vs prior) and RQ-B (which remedy family could help): a localization
failure points at prompting or input-side fixes; a reading failure at the
decoding/representation side.

## 2. Design in one paragraph

Each calibration item is run four times per model: `WHOLE` (prepared page +
the item's own question), `CROP_SAME_SCALE` (the boxed region cut on the
32-px token grid of the same prepared page, so pixels, magnification and patch
alignment are unchanged; padded with white if below the processor's pixel
floor), `CROP_RESCALED` (the region cut from the original image and prepared
as if it were a page, usually enlarged — Up2mEz's edit 1) and `WHOLE_MARKED`
(page with the box drawn + the question). (a)→(c) is finding, (c)→(b) is
magnification. The crop prompt is the benchmark's single template with its
coordinate clauses removed. Answers are located inside the output by
best-window alignment; mark fates are scored only where the base consonant was
read correctly, and the primary outcome is exact paired mark-fate counts.

## 3. Why the crop is built this way

- T1's image policy, then the processor's own size rule, are applied once
  (`geometry.prepare_page`); a page at that size passes the processor
  unchanged, so `WHOLE` and `CROP` see identical pixels (tested).
- Snapping the crop to the 32-px grid keeps each 16-px patch and each merged
  token on the same glyph pixels as in the page (tested) — otherwise crop vs
  page would also be a patch-phase manipulation (gap G2).
- Small crops are padded, never enlarged: enlarging would mix magnification
  into the comparison (the TEMS lesson; zoom is P-ZOOM's question).
- Boxes are tight around base glyphs; a margin of 0.25 × box height keeps
  upper and lower marks inside (checked on real items).

## 4. Relation to other work

- Up2mEz's gap G1 (Text recognition question-following) is the same failure
  family on a different task; F1 uses Fine-grained, where the box is given.
- P-ZOOM (Up2mEz, `feat/p-zoom`) enlarges graphics regions on full pages;
  F1 deliberately does not enlarge.

## 5. Waiting on

1. Up2mEz's review of the F1 registration and approval of the Decision Log
   entry in PR #34.
2. Then: smoke (`--smoke 2`), the full 69 items, analysis, results.
