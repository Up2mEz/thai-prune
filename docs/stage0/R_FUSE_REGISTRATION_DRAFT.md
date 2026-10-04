# R-FUSE — recovering skipped text by fusing two reads

**Status: `DEV_CHECK_FAILED_DO_NOT_RUN_ON_LOCKED`** (2026-10-01). No output of
the locked split exists, and this rule should not consume it. The development
check on the 69 calibration pages (`fusion.py`, unit-tested) found the
negative control `CAT` beating `FUSE` on the outcome registered below, which
exposed that outcome as rewarding extra text; on an outcome that charges it
(mark F1 under global alignment), `FUSE` 92.5% is below a single read
(93.1% / 93.7%) and global CER rises 9.5 points. Detail and table:
`TYPHOON_FAILURE_PROFILE.md` §3 correction. The primary outcome of any
successor must be **mark precision/recall/F1 under global alignment** (Full-
page OCR), never reference-side accuracy alone. The text below is kept as
drafted, for the record. Evidence motivating it: `TYPHOON_FAILURE_PROFILE.md`, from the
calibration split only. Scoring: `THAI_MARKS_T1_SCORING_V2.md`.

## 1. Question and why

**Research question (RQ-B, Typhoon track).** Does merging two greedy reads of
the same page, made with different prompts, reduce the share of reference
marks transcribed incorrectly, without raising misreads of marks or
consonants, and at what latency?

**Why this and not a mark-level remedy.** On the calibration split Typhoon
misreads a mark whose base consonant it read correctly only 0.3–0.7% of the
time on Full-page OCR, yet it gets 6.2% of all reference marks wrong. Most of
that gap is marks inside text it skipped: runs of ≥10 skipped characters are
61% of its Full-page errors, and the two prompts skip different text (a
reference-aided choice per character would reach 97.1% marks correct from
93.8%). A remedy that sharpens mark reading has at most ~0.5 points to gain
on this model; recovering skipped text has several.

**Not assumed.** That fusion helps on the locked split; that the gain holds
for base or other models; that it explains *why* text is skipped.

## 2. Scope — one new factor

- Model: `typhoon-ai/typhoon-ocr1.5-2b` only, pinned revision (base is a
  later round, after the method's mechanics are established).
- Task: **Full-page OCR only.** Text recognition fails differently (answering
  another line: 54% of its errors) and needs a separate design.
- Factor: the second read comes from the other registered prompt. Tiled
  re-reading is **round 2**, not here.
- Decoding: pinned greedy, `t1.generation` of `configs/thai_marks/t1_t2.yaml`.

## 3. Data

- **Development:** the 69 calibration Full-page OCR items, using the
  existing 2026-09-27 T1 reads. No new inference. The rule is implemented,
  unit-tested and frozen here.
- **Confirmation:** the **128 locked** Full-page OCR items (197 − 69), opened
  once, after this registration is approved and the rule is frozen. Opening
  them consumes them for this question; no parameter may change afterwards.
- Cluster unit: item (page); stratum: `category`.

## 4. Arms

| arm | what it is | role |
|---|---|---|
| `R1` | `BENCHMARK_QUESTION` read alone | baseline (primary prompt) |
| `R2` | `TYPHOON_CARD` read alone | second read, reported alone |
| `FUSE` | R1 with R2-only content merged in (§5) | the method |
| `CAT` | R1 followed by R2, no merging | negative control: more text is not fusion |

`CAT` exists because reference-anchored scoring frees text outside the
matched window; if `FUSE` did no better than `CAT`, any gain would be an
artefact of producing more text.

## 5. Merge rule (reference-free, deterministic)

Inputs are the two raw outputs; extraction is scoring-v2 extraction, so
`<figure>` content of the `TYPHOON_CARD` read is dropped by that prompt's own
contract before merging.

1. `E1 = extract(R1)`, `E2 = extract(R2)`.
2. Global Levenshtein alignment of `E2` against anchor `E1`
   (`decompose.align`, same tie-breaks).
3. Output `E1` in order. At each point where the alignment has a maximal run
   of characters present only in `E2`, insert that run if and only if
   - its length is **≥ L = 10** characters (the omission definition used in
     the failure profile, fixed before any fusion was run), and
   - it is **not already in `E1`**: its central 12 characters do not occur in
     `E1` (a block that `R1` read in another order is not inserted twice).
4. Where the two reads disagree on a character, keep `E1`. (Log-probability
   arbitration needs generation log-probabilities, which T1 does not record;
   it is a later factor.)
5. Empty `E2` gives `FUSE = E1`.

Frozen parameters: `L = 10`, duplicate core 12 characters, anchor `R1`.
Sensitivity only, not a decision input: anchor `R2`.

## 6. Outcomes

**Primary.** Mark accuracy over **all** reference marks — tone, upper and
lower vowels pooled — the share whose fate is `correct` under
reference-anchored alignment and the per-arm chance-located rule. Estimand
`Δ = acc(FUSE) − acc(R1)`, paired by item.

**Secondary, each with the same interval method:**

- mark accuracy per class (tone, upper, lower);
- mark-specific error per class (base consonant correct) — **must not rise**;
- consonant error — **must not rise**;
- micro and median CER;
- inserted-text quality: share of inserted characters that align correctly
  to the reference, and **duplication** (inserted runs that match text
  already elsewhere in the output);
- over-generation (surplus characters per reference character) and output /
  reference length;
- omitted runs (≥10) remaining, per page.

**Latency.** Wall time per page of `R1` alone versus `R1 + R2 + merge`, on the
same T4, same run; merge CPU time reported separately.

## 7. Statistics

Item-level bootstrap, 10,000 resamples, seed 20260927, stratified by
`category`, 95% percentile intervals — the T1/T2 convention. Influence: the
failure profile found 10 pages holding 74% of skipped characters, so every
primary and secondary estimate is also reported with the 10 pages of largest
`R1` omission removed.

## 8. Decision rule, fixed now

`FUSE` is reported as **effective** only if all hold on the locked split:

1. the lower bound of the 95% interval of `Δ` is above 0;
2. `FUSE` beats `CAT` on the primary outcome (interval of the difference
   above 0);
3. mark-specific error and consonant error do not rise by more than
   **0.5 percentage points** (upper bound of the increase's interval below
   0.5) — margin to be confirmed by the researcher;
4. inserted-text duplication is reported, whatever its value.

**Speed** is judged separately against the objective's "comparable speed":
proposed margin **≤ 1.25×** `R1` wall time, to be confirmed. Two greedy reads
roughly double decode time, so `FUSE` alone is expected to fail it; the
registered way to recover it is combination with `SPEC_DECODE_S1`
(identity-preserving speculative decoding, Track A), measured on the same
pages, never assumed. An accuracy gain that fails the speed margin is reported
as such, not as meeting the objective.

**Readings stated in advance.**

- Conditions 1–3 met: skipped text is recoverable from a second read; next
  round tests tiled reads (coverage) against prompt diversity.
- `Δ > 0` but `FUSE ≤ CAT`: the gain is an artefact of extra text.
- `Δ ≈ 0`: omissions coincide across prompts on the locked split; the
  calibration pattern did not generalize.
- Mark-specific error rises: inserted text carries misreads; merge rule needs
  arbitration (log-probability factor).

## 9. Run

After approval: implement `src/labbs2026/thai_marks/fusion.py` with unit tests;
report the frozen rule's calibration numbers (exploratory, labelled so); then
one Kaggle T1 submission on the locked Full-page OCR items, Typhoon only, both
prompts, pinned greedy, resolved generation config recorded. Estimated
~128 × 2 calls at the calibration rate (~24 s per call overall, longer for
full pages): about 2–3 T4-hours.

## 10. Decisions needed from the researcher

1. Approve this registration, or change it.
2. Primary outcome: all-marks accuracy instead of registered RQ-B's
   mark-specific error (see §1 — the latter cannot move on this model).
3. Non-inferiority margin 0.5 points and speed margin 1.25×.
4. Open the locked Full-page OCR items for this question.
