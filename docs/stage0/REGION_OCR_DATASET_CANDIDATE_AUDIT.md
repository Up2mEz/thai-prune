# Region OCR — Dataset Candidate Audit

> Status: `SURVEY_COMPLETE_PENDING_HUMAN_SELECTION`
>
> Authorization: **NONE**. No dataset was downloaded, opened, or used.
>
> Audited: 2026-09-20 from dataset cards, publisher pages, and papers.

## 1. The binding filter

Moving the unit of analysis to the text region changed what the dataset must
provide. The models are region recognizers, so ground truth must exist **per
region**, in one of two shapes:

- (a) pre-cropped text-region images with transcriptions, or
- (b) full images with region-level bounding boxes plus transcriptions.

A corpus with only page-level running text is unusable here, because deriving
regions from it would require a layout detector — reintroducing exactly the
uncontrolled, un-pruned stage the region design removes.

This filter alone eliminates both candidates named in the original plan.

## 2. Candidates

| Dataset | Real/Synth | Region GT | Size | Distinct source images | License | Verdict |
|---|---|---|---|---|---|---|
| **TEMS** (Thai–English Multiscript Text Image) | Real smartphone photos, 9 Thai provinces, 2023-11..2024-11 | **Yes, shape (a)** — cropped JPEGs + metadata CSV | 5,000 crops, 148 distinct chars in released labels | **1,237** (verified) | **CC BY 4.0** | **PRIMARY CANDIDATE, conditional on §3.2** |
| ThaiOCRBench fine-grained subset | Mostly real; some ID samples synthetic | **Unconfirmed** — bbox-looking strings seen, but not verified to be a structured field | subset of 2,808 across 13 tasks | not published per task | **CC-BY-SA-4.0** (card) | CONDITIONAL SECONDARY |
| `iapp/thai_handwriting_dataset` | Real handwriting, 2,026 writers | Yes, line crops | 13,550 | 4,920 sentences | Apache-2.0 *asserted by republisher* over NECTEC BEST-2019 + a commercial set | MARGINAL — handwriting arm only |
| `mekpro/ocr_th` | Synthetic | **No** — page-level text only | 4,000 | n/a | Apache-2.0 | **REJECTED** |
| `openthaigpt/thai-ocr-evaluation` | Real | **No** — page-level only | 104 rows | ~104 | CC-BY-SA-4.0 | REJECTED — no boxes, too few clusters |
| `SEACrowd/kvis_th_ocr` | Real scans | Single characters only | 1,079 | 27 writers | — | REJECTED — no diacritic context |
| ICDAR MLT 2017 / 2019 | Real | Yes | — | — | — | **REJECTED — contains no Thai.** MLT17 covers 9 languages / 6 scripts; MLT19 adds Hindi. Thai is in neither. |
| Union14M | Real | Yes | — | — | — | REJECTED — English only |
| DataoceanAI Thai Natural Scene OCR | Real | Yes, line-level | 13,882 | 13,882 | **Commercial vendor, no public license** | REJECTED — not publication-safe without written terms |
| FutureBeeAI Thai OCR sets | Real | Vendor-claimed | — | — | Commercial, terms not public | REJECTED — same reason |
| Suwanwiwat et al. multi-script Thai scene text | Real | Script-class oriented | — | — | **Could not verify** — paywalled, no public download located | UNVERIFIED |

## 3. TEMS — verified structure

Verified by fetching the Mendeley v5 record, its README, and the full metadata
CSV, and by computing over all 5,000 rows. Only public metadata was read; no
model inference occurred and nothing was added to this repository. An earlier
second-hand summary described the v3 documentation and was wrong on several
points, which are corrected below.

Release: `ntdmgksh9w-5.zip`, 27.1 MB, sha256 `7002f644…52da9`, version 5
published 2026-07-13. Mendeley record licence: **CC BY 4.0** (attribution only;
benchmarking and publication permitted).

### 3.1 Region ground truth and page grouping — both confirmed

**Page grouping is recoverable.** The metadata CSV's first column is
`source_photo_id`. Paper §2.5 states it "identifies the original source
photograph from which each cropped text image was extracted … supporting
source-image-level partitioning, data leakage prevention, and traceability."
Example values: `billboards_18`, `road signs_147`, `publication covers_353`.

Computed over all 5,000 rows:

| Property | Value |
|---|---|
| Blank `source_photo_id` | 0 |
| Distinct source photos (= cluster count) | **1,237** |
| Crops per photo | min 1, median 3, mean 4.04, max 44 |
| Single-crop photos | 328 |
| Source photos spanning more than one split | **0** |

**Use the CSV `label` column, not the filename.** Ground truth appears in both,
and they disagree on **80 of 5,000 filenames (1.6%)**: the filename is a
filesystem-sanitised, sometimes lossy variant (apostrophes became `_`, trailing
spaces stripped, some dates expanded — e.g. filename `22 สิงหาคม 2565` vs label
`22-ส.ค.-65`). Reading ground truth from filenames would silently corrupt 1.6%
of the reference text.

CSV schema (UTF-8 with BOM): `source_photo_id, image_id, filename, label,
file_size_mb, script_type, text_length, image_width, image_height, split`.
No Unicode normalization was applied by the authors, but all labels are
NFC-stable in practice (0 labels change under NFC), consistent with this
project's no-normalization primary policy.

The authors' own splits (train 3,989 / valid 497 / test 514) are already
photo-level leakage-safe, so they can be reused instead of re-splitting.

### 3.2 The blocking issue: crops are far too small for the budget grid

Computed crop dimensions over all 5,000 images:

| Dimension | Range | Median | Mean |
|---|---|---|---|
| Width | 47–1,438 px | 262 | 285 |
| Height | 18–275 px | 49 | 55 |

Median area ≈ 12,950 px². At `patch 14 → merge 2`, one post-merge visual token
covers a 28×28 px region, so a median crop at native resolution yields on the
order of **~17 visual tokens**. The budget grid would then be roughly
17 → 13 → 8 → 4, where grid quantization dominates and Resolution Reduction
cannot land near its targets. That is a degenerate design.

This is not fatal, but it forces a **scale policy** that must be frozen before
execution. The processor exposes `min_pixels`/`max_pixels`, and the existing
frozen design already uses `force_equal_min_max_pixels: true`, so each crop can
be resampled to a fixed pixel budget that produces a workable `N` while
preserving aspect ratio. Two consequences must be stated wherever results are
reported:

- Upscaling adds tokens, not information. `FULL` is therefore "the model's
  preferred operating resolution for this crop", not "all available detail".
- Because aspect ratios vary, `N` still varies per crop, so the per-region
  budget-matching rule in the protocol remains necessary.

### 3.3 Component coverage — adequate, with one gap

Counted over all released labels:

| Class | Tokens | Images containing |
|---|---:|---:|
| Tone marks (U+0E48-U+0E4B) | 2,280 | 1,379 |
| Upper vowels (U+0E31, U+0E34-U+0E37, U+0E47) | 4,345 | 2,057 |
| Lower vowels (U+0E38, U+0E39) | 918 | — |
| Lower vowel U+0E3A (phinthu) | **0** | 0 |

Tone marks and upper vowels are well represented, so the diagnostic is viable.
U+0E3A is absent entirely, which is unsurprising for modern signage but must be
declared rather than reported as a zero result. `STACKED_TONE_MARK` is not a
labelled field and would have to be derived from base+upper-vowel+tone-mark
sequences in the label text.

### 3.4 Remaining risk: domain mismatch

TEMS is *scene* text — signage, menus, packaging. Both selected models are
*document* OCR models, and the specialized one was trained on synthetic
document pages. This is off-distribution use, and poor `FULL` performance would
be confounded with the intervention. This risk is unchanged by the verification
above and is exactly what the Phase-1 smoke exists to measure.

### 3.5 Corrections to the record

- Cluster count is **1,237**, not the 1,625 claimed in the paper. The
  discrepancy (train 1,011 / valid 114 / test 112) is unexplained in both the
  paper and the README; the released data governs.
- Released labels contain **148** distinct characters, not 161. The 161 figure
  refers to the source-photograph analysis stage, not the released crops.
- The paper's stated width range (45–1,512) does not match the released
  metadata (47–1,438).
- The README is a stale v3 document: it lists 9 CSV fields and omits
  `source_photo_id`.
- Parent photographs and XML annotations are **not** distributed — §2.8 states
  they "are currently being used in ongoing research". Only crops plus the
  source ID are released, so alternative crop policies cannot be re-derived.

## 4. ThaiOCRBench — conditional, with two unresolved checks

Better domain match (documents) but weaker on governance:

- The card declares **CC-BY-SA-4.0**, while the paper is CC BY 4.0. Treat the
  ShareAlike card licence as binding: redistributed derivative crops would
  inherit it.
- Provenance includes "licensed commercial datasets" whose upstream terms are
  not enumerated. For a project that already lost a branch to upstream terms,
  this is a real residual risk rather than a formality.
- Whether a structured bounding-box field exists could **not** be confirmed from
  the card. This must be verified by loading the split before any reliance.

The existing Typhoon prohibition is scoped to the Typhoon *model* branch and
says nothing about this dataset; that is a reason to read the dataset's terms
independently, not a reason to assume either clearance or prohibition.

## 5. Selection rule — to be frozen before any pruning outcome

The corpus is **not** selected on pruning results. It is selected on
measurement adequacy, declared in advance and evaluated before the scientific
run. Steps 1 and 2 are already discharged for TEMS by §3:

1. ~~Component coverage~~ — **done** (§3.3): adequate for tone marks and upper
   vowels; U+0E3A absent and must be declared.
2. ~~Cluster structure~~ — **done** (§3.1): 1,237 photo-level clusters,
   leakage-safe splits already provided.
3. **Freeze the scale policy** (§3.2) — choose the fixed pixel budget that
   yields a workable `N`, preserving aspect ratio, before any outcome is seen.
   Record the resulting `N` distribution and confirm that `0.75N / 0.50N /
   0.25N` remain distinct after grid quantization for the large majority of
   regions. Regions where they do not must be identified by a pre-declared rule,
   not dropped after inspection.
4. **Measure `FULL` baseline CER** for both models on a small sample. If no
   corpus leaves room for degradation to be observable, stop and report that to
   the human rather than proceeding (§3.4 is the live risk here).
5. Freeze corpus, split, scale policy, and crop policy before the scientific run.

This mirrors the precedent already set in this repository: image size was
chosen from legibility and machine capability before OCR scores were examined,
and the Qwen3.5 backbone was pre-registered on measurement-capacity grounds
with a prohibition on retrospective rationale.

## 6. Consequence for the fallback

A real-imagery Thai corpus with region-level annotations and a
publication-safe licence **does exist and is obtainable**. The synthetic
rendering fallback is therefore demoted from "likely route" to "used only if
both TEMS and ThaiOCRBench fail the §5 checks."

If it is ever used, the vendored fonts are SIL OFL 1.1 with pinned commit and
SHA-256 recorded in `assets/fonts/noto/SOURCE.md`, and the existing shaping and
rasterization primitives in `src/labbs2026/stage0/rendering.py` accept arbitrary
text and canvas dimensions, so line rendering is a wrapper rather than a new
renderer. The text corpus would itself require separate licence clearance.

## 7. Not verified

- per-task sample counts in ThaiOCRBench, and whether its bbox data is a
  structured field;
- availability and terms of the Suwanwiwat et al. dataset;
- all commercial vendor licences;
- upstream NECTEC BEST-2019 terms behind the `iapp` republication.
