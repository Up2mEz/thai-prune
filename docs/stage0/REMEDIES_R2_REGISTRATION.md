# REMEDIES_R2 — registration (Track B: mark-protected contrast)

**Status: `APPROVED`** under `docs/DECISION_LOG.md` 2026-09-28b (Track B
evaluation, both researchers) and Up2mEz's run order in
`collab/messages/20261003T1810Z_Up2mEz_to_PELY334_review-r1-pilot-and-s1-addendum3.md`
("run direction 2 first, on Typhoon … register each before running").
Written before any R2 output exists. Parameters: `configs/remedies/r2.yaml`.
Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

**Question.** In R1, M3ID-form contrast ended loops but lost tone marks on
readable outputs, by deletion — broadly on the base, concentrated on one long
page on Typhoon (`docs/stage0/REMEDIES_R1_RESULTS.md` §3, §3b). If contrast is
forbidden to change any decision that involves a Thai mark, does it keep its
loop-ending benefit without the mark cost? This tests R1's deletion mechanism
directly.

**Primary model: Typhoon OCR 1.5**; the base is reported beside it.

## 1. Fixed inputs

Identical to R1 (`docs/stage0/REMEDIES_R1_REGISTRATION.md` §1): the same 24
calibration items (12 per task, hash order), `BENCHMARK_QUESTION`, T1's image
policy, fp16 with fp32 fallback, greedy passed explicitly
(`do_sample=false`, `num_beams=1`, `repetition_penalty=1.0`,
`no_repeat_ngram_size=0`), `max_new_tokens=3072`, 2×T4.

## 2. Arms

| arm | what |
|---|---|
| `FULL` | plain greedy |
| `M3ID` | R1's M3ID-form arm unchanged (no-image contrast, `w_t = (1 − e^{−λt}) / e^{−λt}` capped at 10, λ = 0.02, β = 0.1) |
| `M3ID_MP` | `M3ID` with **mark protection**: at any step where the contrastive choice differs from the greedy token and **either token's text contains a Thai tone mark or upper/lower vowel**, the greedy token is kept (`labbs2026.remedies.contrastive.mark_protector`) |

Smoke-only control `MP_ALPHA0` (weight 0, β 0, protection on) must reproduce
`FULL`. The arms' implementations are this project's (M3ID-form), not checked
line by line against the paper; claims are about these implementations.

## 3. Recorded

As R1, plus per contrastive item: steps where contrast changed the token and
steps where protection kept the greedy token.

## 4. Metrics and comparisons

R1's analysis (`labbs2026.remedies.analysis`, §4 of R1's registration),
unchanged, with one added pair:

- each arm vs `FULL` (cause transitions, micro CER, structural de-looped CER,
  mark-specific error and consonant error on items both arms leave
  `misread`/`reading_order`, latency);
- **`M3ID_MP` vs `M3ID`** (same measures);
- per-item tone differences and item-mean, as added to R1 (§3b), for every
  pair.

`FULL` and `M3ID` repeat R1's conditions exactly; their token ids are compared
with R1's outputs as a reproducibility check (reported, not a gate).

## 5. What each pattern would mean, stated in advance

Read on Typhoon first; the base beside it. Counts are small (Typhoon had 10
extra tone errors under M3ID in R1, 7 on one page).

| pattern | reading |
|---|---|
| `M3ID_MP` keeps `M3ID`'s cause transitions out of `loop`/`overgeneration`, and its tone error on kept items is back at `FULL`'s level | the deletion came from contrast acting on mark decisions; a mark-protected contrast keeps the loop benefit for free — worth a full evaluation |
| `M3ID_MP` loses the loop transitions (outputs loop again) | escaping those loops required changing mark-bearing tokens; protection and loop-ending conflict |
| `M3ID_MP`'s tone error stays above `FULL`'s | marks are lost through other tokens (e.g. a changed syllable token without a mark); the token-level protection is too narrow |
| `M3ID` does not reproduce R1 | report and examine before reading anything else |

## 6. Budget, smoke, stopping

Smoke first (1 item per task, plus `MP_ALPHA0`). Cap **4 T4-hours** (R1's
full pilot used ~2 h with PAI's slow looping arm, which R2 does not have). If
the smoke's estimate exceeds the cap, items per task are reduced to fit,
decided before any pilot output, recorded.

## 7. Not in scope

PAI-style arms (next round, at low strength, after the line-by-line check),
VCD, other λ/β, other prompts, the locked split, any claim beyond these two
checkpoints.

---

## Addendum, 2026-10-04 — §6 budget from the smoke, before any pilot output

Smoke `kaggle-remedies-r2-ed4c81a0bb67-smoke1` (1 item per task, both models,
plus `MP_ALPHA0`): 0 failures, fp16, checksums verified. `FULL` and `M3ID`
reproduced R1's token ids exactly on both items and both models; `MP_ALPHA0`
reproduced `FULL` in all four cases; protection fired on 8 and 4 steps (base)
and 0 and 1 (Typhoon). Engineering observations only.

Estimate, slower model (Typhoon), seconds per item over `FULL` + `M3ID` +
`M3ID_MP`: mean 112.5 s → 24 items = **0.75 T4-hours ≤ 4**. Items per task stay
12. No other change.
