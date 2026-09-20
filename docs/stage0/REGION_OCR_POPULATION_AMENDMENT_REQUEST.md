# Authorization Request — Analysis-Population Amendment

> Status: `AWAITING_HUMAN_DECISION`
>
> Subject: protocol §8.2.1, committed in `463912f`
>
> Effect today: **NONE**. The amendment does not govern any analysis.

## 1. Why this request exists

Commit `463912f` added an analysis-population rule to the protocol: restrict the
primary analysis to regions where `CER(FULL) = 0`, with all eligible regions as
a sensitivity population.

**That is a change to the registered scientific estimand, not engineering
plumbing**, and it was committed without a corresponding `docs/DECISION_LOG.md`
entry. The project's governance reserves scientific decisions to the human
researcher, so the amendment is marked
`PENDING_HUMAN_APPROVAL_NOT_IN_EFFECT` and the registered estimand remains
§8.2 over all eligible regions until this request is decided.

The process error is the agent's: the amendment was written and committed on a
request to "write the protocol and commit", and the scientific-versus-engineering
distinction should have been raised at that point rather than after the fact.

## 2. What is being proposed

| Role | Population |
|---|---|
| Primary | regions where `CER(FULL) = 0` |
| Sensitivity | every eligible region |

## 3. The argument for it

A region the model cannot read at `FULL` has no measurement headroom.
Compression cannot make it informatively worse, so it adds variance to the
contrast without adding signal. This is the same headroom reasoning the project
applied to component baselines in Stage 0.

Conditioning on a control-arm outcome is normally unsafe, because it selects
favourable measurement noise and re-measurement then regresses toward the mean.
Two specific facts remove that mechanism here:

1. Decoding is greedy and deterministic, so a region's `FULL` output is a fixed
   value rather than a draw. The Phase-1 smoke verified this directly: every
   region was generated twice with identical token ids, and macro CER reproduced
   to four decimals across two separate runs.
2. The registered estimand is a difference of differences in which the `FULL`
   term cancels:

```
DiD_b = [CER(PRUNE,b) − CER(FULL)] − [CER(RR,b) − CER(FULL)]
      = CER(PRUNE,b) − CER(RR,b)
```

Both arms are measured on the same regions against the same baseline, so any
floor the selection imposes applies to both and drops out of the contrast.

## 4. The argument against it, stated plainly

Within the primary population `CER(FULL) = 0` by construction, so each arm's
marginal `ΔCER` is non-negative by construction. An improvement can never be
observed and the magnitude is not comparable to an unconditioned rate.

The amendment therefore supports only statements of the form *"among regions
this model already reads correctly, intervention family X degrades recognition
more than Y"*. It supports **no** absolute degradation rate and **no**
generalisation to Thai region OCR as a whole. Those require the sensitivity
population, which is why the proposal reports both rather than one.

A reviewer may also object that selecting on the control arm is unusual
regardless of the argument in §3. The mitigation is that both populations are
pre-registered and both reported, so the effect of the restriction is visible
rather than hidden.

## 5. Decision options

1. **Approve as proposed** — `CER(FULL) = 0` primary, all-regions sensitivity.
2. **Reject** — keep §8.2 over all eligible regions as primary; the
   `CER(FULL) = 0` cut becomes a reported secondary instead.
3. **Approve with the roles reversed** — all-regions primary, `CER(FULL) = 0`
   secondary. This is the most conservative option and still reports both.

Whichever is chosen must be frozen before any pruning inference runs, which is
why this is being raised now rather than after results exist.

## 6. Related operational status, for the same review

- **Kaggle:** `AUTH_CONFIRMED`. The CLI is 2.2.4 with
  `C:\Users\acer\.kaggle\credentials.json` and `auth_method: OAUTH`, and
  `kaggle kernels list --mine` succeeds. An earlier agent report that Kaggle was
  unusable was wrong: it checked only `kaggle.json` and `KAGGLE_*` environment
  variables, which do not cover the newer CLI's OAuth. No credential needs to be
  issued or rotated.
- **Submission remains unauthorized.** Authentication is not authorization. No
  `kaggle kernels push` has been run and none will be until the human approves a
  specific workload.
- **Dataset:** the complete release is now local, removing the sampling bias
  described in the dataset audit. This was data preparation only — no inference
  and no protocol change.

## 7. Proposed Decision Log entry, for human editing

```md
## 2026-09-__ — Region OCR analysis-population decision

**Stage/Gate:** Region-OCR branch analysis specification. Gate 0 remains
`NOT_RUN`.

**Decision owner:** Human researcher

**Decision:** <approve as proposed | reject | approve with roles reversed>
for protocol §8.2.1, committed in `463912f` and held
`PENDING_HUMAN_APPROVAL_NOT_IN_EFFECT` until this entry.

### Reasoning
<researcher's own reasoning>

### Known limitations
Within a `CER(FULL) = 0` population each arm's marginal delta-CER is
non-negative by construction; no absolute degradation rate and no
generalisation to Thai region OCR as a whole may be claimed from it.

### Consequence for next stage
Freeze the chosen population before any pruning inference. Kaggle submission
remains separately unauthorized.
```
