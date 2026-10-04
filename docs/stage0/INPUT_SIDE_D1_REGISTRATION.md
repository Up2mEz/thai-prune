# INPUT_SIDE_D1 — registration (Track D, gap G2: patch phase)

**Status: `DRAFT_FOR_REVIEW`.** Written before any D1 output exists. Scope
(G2 only) agreed by Up2mEz with three edits, all built in below
(`collab/messages/20261004T0605Z_Up2mEz_to_PELY334_f1-addendum1-ok-pr38-track-d-review-s1-results.md`).
Authorizes nothing until a `docs/DECISION_LOG.md` entry approved by both
researchers records it. Plan: `docs/exec-plans/active/INPUT_SIDE_PLAN.md`.
Parameters: `configs/input_side/d1.yaml`. Claim level of every result:
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

**Question.** Does where the 16-px patch grid falls on a Thai glyph decide
whether its mark is read correctly?

**Primary model: Typhoon OCR 1.5**; the base is reported as a reference.

## 1. Fixed inputs (as FIND_VS_READ_F1 unless stated)

| | |
|---|---|
| models | `Qwen/Qwen3-VL-2B-Instruct@89644892e4d85e24eaac8bacfd4f463576704203`, `typhoon-ai/typhoon-ocr1.5-2b@9c8a8fa14905041d793f1e4e922312147956dcc0` |
| items | the same **69** Fine-grained calibration items as F1 (T1's seeded rule), run in `Id` order; locked split never touched |
| page | F1's `prepare_page` (T1 policy, then the processor size rule, applied once) |
| base rectangle | F1's page-scale crop rectangle: box + 0.25 × box height on every side, snapped outward to the 32-px grid, clamped |
| prompt | F1's crop prompt `ช่วยดึงข้อความของรูปภาพออกมาให้หน่อย`, SHA-256 `45078cf08e63c50260c2456ee5ced9ccb1af0abae5a3e49ce8c0c78561f558d5`, both models |
| decoding | greedy, explicit (`do_sample=false`, `num_beams=1`, `repetition_penalty=1.0`, `no_repeat_ngram_size=0`), `max_new_tokens=512` |
| precision | fp16; fp32 only if the first item's logits are non-finite; recorded |
| hardware | Kaggle 2×T4, one model per GPU |

## 2. The shift (`labbs2026.input_side.phase`; Up2mEz's edit 1)

For a shift `d`, the crop **window is moved up by `d` px** over the prepared
page: window row `y` shows page row `top + y − d`, so every glyph sits `d` px
lower relative to the grid. Rows that fall outside the page are white. The
window keeps the base rectangle's size (a multiple of 32); below 65,536 pixels
it is padded right/bottom with white exactly as in F1. **No pixel is
resampled and the processor leaves the image unchanged** (tested for every
`d`). Images are never written anywhere; per arm the SHA-256 of the exact
pixels is recorded.

## 3. Arms (every item, both models, same loaded model, this order)

| arm | `d` (px) | what changes relative to `D0` |
|---|---|---|
| `D0` | 0 | — (F1's `CROP_SAME_SCALE` input) |
| `D4`, `D8`, `D12` | 4, 8, 12 | **patch phase** (16-px period) |
| `D16` | 16 | same patch phase; different **2×2 merge pairing** into tokens (32-px period) |
| `D32` | 32 | same patch and merge phase, one token row lower: the **phase-neutral control** (M-RoPE positions shift; 32 px of edge context change) — Up2mEz's edit 2 |

## 4. Scoring

Exactly F1's (`find_vs_read.scoring`, `find_vs_read.analysis.item_rows`): T1's
`normalize_text` (primary), best window, mark fates; a mark is **scored** in an
arm only if its base consonant is read correctly **and** that arm's answer is
found (window CER ≤ 0.5; F1 addendum 1).

## 5. Primary outcome — exact counts, no interval (Up2mEz's edit 3)

Per model (Typhoon first) and mark class (TONE first):

- **flips(d)** for `d` ∈ {4, 8, 12, 16}: marks scored in both `D0` and `Dd` whose
  status differs (correct→wrong plus wrong→correct), with the number scored in
  both;
- **flips(32)**: the same between `D0` and `D32` — the control count;
- the paired table per shift, and the number of marks scored in all of `D0`,
  `D4`, `D8`, `D12` whose status is not constant across them.

## 6. What each pattern would mean, stated in advance

| pattern (Typhoon, tone marks first) | reading |
|---|---|
| flips(4/8/12) **no larger than** flips(32) | grid phase does not decide marks; differences between page positions are position/context noise of the same size |
| flips(4/8/12) clearly larger than flips(32), and flips(16) ≈ flips(32) | sub-patch phase decides marks: patch embedding, not merging, is where a mark can be lost; reading at two phases is worth registering as a remedy |
| flips(16) clearly larger than flips(32) | the 2×2 merge pairing decides marks (which patches share a token) |
| all shifts including 32 flip many marks | readings are unstable to any small input change; phase cannot be singled out (cf. P-ZOOM-2's perturbation control) |

"Clearly larger" is judged on the exact counts and reported with them; with
about 105 tone marks a difference of a few marks is not read as an effect.
Consonant flips are reported alongside: a phase effect specific to marks
should not appear equally on consonants.

## 7. Budget, smoke, stopping

Smoke first: `--smoke 2` (two items, both models, all six arms), checked for
dtype, failures, crop sizes, output format and time. Six short-answer arms on
69 items: F1's smoke timing implies well under **1 T4-hour**; cap 2 T4-hours.
If over, only the first items in `Id` order that fit are run — decided before
any full-run output, recorded.

## 8. Not in scope

Scale (G3, with P-ZOOM); horizontal shifts; Full-page OCR and Text
recognition; any remedy; the locked split; claims beyond these two
checkpoints of one architecture family.
