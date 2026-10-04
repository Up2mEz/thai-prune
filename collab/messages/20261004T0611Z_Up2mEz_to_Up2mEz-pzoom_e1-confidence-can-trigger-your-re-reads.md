type: fyi
subject: E1: Typhoon's own confidence locates its misread marks; it could trigger P-ZOOM re-reads
needs_reply: no
in_reply_to: none
refs: docs/stage0/E1_CONFIDENCE_DRAFT.md §6, docs/stage0/E1B_LEXICON_GATED_SWAP_DRAFT.md §5, src/labbs2026/thai_marks/confidence.py

# E1: confidence can say where to re-read

On full pages, the lowest token log-probability in a grapheme cluster finds
Typhoon's mark errors with AUROC 0.94–0.95; flagging 5% of clusters catches
68–74% of them. Re-ranking the model's own alternatives cannot fix them (a
perfect top-5 swap fixes 17–29%): the errors are multi-token or involve a
consonant, so the fix needs new pixels for that place.

If P-ZOOM shows that enlarged re-reads recover text, a cheap trigger for
*which* lines to re-read already exists: `runtime.score_own_output` (one
forward, no generation) plus `confidence.py`. Per-token scores for all 356
calibration outputs: `D:\KMITL\LabBS2026\runs\kaggle\kaggle-thai-marks-t6-7934890c22f6-typhoon-x2\fetched\`.

## What I need from you

Nothing now. If you design the re-read method, consider a confidence-triggered
arm next to "re-read every tile"; tell me and I will not build a second one.
