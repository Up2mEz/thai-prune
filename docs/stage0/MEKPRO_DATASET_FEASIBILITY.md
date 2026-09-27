# `mekpro/ocr_th` — feasibility assessment for a whole-image H3 arm

**Status: `CONDITIONAL_GO`, nothing authorized, no design written.** This records
measurements only. Any run needs its own registration and a Decision Log entry.

## Why this was revisited

`docs/stage0/REGION_OCR_DATASET_CANDIDATE_AUDIT.md` lists this dataset as
`REJECTED`, on two grounds: "Synthetic" and "No — page-level text only".

**The second ground is void for a whole-image design.** It was recorded when the
unit of analysis was a text region and region annotations were required. Using
whole images as the unit removes that requirement. The first ground stands and is
carried forward as a limitation below.

The reason to revisit at all is round 3's family E: TEMS regions sit below the
processor's pixel floor, so resolution reduction there never discards source
information and the corpus cannot test H3 in the compression regime at any
budget. See `REGION_OCR_ROUND3_RESULTS.md` §8.

## Licence

`apache-2.0` as declared on the dataset card, read 2026-09-21. No addendum, no
acceptable-use rider. 4,000 rows, `Image-to-Text`, language Thai, tagged
`Synthetic`.

## Population (exact counts, `labbs2026-mekpro-population-count`)

| subset | rows | below floor | native, no resize | above ceiling | `RR_25` discards real pixels | in readable band |
|---|---|---|---|---|---|---|
| `official` | 2,000 | **0** | 1,924 | 76 | **2,000 / 2,000** | **903** |
| `table` | 1,000 | 2 | 998 | 0 | 1,000 / 1,000 | 656 |
| `text` | 1,000 | 499 | 494 | 7 | 774 / 1,000 | 368 |

Processor floor 112,896 px, ceiling 1,003,520 px. "Readable band" is
112,896–350,000 px, the range that did not collapse in the GPU probe below.

`official` area p10/p50/p90 = 220,420 / 369,138 / 685,410 px; reference length
p50 = 586 characters. Within the band: area p10/p90 = 193,104 / 334,530,
characters p50 = 522.

**This is the regime TEMS cannot provide.** Every `official` row renders at or
near native resolution and is genuinely downsampled by every reduced budget. For
comparison, requiring a real compression regime in TEMS leaves 61 Thai regions
across 52 photos in the entire dataset.

## Can the model read a whole page? (`labbs2026-mekpro-page-feasibility`)

24 images, `PaddleOCR-VL-1.6` @ `c5630ab`, float16, T4, `FULL` only, no pruning,
`max_new_tokens` 768, `table` excluded. This is the gating question, because the
checkpoint's own card states it is a region recogniser trained on crops that has
never seen a whole page.

| subset | n | median CER | truncated | upsampled | `RR_25` discards pixels |
|---|---|---|---|---|---|
| `text` | 11 | **0.0000** | 0 | 9/11 | 6/11 |
| `official` | 13 | 0.2628 | 3/13 | 5/13 | 13/13 |

`text` is read perfectly — and is the wrong regime, mostly upsampled snippets,
the same situation as TEMS.

`official` is the right regime and is read **partially**. Excluding the three
truncations the median is 0.2174 (range 0.0288–0.4859). Two of thirteen exceed
CER 1.0, which happens when the hypothesis is longer than the reference: the
model falls into a repetition loop. The worst case, a 593×679 page, ended with

```
… 2564 ดร 2564 ดร 2564 ดร 2564 ดร 2564 ดร …
```

repeated to the token cap. Raising `max_new_tokens` cannot fix this; the loop
does not terminate.

**The collapses are the large pages.** Restricting to area ≤ 350,000 px gives
n = 8, median CER 0.2136, **zero truncations**. That is the basis for the band
used in the population table, and it is an eight-image basis — it needs
confirming on a larger sample before any design rests on it.

## Independence (`labbs2026-mekpro-independence`)

903 rows is not 903 independent observations, and the dataset has no
`source_photo_id` analogue to cluster on. It is synthetic and template-generated,
so content reuse is the threat that photo-level clustering was in TEMS.

Within the `official` band:

- 903 distinct texts; **no text repeats**;
- but only **413 distinct 30-character openings**, and the most common opening
  appears **110 times**;
- **793 of 4,332 long-sentence instances (18%) are sentences that appear
  elsewhere** in the band.

**The bootstrap cluster unit must be the template, not the row.** That gives
**413 clusters** — eight times what TEMS could offer for this regime, but it must
be designed on 413, not on 903.

## Decisions already forced by the measurements

1. **`table` is excluded outright, not caveated.** Its ground truth serialises
   cells with a pipe character that appears nowhere in the image. Scoring it
   would measure whether the model guesses a formatting convention.
2. **`text` does not serve the purpose.** Mostly below the floor; it reproduces
   the TEMS regime.
3. **Cluster on template openings.**
4. **Page area must be bounded** to keep the baseline collapse rate low.

## Limitations to carry into any write-up

- **Synthetic, and rendered rather than photographed.** No camera noise, no
  perspective, no lighting variation. Moving from TEMS to this corpus trades
  external validity for the ability to test H3 at all, and that trade must be
  stated in the paper rather than left implicit. It is also the same criticism
  the project's earlier synthetic minimal pairs attracted.
- **Reading order becomes live.** Region-level CER had a linear, unambiguous
  order. Multi-line pages do not, and CER is sensitive to it. The ordering rule
  must be fixed before any result is seen.
- **Generation collapse contaminates CER.** The protocol already reports
  truncation, empty and degenerate rates separately and requires truncated items
  to stay in the primary result. At a baseline collapse rate near 23% for
  unbounded pages, the primary estimate would be dominated by collapse dynamics
  rather than recognition — which is why the area bound is not optional.
- **The band itself rests on eight images.** Confirm before designing.

## Not done

No arm designed, no registration written, no Decision Log entry. `wayu` still
unrun. The decoder insertion point remains deferred by the 2026-09-21b entry.
