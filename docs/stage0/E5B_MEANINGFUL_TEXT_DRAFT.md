# E5b — E5 again with meaningful text: does the language prior change omission or marks?

**Status: `APPROVED` by the researcher in session on 2026-10-12** ("ทำ E4b E5"), written **before any E5b output
exists**. Typhoon only. Claim level `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. **Synthetic: every result is a controlled
probe and is never described as real-world evidence.** Decision Log 2026-10-12f (gaps). Follows E5
(`E5_SYNTHETIC_OMISSION_DRAFT.md` §7).

## 1. Question

E5 found no omitted line on clean synthetic pages (0.0% in all nine cells), and found that marks are misread more
often at small sizes (4.4% at 24 px, 1.1% at 44 px) and not more often with more lines. Its text was random
dictionary words, so the language prior was weakened. E5b changes **one thing**, the text, and keeps the page layout
grid, sizes, renderer, prompt and decoding:

1. Is a line omitted when the text is meaningful? (E5 said no for random words.)
2. Does the share of misread marks in found lines change, against E5's random-word pages with the same layout?
   A prior could help (frequent words are spelled from memory) or hurt (a frequent word replaces the one on the
   page; E5's hand-read example `เชื้อ` read `เชื่อ` already points that way).

## 2. Pages and reads (Typhoon, `TYPHOON_CARD`, greedy as T1, fp16): 54

- **Pages:** the E5 grid: 3 line counts (4, 10, 18) × 3 sizes (24, 32, 44 px, A4 at 150 dpi) × 6 pages = 54, black on
  white, Noto Sans Thai, matplotlib 3.11, same seeds as E5 (the page seed picks the phrases here, not words).
- **Text:** phrases from a small hand-written lexicon (`thai_sentences.py`): a time phrase, a subject, a verb with its
  object, and sometimes a place, for example `ทุกเช้า คุณครู ตรวจเอกสารสำคัญ ที่ศาลากลางหมู่บ้าน`. Every combination is
  grammatical and sensible. The sentences are **templated, not natural prose**: they come from a closed set of 10 time
  phrases, 12 subjects, 20 verb phrases and 8 places, there is no punctuation, and consecutive sentences are unrelated.
  Phrases are separated by a space, and lines are filled to the page's text width; each line holds at least 4 marks.
  The lexicon is hand-written and does not come from any benchmark.
- **Not run in E5b:** the per-line tight and masked reads of E5 (no omitted line existed to explain); E5b reads pages only.
- **Code:** `thai_sentences.py`, `scripts/thai_marks_e5_cases.py --text sentences --no-line-views`, the worker's `e5`
  test, `configs/thai_marks/e5b.yaml`. 2×T4, under 0.3 GPU-hours, own quota.

## 3. Measures, fixed before any output is read (`e5b_analysis`, built on `e5_analysis`)

- **Omitted share** per cell and overall (marks of reference lines not found, over reference marks), 95% bootstrap over
  pages (seed 20261012, 2,000 resamples), lines located as in E5.
- **D1 / D2:** density (18 minus 4 lines) and size (24 minus 44 px) contrasts of the omitted share, as in E5.
- **Misread share in found lines** per cell.
- **D3 = misread share (meaningful) − misread share (E5 random words)**, all pages pooled, and per size; two-sample page
  bootstrap (pages are not paired: the text differs).
- **Cost:** reads, generated tokens, loops per page.
- **Raw outputs:** checked for markup and for line-count mismatches before scoring, as in E5.

## 4. Readings, fixed in advance

| outcome | reading |
|---|---|
| overall omitted share under 2% of reference marks | `clean_meaningful_text_almost_never_omitted`. Meaning does not make Typhoon omit lines on a clean page either. D1 and D2 are reported, not read. |
| overall omitted share at least 2% | Omission appears with meaningful text; D1 and D2 are read by E5's rule (material when the 95% interval excludes 0 and the estimate is at least 5 points). The cause is then not tied to a feature of E5's random words. |
| D3 material (95% interval excludes 0 and \|estimate\| at least 1 point; a judgement) and positive | `meaningful_text_more_misreads`: marks are misread more often in meaningful text than in random words at the same layout. |
| D3 material and negative | `meaningful_text_fewer_misreads`: the language prior helps marks. |
| D3 not material | `no_difference_shown`. This does not say the two are equal. |

n = 54 pages (and 54 in E5): **direction, not magnitude**. No outcome is called "equivalent".

## 5. What this does not decide

- It does not show anything about real pages. The page is clean, black on white, with no graphics, advertisements or
  mixed sizes; E5 and E5b together say only that those are not enough to make Typhoon omit a line.
- Templated sentences are not natural Thai. A different text source (real prose) would be a new registration.
- A mark error that is a real Thai word (a tone mark swapped for another that gives another word) is scored as an
  error, as in E5; the scorer does not know about the prior.
- It evaluates no remedy.

## 6. Cost and stopping

Smoke first (the first two pages), then the full run. No read is repeated to change a result; a failed read is listed.

## 7. Result (2026-10-13)

Run `kaggle-thai-marks-e5-1e15847649a9-typhoon-x2` (git `1e15847`), 54 reads, 0 failures, checksums verified, 2×T4, fp16,
0.30 GPU-hours, cases hash `89535fd4…` (regenerated by `scripts/thai_marks_e5_cases.py --text sentences
--no-line-views`; the E5 cases still regenerate to `a8ed5403…`). Scored by `scripts/thai_marks_e5b_analyze.py`
(`docs/stage0/data/E5B_SUMMARY_1e15847649a9.json`) against the E5 run. Smoke first (2 pages, 0 failures).

**Registered reading: `clean_meaningful_text_almost_never_omitted`.** The omitted share is **0.0% in all nine cells**
(every line of all 54 pages was found, up to 18 lines at 24 px). D1 and D2 are 0.0 and are reported, not read.

**D3 (misread marks in found lines, meaningful minus E5 random words): −2.9 points** [−3.5, −2.3], reading
`meaningful_text_fewer_misreads`. The misread share is **0.0% in every cell** (0 marks wrong in 54 pages); E5's random
words gave 4.4% at 24 px, 2.2% at 32 px and 1.1% at 44 px, so D3 by size is −4.4, −2.2 and −1.1 points, each interval
excluding 0.

**Raw outputs checked after scoring** (as in E5; the check is not a registered measure): no output contains markup
(0 of 54); 53 of 54 outputs equal the reference once line breaks are ignored; Typhoon rewrapped the text into a
different number of lines on 37 of 54 pages (line breaks are not scored, lines are located by content); no loops.

**What this shows, and does not.** On clean templated Thai phrases Typhoon omits no line and misreads no mark, at any
tested density or size. Against E5's random words the difference in marks is the whole of E5's error. Two readings fit
and E5b cannot separate them: the language prior corrects what the pixels leave ambiguous, or the closed phrase set
(about 50 phrases, repeated across pages) is simply easy to reproduce from memory of common words. The second reading
weakens any claim that meaningful text is "read better": these sentences are templated and repetitive, not natural prose.
The 0.0% is not a rate for real Thai documents. Together with E5, omission on ThaiOCRBench is not explained by line
count, text size, or whether the clean text is meaningful; the lines it omits are more likely tied to what the page
contains (graphics, advertisements, layout). That last step is an inference, not tested here.
