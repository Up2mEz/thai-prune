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

### 3.2 Crop size and the budget grid — resolved by the processor defaults

**Resolution (2026-09-20), measured.** The concern below was real at native
resolution but is answered by the processor's own configuration. The pinned
PaddleOCR-VL-1.6 processor declares `min_pixels: 112896`, `max_pixels: 1003520`,
`patch_size: 14`, `merge_size: 2`, and upsamples anything below the floor.

An earlier draft of this section projected a constant **144** placeholders by
dividing `min_pixels` by 784. **That was wrong in detail.** The processor's
`smart_resize` rounds each side up to a multiple of 28 px, so it overshoots the
floor by a shape-dependent amount. Running the actual processor over all 5,000
released crop dimensions gives:

| Quantile | p1 | p5 | p25 | median | p75 | p95 | p99 |
|---|---|---|---|---|---|---|---|
| Placeholders | 145 | 148 | 154 | **160** | 168 | 175 | 180 |

with min 144, max 405, 33 distinct values, and **0 regions whose
`FULL/75/50/25` grid degenerates**. The count is not monotonic in crop area —
a 360×60 crop yields 150 placeholders while a smaller 262×49 crop yields 168 —
because `smart_resize` chooses the grid shape, not just its size.

So no arbitrary scale policy has to be invented: `FULL` is the processor's
default operating point, which is also the deployment behaviour. `N` sits in a
narrow 144–180 band for 99% of regions, and the per-region budget-matching rule
in the protocol does real work because `N` genuinely varies.

Method validated against the existing frozen record: feeding a 448×448 control
through the same path reproduces `grid [1,32,32]`, 1,024 pre-merge, **256**
placeholders, matching `PADDLE_WAYU_PROCESSOR_GEOMETRY.json`. Full measurement
is recorded in `docs/stage0/REGION_OCR_PROCESSOR_GEOMETRY.json`
(`PROCESSOR_ONLY_NO_MODEL_INFERENCE`).

**Residual scientific caveat.** A median crop carries roughly 11 tokens' worth
of native detail but is presented to the model as 144 tokens, so most tokens are
interpolated redundancy. This is the model's genuine operating point rather than
something the design imposes, but it biases the experiment towards finding
pruning harmless. A *positive* result under this redundancy is therefore strong;
a *null* is correspondingly weak and must be reported with this caveat attached
rather than as evidence that pruning is safe.

### 3.2.1 The original concern, at native resolution

Computed crop dimensions over all 5,000 images:

| Dimension | Range | Median | Mean |
|---|---|---|---|
| Width | 47–1,438 px | 262 | 285 |
| Height | 18–275 px | 49 | 55 |

Computed directly over the released metadata, native-resolution token counts are
p5 = 4, p25 = 7, **median = 11**, p75 = 20, p95 = 44. 4,382 of 5,000 regions
(88%) fall below 32 tokens and 3,330 (67%) below 16. At the median the grid
would be 11 → 8 → 5 → 2, which destroys the input rather than compressing it,
and 214 regions cannot produce four distinct budget levels at all.

Filtering to naturally large regions does not rescue this: only 618 regions
(441 clusters) reach 32 native tokens, 87 regions (77 clusters) reach 64, and
17 reach 128. Region size tracks capture resolution rather than text length —
median `text_length` stays at 12-14 characters across every size band — so
discarding small crops would cost almost the whole corpus without buying longer
text.

Native resolution is therefore unusable, which is what makes the processor's
own upsampling floor in §3.2 the operative answer.

### 3.2.2 Almost half the corpus carries no Thai at all

TEMS is a Thai–**English** multiscript corpus, and the released `script_type`
column shows that a large part of it is irrelevant to this study:

| `script_type` | Regions | Photos | Regions containing Thai |
|---|---:|---:|---:|
| English | **2,297** | 772 | **0** |
| Numeric and Special Characters | 42 | 40 | **0** |
| Thai | 2,174 | 818 | 2,174 |
| Mixed Thai-English | 487 | 311 | 487 |

Eligibility is therefore decided on the label itself — at least one codepoint in
U+0E00–U+0E7F — rather than by trusting the metadata column. The **effective**
corpus is:

| Split | Thai-bearing regions | Clusters |
|---|---:|---:|
| train | 2,070 | 747 |
| valid | 270 | 87 |
| test | 321 | 93 |
| **total** | **2,661** | **927** |

So the usable corpus is 2,661 regions across 927 source photographs, not the
headline 5,000 / 1,237. That is still far above the clustering threshold, and
median `text_length` among Thai-bearing regions is 17 characters rather than 14.

An unfiltered sample would have been dominated by English signage: the first
selection attempted here returned "THE ORIGINAL THAI BEER", "NET CONTENTS
320 ml." and similar, which carry no Thai orthography whatsoever.

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
