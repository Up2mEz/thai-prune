# E5 — synthetic pages with known lines: does omission follow density, size, or content?

**Status: `APPROVED` by the researcher in session on 2026-10-12** ("ทำสิ่งที่ต้องทำเพิ่มข้อ 2, 3, 5"), written
**before any E5 output exists**. Typhoon only. Claim level `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. **Synthetic: every
result is a controlled probe and is never described as real-world evidence.** Decision Log 2026-10-12d (gaps).

## 1. Question

On ThaiOCRBench, Typhoon leaves out whole lines, mostly text in graphics, advertisements and page furniture
(`TYPHOON_FAILURE_PROFILE.md` §2d). The benchmark cannot separate what a line *is* from how many lines compete with
it, or how large they are, because every page differs in everything. On a synthetic page the text is the same kind
everywhere and each line's box is known. E5 asks, on clean text:

1. Is a line omitted more often when the page holds more lines (density)?
2. More often when the text is smaller (size)?
3. For a line omitted in the page, is it found when it is the only content left on a page-sized canvas
   (`masked`, same image size and token count) or in a tight crop of it (`tight`)?
4. Given a line is found, are its marks misread more often on denser pages?

If clean text is almost never omitted, that is the finding: omission on real pages comes from what the page
contains, not from line count or size.

## 2. Pages and reads (Typhoon, `TYPHOON_CARD`, greedy as T1, fp16): 378

- **Pages:** 54 = 3 line counts (4, 10, 18) × 3 font sizes (24, 32, 44 px on an A4 page at 150 dpi) × 6 pages.
- **Text:** lines of random Thai dictionary words (`pythainlp` word list, 2 to 8 characters, consonants, vowels and
  marks only), in groups of 2 to 4 words separated by spaces, filled to the page's text width. Each line holds at
  least 4 marks. The words carry no meaning, so the language prior is weakened; this is stated beside every number.
- **Rendering:** matplotlib 3.11 (Raqm text layout shapes stacked vowels and tone marks; checked by eye), Noto Sans Thai
  (`assets/fonts/noto`), black on white, deterministic from the seed (20261012). Per-line boxes come from the renderer.
- **Per page, 3 lines are sampled** (seeded) and each is also read in two views, 324 reads:
  - `line_tight`: the tight crop (14 px padding), through `runtime.resize_policy`;
  - `line_masked`: the line alone on a page-sized white canvas at its place, through `runtime.resize_policy`
    (same size and visual-token count as the page read).
- **Code:** `synthetic_pages.py`, `scripts/thai_marks_e5_cases.py` (the cases JSON carries the images, base64), the
  worker's `e5` test, `configs/thai_marks/e5.yaml`. 2×T4, about 1 GPU-hour, own quota.

## 3. Measures, fixed before any output is read (`e5_analysis`)

Lines are located in the output as P-ZOOM located them (`p_zoom_analysis.score_page`, `READ_ELSEWHERE_CER` 0.2).

- **Omitted share** per cell: marks in reference lines not found, over the cell's reference marks; 95% bootstrap over
  pages (seed 20261012, 2,000 resamples).
- **Misread share in found lines:** marks of found lines not read correctly, over the marks of found lines.
- **D1 (density):** omitted share of the 18-line pages minus that of the 4-line pages, all sizes pooled, with a paired-free
  two-sample page bootstrap.
- **D2 (size):** omitted share at 24 px minus at 44 px, all line counts pooled, likewise.
- **Line arms:** among sampled lines omitted in the page read, how many are found in `line_masked` and in
  `line_tight`; also lines found in the page but not in `line_masked` (a check on the masked view).
- **Cost:** reads, generated tokens, loops (`reached_max_new_tokens`) per kind.

## 4. Readings, fixed in advance

A contrast is *material* when its 95% interval excludes 0 and its estimate is at least 5 points (a judgement).

| outcome | reading |
|---|---|
| omitted share overall under 2% of reference marks | Clean synthetic text is almost never omitted. Omission on ThaiOCRBench is not explained by line count or size alone, and is likely tied to page content (graphics, advertisements, layout). D1, D2 and the line arms are reported, not read. |
| D1 material | more lines on the page means more omission, at fixed text style |
| D2 material | smaller text means more omission |
| line arms, at least 10 omitted sampled lines: ≥ 50% found in `line_masked` | omitted lines are readable alone at the same image size, so what hides them is the other lines (competing content) |
| line arms: under 50% in `line_masked`, ≥ 50% in `line_tight` | what hides them is image size or zoom, not the other lines |
| line arms: under 50% in both | omitted lines cannot be read alone at this scale: a recognition limit |
| fewer than 10 omitted sampled lines | no reading of mechanism |
| misread share in found lines does not rise with the line count | marks are read correctly once a line is found, at any density |

n = 54 pages, so **direction, not magnitude**. No outcome is called "equivalent".

## 5. What this does not decide

- It does not show that the same holds for real pages: the text is clean, black on white, with no graphics.
- Random words are not language. Typhoon may behave differently on meaningful text; a follow-up with sentences would
  be a new registration.
- It evaluates no remedy.

## 6. Cost and stopping

Smoke first (the first two cases), then the full run. No read is repeated to change a result; a failed read is
listed.

## 7. Result (2026-10-12)

Run `kaggle-thai-marks-e5-ddad6b7569b2-typhoon-x2` (git `ddad6b7`), 378 reads, 0 failures, checksums verified, 2×T4,
fp16, 0.55 GPU-hours, cases hash `a8ed5403…` (regenerated byte-identically by `scripts/thai_marks_e5_cases.py`).
Scored by `scripts/thai_marks_e5_analyze.py` (`docs/stage0/data/E5_SUMMARY_ddad6b7569b2.json`). Raw outputs checked
before scoring: no markup in any output (0 of 54 pages contain `<`), every page's output has the reference's number
of lines but one (a 4-line page returned as one line with all the text).

**Registered reading: clean synthetic text is almost never omitted.** The omitted share is **0.0% in all nine cells**
(every line of all 54 pages was found), so D1 (density), D2 (size) and the line arms (0 omitted sampled lines of 162)
are reported and not read, as registered.

| cell (line count, px) | omitted marks | misread marks in found lines |
|---|---|---|
| 4 lines, 24 / 32 / 44 | 0.0% / 0.0% / 0.0% | 4.2% / 1.8% / 1.4% |
| 10 lines, 24 / 32 / 44 | 0.0% / 0.0% / 0.0% | 5.2% / 2.4% / 0.6% |
| 18 lines, 24 / 32 / 44 | 0.0% / 0.0% / 0.0% | 4.0% / 2.2% / 1.3% |

**Exploratory, not registered** (computed after the registered readings, labelled as such):

- Misread share in found lines by text size, pooled over line counts: **4.4% at 24 px** [3.6, 5.2], 2.2% at 32 px
  [1.5, 2.9], 1.1% at 44 px [0.5, 1.7]. By line count: 2.8% (4 lines), 3.2% (10), 2.8% (18). Smaller text costs
  marks; more lines do not.
- Sampled lines, marks read correctly: tight crop 97.6% against 97.2% for the same lines inside the page; masked
  canvas 95.2% against 97.2%. Reading a line alone does not improve its marks. 162 of 162 sampled lines were found
  in the page, 162 in the tight crop and 161 in the masked canvas.
- Three raw outputs read by hand show the pattern of the misreads: a consonant swap, a vowel mark moved to the
  neighbouring consonant, and a tone mark changed (`เชื้อ` read `เชื่อ`, the commoner word). Three examples are an
  illustration, not a count.

**What this shows, and does not.** On clean black-on-white text of random words, Typhoon omits no line at any tested
density (up to 18 lines) or size (down to 24 px). The lines it omits on ThaiOCRBench are therefore not explained by
line count or text size alone, and are more likely tied to what the page contains (graphics, advertisements, layout).
It does not show that this holds for real pages, for meaningful text, or for other models. Marks are an exception to
"nothing depends on density": their error rate depends on size, not on the number of lines.
