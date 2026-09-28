# Output diagnostics — what the smoke outputs showed about the metric

**Status: `ENGINEERING_NOTE`**, PELY334, 2026-09-28. Written from 10 outputs of
two engineering smokes on calibration items
(`kaggle-thai-marks-t1-86cf28ec3e85-smoke1`, `kaggle-spec-decode-s1-be7333b19b85-smoke2`).
Not evidence about either model: n = 10, three distinct items. It records how
the scoring pipeline behaves on real outputs, so that registrations in tracks
A-D can pre-specify sensitivity analyses. T1's registered normalization is
not changed by anything here.

Code: `src/labbs2026/output_diagnostics/` (`structural_normalize`,
`loop_period`, `deloop`, `diagnose`), tests in
`tests/test_output_diagnostics.py`.

## 1. What was found

| # | finding | seen in | effect on T1-normalized CER |
|---|---|---|---|
| F1 | The base model with `TYPHOON_CARD` wraps whole transcriptions, tables included, in `<figure>…</figure>`; T1 drops every figure block (correct for Typhoon, whose figures describe pictures) | base, 2 of 4 CARD outputs | 1.000 → **0.091** and 1.000 → **0.012** once text-bearing figures are kept |
| F2 | The base invents table tags (`<row>`, `<cell>`) | base | none — T1's generic tag rule removes them |
| F3 | List markers differ (`*` in Typhoon output, `-` in references); T1 removes `**` but not `*` | Typhoon | small substitution/insertion noise |
| F4 | Loops with a period longer than 200 characters are not flagged by T1's repetition rule | Typhoon CARD `0159AF30` (paragraph repeated to `max_new_tokens`) | CER 0.98 read as misreading; bag precision shows over-generation |
| F5 | Short-period loops inflate CER without bound (insertions) | Typhoon `28987CC6`: CER **47.4**, 0.37 after de-looping | one item can dominate a macro average |
| F6 | In looped or over-generated outputs almost every reference mark counts as "deleted" (e.g. TONE 89/89) | all loop items | mark-error rates mix in the loop rate |

## 2. Consequences for measurement (proposals, not rules)

1. Any comparison of base vs Typhoon on generated text should report, next to
   T1's CER, the structure-aware CER (F1) — otherwise the base's format choice
   is scored as a reading failure. T2 is unaffected (teacher-forced on the
   reference).
2. Every generation metric should be reported per primary cause
   (`format_loss`, `loop`, `omission`, `overgeneration`, `reading_order`,
   `misread`), and mark-error rates **only on `misread`/`reading_order`
   items** (F6). A remedy that merely changes the loop rate would otherwise
   look like a mark fix.
3. Micro CER, or a CER with the hypothesis de-looped, alongside macro CER (F5).
4. For track A's headline population (`SPEC_DECODE_S1_REGISTRATION.md` §5),
   T1's repetition rule misses long-period loops (F4); a sensitivity analysis
   with `loop_period` would need an addendum before the full run.

These are for the track owners to adopt or not in their registrations; for
T1/T2 the decision is Up2mEz's.
