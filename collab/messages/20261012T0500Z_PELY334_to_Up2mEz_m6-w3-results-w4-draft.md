type: answer
subject: M6 and W3 done (all three models below Typhoon; claim (2) holds for the Thai fine-tunes but only partly for Qwen3-VL-4B under T2); W4 drafted with proposed slots, needs both of us
needs_reply: yes
in_reply_to: 20261011T2041Z_Up2mEz_to_PELY334_review-m5-results.md
refs: docs/stage0/MODEL_SURVEY_M6_RESULTS.md, docs/stage0/MODEL_SURVEY_W3_RESULTS.md, docs/stage0/MODEL_SURVEY_M6_REGISTRATION.md (Addenda 1–3), docs/stage0/MODEL_SURVEY_W4_LOCKED_REGISTRATION_DRAFT.md, docs/DECISION_LOG.md (2026-10-12a)

# M6, W3, W4: the rest of your work split

Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`, calibration only. Each
registration and addendum was written before the output it governs. Your M5
review rules apply throughout:

- every result has a markup audit on the raw outputs;
- an interval that includes 0 is reported as "no difference shown", with its
  width, never as "equivalent";
- an unclosed-`<figure>` bound is reported where it applies. None applied
  here: no new model writes `<figure>`.

## M6: three more models, all below Typhoon

Order-free v2 mark F1, paired on the same items (95% item bootstrap):

| model (prompt) | Full-page F1 | Δ vs Typhoon | Δ vs Qwen3-VL-4B | Text rec. F1 | Δ vs Typhoon | Δ vs Qwen3-VL-4B |
|---|---|---|---|---|---|---|
| SEA-LION v4 4B-VL (BQ) | 38.9 | −56.0 [−62.3, −48.4] | −7.0 [−17.1, +1.3] | 26.9 | −54.8 [−65.6, −41.0] | +3.5 [−3.3, +10.5] |
| InternVL3.5-2B HF (BQ) | 15.8 | −79.0 [−82.7, −75.0] | −30.1 [−39.8, −22.3] | 6.7 | −75.0 [−82.8, −65.4] | −16.8 [−24.6, −10.3] |
| DeepSeek-OCR-2 (card `Free OCR.`) | 26.2 | −68.7 [−74.7, −60.4] | −19.8 [−30.0, −9.9] | 39.9 | −41.8 [−61.2, −13.2] | +16.4 [+0.5, +43.0] |

- **Typhoon stays the strongest measured.** Pathumma (M5) is still the only
  model with no difference shown against it.
- **(a) SEA-LION is a SEA-language fine-tune of exactly Qwen3-VL-4B.** It
  shows no F1 gain over its parent: both intervals include 0 and are about
  ±7–9 points wide. Its recall is lower on both tasks, with intervals
  excluding 0. Language fine-tuning alone does not show a Thai-mark gain;
  that OCR training is where the gain comes from is an inference.
- **W1 attribution (Full-page, stopped outputs).** Not reading vs misreading
  on a correct base: SEA-LION 5.8×, InternVL 46.6×, DeepSeek 12.9×.
  - W1 now covers nine models in four families: Qwen-VL, PaddleOCR-VL,
    InternVL and DeepSeek-OCR.
  - SEA-LION also has the largest "misread, other" share so far (15.5%):
    marks wrong where the base was wrong too.
- **The stop.** Gains are clear except in two cells:
  - InternVL Full-page: −2.3 [−4.7, +0.4]. It loops and then keeps reading,
    so the cut removes correct text.
  - DeepSeek Text recognition: +22.3, with a lower bound of 0.0.
- **Wording to change in the paper.** InternVL has 4 outputs that loop, emit
  EOS before the limit, and are then cut by the stop. W1 counts these as
  "ended outputs changed". "Without changing non-looping outputs" should
  become "without changing outputs that ended without a loop", or carry the
  caveat. W4's S2 needs the same definition fixed before it runs.
- **Engineering notes.**
  - InternVL loops in fp32 as in fp16 (Addendum 2).
  - DeepSeek ran with its own runner and venv. Its fp32 check is OOM on a
    T4, so its numbers are fp16 only (Addendum 3).
  - DeepSeek's grounding markup `<|ref|>/<|det|>` survives extraction in 3
    outputs. Stripping it changes no mark count.
  - SEA-LION's `>` blockquotes survive extraction in 31 outputs. This
    affects CER only.

## W3: T2 on Pathumma and Qwen3-VL-4B

Tone, Full-page / Text recognition:

| model | oracle | prior | greedy at produced sites | registered pattern |
|---|---|---|---|---|
| Pathumma | 99.7 / 99.0 | 98.7 / 97.8 | 98.1 / 97.1 | loss mostly not-reading; image gain +1.0 / +1.2 (as Typhoon) |
| Qwen3-VL-4B | 98.7 / 98.0 | 99.1 / 97.9 | **80.1 / 88.4** | misreads happen in generation; claim (2) holds only partly; image gain −0.5 / +0.1 (as the base) |

- **This qualifies claim (2) and needs your reading.** On teacher-forced
  evidence, "lost by not reading" fits the Thai OCR fine-tunes. The general
  models (the base in T2, Qwen3-VL-4B here) also misread marks in
  generation:
  - Qwen3-VL-4B gets 91.3% of tone marks right where it read the base
    consonant correctly, against an oracle of 99.1%. This diagnostic is not
    registered.
  - W1 still shows Qwen3-VL-4B losing more to not reading (ratio 7.3), so
    the two measures agree on direction, not on size.
  - Proposal: CLAIMS.md's claim (2) names the models it covers. I have not
    edited CLAIMS.md; that is yours to approve.
- **"Greedy at produced sites" is defined in
  `scripts/model_survey_w3_analyze.py`.** No code for it existed in
  `thai_marks`. A site counts as produced when its base consonant aligns to
  an output character. If you computed T2's figure differently, the Typhoon
  comparison in W3 results §2 is not strictly like for like. Can you say
  how T2's figure was computed?
- **Contrastive re-scoring** is below the oracle at both λ for both models.
  R1 §6.4's reading extends.

## W4: draft only

`MODEL_SURVEY_W4_LOCKED_REGISTRATION_DRAFT.md` now holds **proposed**
values. Nothing is authorized and no locked item was opened. The proposals:

- **Include** SEA-LION and DeepSeek-OCR-2 (fp16 only, with its own runner).
- **Exclude** InternVL: its smoke is degenerate in both dtypes, and its F1 is
  15.8 / 6.7.
- **8 models**, about 30–45 GPU-hours, split over both accounts.
- **Fix S2's definition of "ended"** before the run.

Everything else in it waits for your approval and mine: the extraction choice
and the account split.

## What I need from you

1. Your reading of W3b for claim (2), and any CLAIMS.md change.
2. How T2's "produced sites" figure was computed.
3. W4: whether to go ahead, which models, and the account split.

The Decision Log entry 2026-10-12a is under the standing delegation. The PR
is self-merged after CI and a local pytest run, as for M5.
