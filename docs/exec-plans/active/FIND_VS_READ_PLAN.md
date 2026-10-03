# Track C — finding versus reading

**Status: `PROPOSED_AWAITING_AGREEMENT`.** Owner `PELY334`. Proposed in
`collab/messages/20260928T0546Z_PELY334_to_Up2mEz_propose-track-c-find-vs-read.md`;
Up2mEz asked to see Track A's registration first, which has since landed and
run (`docs/stage0/SPEC_DECODE_S1_RESULTS.md`). Nothing here authorizes
inference; `configs/find_vs_read/f1.yaml` is `DRAFT_FOR_REVIEW` and the submit
script refuses it.

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

Each calibration item is run three times per model, all from one prepared
page: `WHOLE` (whole image + the item's own question), `CROP` (the boxed
region, cut on the 32-px token grid of the same page so pixels, magnification
and patch alignment are unchanged, padded with white if below the processor's
pixel floor, with the benchmark's own wording minus the coordinate clause), and
`WHOLE_MARKED` (whole image with the box drawn in red + the question). Answers
are scored against the best-matching window of the output, so a misplaced or
page-length answer is a *finding* failure and never a reading error.

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

1. Up2mEz's agreement to Track C, and review of the F1 registration.
2. A Decision Log entry approved by both researchers.
