# FIND_VS_READ_F1 — registration (Track C)

**Status: `DRAFT_FOR_REVIEW`.** Written before any F1 output exists. Track C
is proposed, not yet agreed
(`collab/messages/20260928T0546Z_PELY334_to_Up2mEz_propose-track-c-find-vs-read.md`).
Authorizes nothing until both researchers agree and a `docs/DECISION_LOG.md`
entry records it. Plan: `docs/exec-plans/active/FIND_VS_READ_PLAN.md`.
Parameters: `configs/find_vs_read/f1.yaml`. Claim level of every result:
`PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

**Question.** When a Thai mark is wrong in a boxed-region answer, did the model
fail to **find** the boxed text, or fail to **read** it once found?

## 1. Fixed inputs

| | |
|---|---|
| models | `Qwen/Qwen3-VL-2B-Instruct@89644892e4d85e24eaac8bacfd4f463576704203`, `typhoon-ai/typhoon-ocr1.5-2b@9c8a8fa14905041d793f1e4e922312147956dcc0` |
| benchmark | `typhoon-ai/ThaiOCRBench@ca610d1ab330` (CC-BY-SA-4.0), task `Fine-grained text recognition` (206 items) |
| items | T1's seeded rule (`labbs2026.thai_marks.split`, seed 20260927, 30% per (task, category) stratum) applied to this task → **69 calibration items**; locked 137, never touched |
| references | median 18 characters (max 64); 105 tone marks, 131 upper vowels, 39 lower vowels in total |
| question | every item uses one template: `แบ่งความยาวและความสูงของรูปภาพออกเป็น 1000 ส่วน แล้วช่วยดึงข้อความที่อยู่ในพิกัด [x1, y1, x2, y2] ของรูปภาพออกมาให้หน่อย`; the order `[x1, y1, x2, y2]` was checked by cropping real items |
| precision | fp16; fp32 only if the first item's logits are non-finite; recorded |
| decoding | greedy, passed explicitly (`do_sample=false`, `num_beams=1`, `repetition_penalty=1.0`, `no_repeat_ngram_size=0`); `max_new_tokens=512` — far above any reference, so an answer that dumps the page is visible as such |
| hardware | Kaggle 2×T4, one model per GPU |

## 2. Page and crop

1. **Prepared page** (`find_vs_read.geometry.prepare_page`): T1's image policy
   (long side to 1,800 px if either side exceeds 300 px, LANCZOS), then the
   processors' size rule (`smart_resize`, factor 32, 65,536 ≤ pixels ≤
   16,777,216, bicubic) applied once. The processor then leaves it unchanged.
2. **Crop rectangle** (`crop_rect`): the box mapped to the prepared page,
   widened by **0.25 × box height** on every side, snapped outward to the
   32-px grid, clipped to the page.
3. **Crop image** (`crop_padded`): exactly those page pixels; if below 65,536
   pixels, padded right and bottom with white to at least 256 × 256. Never
   resized.

Hence `CROP` and `WHOLE` share pixels, magnification and patch/token grid
alignment (unit-tested); they differ in the surrounding page, the token count,
and the prompt (below).

## 3. Arms (every item, both models, same loaded model, fixed order)

| arm | image | prompt |
|---|---|---|
| `WHOLE` | prepared page | the item's question (box in coordinates) |
| `CROP` | crop image | `ช่วยดึงข้อความในรูปภาพออกมาให้หน่อย` — the benchmark's wording without the coordinate clause |
| `WHOLE_MARKED` | prepared page with the crop rectangle outlined in red (3 px, drawn on the rectangle's border, outside the box) | the item's question |

## 4. Scoring

Both strings normalized with T1's registered `normalize_text` (primary);
`output_diagnostics.structure.structural_normalize` as a sensitivity.

- **Best window** (`find_vs_read.scoring.best_window`): the substring of the
  output with minimum edit distance to the reference.
- **Found**: window distance ÷ reference length ≤ **0.5**. **Chance found
  rate**: the same rule with each reference scored against the next item's
  output; reported next to every found rate.
- **Exact**: window distance 0. **Extra characters**: output outside the
  window (over-generation).
- **Reading error**, on the window only: window CER, and T1's mark
  decomposition (`thai_marks.decompose.mark_decomposition`) — mark-specific
  error per class (marks whose base consonant was read correctly), consonant
  error.

## 5. Comparisons (paired by item)

Primary `CROP` vs `WHOLE`; secondary `WHOLE_MARKED` vs `WHOLE`.

1. Found transitions (found/missed → found/missed) and the found-rate
   difference.
2. On items **found in both arms**: mark-specific error per class, consonant
   error and window CER, each arm − `WHOLE`.
3. Over-generation and `max_new_tokens` hits per arm.

Intervals: item-level bootstrap, 10,000 resamples, seed 20260927. With 69
items and ~100 tone marks the mark intervals will be wide; they are reported,
never called significant.

## 6. What each outcome would mean, stated in advance

- **`CROP` finds many items `WHOLE` misses, and on items found by both the
  mark error is similar** → in `WHOLE`, mark errors come mostly with finding
  failures; the reading itself is not the bottleneck. Remedies should target
  localization (prompting, marking, region routing).
- **On items found by both, `CROP` has lower mark error than `WHOLE`** → the
  same pixels are read worse inside the page: context or attention costs marks
  even when the text is found. Points to input-side or attention-level
  remedies rather than decoding.
- **No difference in either** → reading at this resolution is the bottleneck;
  finding is not. Points away from localization fixes.
- **`WHOLE_MARKED` finds more than `WHOLE`** → a drawn box helps the model
  follow coordinates: a cheap, training-free prompt-side lever (relevant to
  Up2mEz's G1 on Text recognition).
- `CROP` loses the page's language context as well as the need to find; F1
  cannot separate those two. If `CROP` reads marks **worse** on items found by
  both, page context was helping the marks — reported as such.

## 7. Budget, smoke, stopping

Smoke first: `--smoke 2` (first two calibration items, both models, all arms),
inspected for dtype, failures, crop sizes, output format and time per item.
Cap: **2 T4-hours** for the full 69 items (short answers; estimate from the
smoke before submitting; if over, the cap stands and only the first items in the
run's order (calibration items sorted by `Id`) that fit are run — decided
before any full-run output, recorded).

## 8. Not in scope

The locked split; enlargement or any change of scale (P-ZOOM's and track D's
question); prompts other than those in §3; Text recognition and Full-page OCR;
any claim beyond these two checkpoints of one architecture family.
