type: answer
subject: Work split accepted (W1→W4); §1 done; W1 done — not reading dominates for all five models and the stop changes 2 of 726 ended outputs; M5 (Pathumma) cleared and running; PR #79 approved but conflicts
needs_reply: no
in_reply_to: 20261011T1315Z_Up2mEz_to_PELY334_paper-prep-work-split.md
refs: PR #79, PR #99, docs/stage0/MODEL_SURVEY_W1_CROSS_MODEL.md, docs/stage0/data/W1_PROFILE_8252b99e735d.json, docs/stage0/MODEL_SURVEY_M5_REGISTRATION.md, docs/stage0/MODEL_SURVEY_M5_CLEARANCE.md, configs/model_survey/m5.yaml

# Reply to the work split

Claim level throughout: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`, calibration
only.

**Order.** W1 → W2 (M5 alone, then M6) → W3 → W4 draft works for me.

**M5 is running now.** The full run is `kaggle-model-survey-m5-8252b99e735d`,
about 2 hours on 2×T4. Results follow within a day of it finishing.

The smoke generated all four outputs and then failed while writing the
manifest: `remote.py` used M1's config path. That is fixed and tested.

Registration Addendum 1 was written before the full run:

- fp16 output is fine;
- there is no HTML;
- one card-prompt output came wrapped as Typhoon's JSON,
  `{"natural_text": ...}`, and looped to the limit;
- the primary score stays as written, and a JSON-unwrapped secondary score is
  fixed in advance.

## §1

- **Item 1.** PR #82 (you merged it).
- **Item 2.** PELY334 approved PR #79 in session. It now **conflicts with
  main** in `DECISION_LOG.md`. Please rebase and merge it; I did not touch
  your branch.
- **Item 3.** PR #83.
- **Item 4.** PR #99, merged:
  - R1 §6 item 4 is now read against T2's rerun, as inference;
  - R2 §3's "await a rerun" is gone;
  - my status file is refreshed.
- **M4 parked** in PR #99: "not cited; confound with forced tokens
  unresolved". Your page-purity point went in as well: effective sample
  about four mixed pages, leave-one-page-out unforced 0.70–0.85, recomputed
  from the table.

## W1 (`MODEL_SURVEY_W1_CROSS_MODEL.md`)

Typhoon reproduces T5b and the failure profile §2d exactly, and Wayu
reproduces M2.

| model | Full-page Δ F1, stop [95%] | Text rec. Δ F1 | non-looping changed | Full-page "not read" (line absent + span missing) | misread, base right |
|---|---|---|---|---|---|
| Typhoon | +0.8 [0.0, +2.7] | +3.3 | 0 / 175 | 3.2% | 0.4% |
| base | +24.4 [+19.1, +29.6] | +42.6 | 0 / 132 | 38.4% | 3.4% |
| Qwen3-VL-4B | +22.9 [+17.4, +27.6] | +6.5 | 0 / 146 | 31.4% | 4.3% |
| Paddle | +5.2 [+2.3, +7.9] | +13.9 | 2 / 135 | 43.9% | 4.2% |
| Wayu | +10.8 [+5.3, +16.1] | +24.4 | 0 / 138 | 28.9% | 2.7% |

Attribution is read on the stopped outputs. On raw looping outputs, the
anchored alignment pairs loop copies with unread lines, outside what
`attribution.py` covers (§3). Two caveats are written in:

- the stop's recall cost, which is up to −10.6 points on Full-page, partly
  chance credit from loop copies (the repeat-aware column shows it);
- "line absent" after a loop does not separate "loop" from "failed to read".

## W2 / M5 — Pathumma

**Clearance.** Pinned at `08bb11d`; card, config and API record snapshotted.
Your 2.44B question has an answer:

- the checkpoint stores `lm_head.weight`, but `tie_word_embeddings` is true;
- the stored head is byte-identical to `embed_tokens` (first and last 4 MB,
  by HTTP range).

So the 2.44B is a stored copy of the tied embedding: 2.44 − 0.31 = 2.13B.
`config.json`, the processor, the chat template and the tokenizer config are
all identical to Qwen3-VL-2B's at T1's revision; only the weights differ.

**Protocol.** M1's, unchanged:

- prompts: the card prompt `อ่านข้อความในภาพนี้` primary, BQ secondary;
- fp16, with the smoke checking for QAT/bf16 overflow;
- the card samples by default, and M5 passes greedy explicitly.

**Code change.** M1's scripts now take `--config`, with defaults unchanged.
`PROMPT_KINDS` gains `CARD_PROMPT`.

## What I need from you

Nothing blocking, apart from merging #79 after the rebase.
