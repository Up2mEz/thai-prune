# REMEDIES_R2 — results (Track B: mark-protected contrast)

**Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.** Same 24 calibration
items and conditions as R1. Registration: `docs/stage0/REMEDIES_R2_REGISTRATION.md`
(+ budget addendum). Authorization: `docs/DECISION_LOG.md` 2026-09-28b, run order
per Up2mEz. Arms are this project's implementations (`M3ID` = M3ID-form).

| | |
|---|---|
| run | `kaggle-remedies-r2-236ecdebe734`, commit `236ecde`, 2×T4, fp16 both models |
| smoke | `kaggle-remedies-r2-ed4c81a0bb67-smoke1` (`MP_ALPHA0` reproduced `FULL`) |
| failures | 0; checksums verified; analysis `scripts/remedies_analyze.py` (registered) |
| reproduction | `FULL` and `M3ID` token-identical to R1 on **24/24 items, both models** |

## 1. Results

Comparisons paired by item; mark rates on items both arms leave
`misread`/`reading_order`; 95% bootstrap intervals (descriptive).

### Typhoon (primary)

| | `M3ID` vs `FULL` | `M3ID_MP` vs `FULL` | `M3ID_MP` vs `M3ID` |
|---|---|---|---|
| cause transitions off FULL's failures | loop→misread 1, omission→misread 1, overgen→reading_order 1 | **identical to `M3ID`** | 0 changes in cause |
| micro CER (T1) | 0.276 → 0.057 | 0.276 → **0.054** | 0.057 → 0.054 |
| TONE mark-specific, kept | 0.004 → 0.010 | 0.004 → **0.007** (+0.003 [0.000, 0.009]) | 0.012 → 0.008 (−0.004 [−0.008, −0.001]) |
| UPPER | 0.006 → 0.008 | 0.006 → 0.006 | −0.003 |
| LOWER | 0.002 → 0.002 | 0.002 → 0.005 | +0.002 |
| consonant, kept | 0.035 → 0.029 | 0.035 → 0.025 | 0.029 → 0.025 |
| per-item tone: worse / better / same, net extra tone errors | 4 / 0 / 15, **+10** | 2 / 0 / 17, **+5** | 0 / **4** / 18, −6 |
| latency vs FULL | ×1.60 | ×1.61 | ×1.00 |

### Base (reference)

| | `M3ID` vs `FULL` | `M3ID_MP` vs `FULL` | `M3ID_MP` vs `M3ID` |
|---|---|---|---|
| loops ended (of 7) | 6 | 5 (one stays a loop) | one readable item turns into a loop |
| micro CER (T1) | 1.124 → 0.213 | 1.124 → 0.293 | 0.213 → 0.293 |
| TONE mark-specific, kept | 0.037 → 0.076 | 0.037 → **0.062** | 0.076 → 0.063 (−0.013 [−0.025, −0.001]) |
| per-item tone: worse / better / same, net | 9 / 0 / 3, **+33** | 7 / 0 / 5, **+21** | 3 / **10** / 4, −17 |
| median protected steps per item | 0 | 10.5 | |

## 2. Reading, against the patterns stated in advance (registration §5)

- **Typhoon: protection keeps the loop benefit and halves the tone cost.**
  Every cause transition `M3ID` produced is kept, CER is as good or better, and
  extra tone errors fall from +10 to +5 (4 items improve, none worsen). Tone
  error is not fully back at `FULL`'s level, so the result sits between
  pattern 1 ("deletion came from contrast acting on mark decisions") and
  pattern 3 ("marks are lost through other tokens").
- **Base: the same direction, smaller and with a trade-off.** Extra tone errors
  fall from +33 to +21 (10 items improve, 3 worsen), but one loop is no longer
  ended and one readable item loops — pattern 2 in a small way.
- **Mechanism (inference).** About half of the tone loss runs through
  decisions where a mark-bearing token is directly at stake, which protection
  blocks. The rest remains: a contrast change on a token with no mark can still
  lead into a continuation where the mark is never produced (for example a
  syllable tokenized differently). Token-level protection is too narrow to stop
  that.

## 2b. Markup audit of the raw outputs (`scripts/audit_markup.py`)

Checked before reporting (24 outputs per model and arm): no HTML tag in any
output; Markdown list markers in 8–9 outputs per arm, bold in ≤ 4, one
heading — identical across a model's arms. Thai characters removed by
normalization: 0.0% (T1) and ≤ 0.1% (structure-aware). One Typhoon page
carries an HTML entity (`&amp;` for `&`) in all three arms, which T1's
normalization does not decode — a few characters of CER, identical in every
arm, no effect on marks or on any paired comparison.

## 3. What this result does not show

- Not magnitudes: 24 items; Typhoon's tone changes are a handful of marks.
- Not that `M3ID_MP` is safe for marks: on both models it still costs some.
- Not a comparison with T2's oracle (T2's tone numbers await a rerun).
- Nothing about other prompts, the locked split, or other models.

## 4. Directions (each would need its own registration)

1. **Wider protection**: protect a whole syllable (the Thai cluster around a
   possible mark site) rather than single tokens, or apply contrast only to
   tokens outside Thai script.
2. **Loop-triggered contrast** (R1 direction 1): greedy until a loop is
   detected, contrast after — on Typhoon only 1–3 items per 24 need it, so most
   pages would keep greedy's marks untouched. This overlaps Up2mEz's T5b
   (stop-at-loop); coordinate first.
3. For Typhoon the net picture is already favourable: CER 0.276 → 0.054 on
   these 24 items for 5 extra tone errors in ~1,600 scored tone marks.
