# Authorization Request — Region OCR Token-Pruning Branch

> Status: `AWAITING_HUMAN_DECISION`
>
> Authored by: agent. **This is a proposal, not an authorization.**
>
> Inference performed: **NONE**.

The Decision Log records that "Codex may propose decisions and summarize
evidence, but final gate approval belongs to the researcher." This document is
such a proposal. Nothing in it takes effect until the human researcher writes
the entry into `docs/DECISION_LOG.md` themselves.

---

## 1. Why an authorization is required at all

The repository is currently in a hard stop. `docs/DECISION_LOG.md:48-50` states:

> "Stop for human review. No additional experiment, post-hoc rescue analysis,
> threshold or budget change, prompt tuning, pruning/merging, or fine-tuning is
> authorized."

and the standing prohibition list (`DECISION_LOG.md:535-536`) includes:

> "Still unauthorized: locked inference, Resolution Reduction inference, Token
> Pruning, Token Merging, fine-tuning, and method development."

Therefore **no part of the proposed branch may begin** — not the feasibility
smoke, not a dataset download, not a processor call — until a new entry exists.

## 2. What is being asked for

Authorization to open a new, separately-registered branch that tests
**post-encoder Token Pruning against Input Resolution Reduction inside a single
experiment**, on Thai text regions from document images, using the already
terms-cleared Paddle/Wayu pair.

The frozen design is `docs/stage0/REGION_OCR_TOKEN_PRUNING_PROTOCOL.md`.

## 3. What this does NOT ask for

- Gate 0 or Gate 1 approval, or any change to their status
- Re-opening, re-analyzing, or amending the completed
  `kaggle-paddle-wayu-locked-panel-attempt5` result
- Using that completed panel as a control arm for the new contrast
- Any new backbone beyond the two already cleared models
- Quantization, fine-tuning, or method development
- Any claim about H1-H4 being confirmed or rejected

## 4. Decisions the human must make explicitly

1. **Authorize the branch, or not.**
2. **Note that no documentation amendment is needed to execute** (§6). An
   earlier draft claimed otherwise; that claim is withdrawn. Stage 1A text is
   not touched by this branch.
3. **Approve the dataset route** once its terms are read: an external Thai
   document corpus, or the licence-free synthetic fallback. Neither
   `typhoon-ai/ThaiOCRBench` nor `mekpro/ocr_th` currently has any governance
   record in this repository, so neither is cleared today.
4. **Confirm the evidence ceiling**: results from this branch are
   `Preliminary/Pilot` and cannot inform any gate.

## 5. Risks the human should weigh before authorizing

- **No pruning implementation exists.** A repository-wide scan found no
  post-encoder token removal anywhere; every visual hook is a read-only
  `register_forward_hook`. This is new, non-trivial engineering, and the
  existing token-accounting invariants deliberately raise on exactly the
  condition that pruning creates.
- **Model capability at `FULL` is unmeasured on this stimulus type.** The
  Paddle/Wayu pair scored 31.750% / 45.625% exact transcription on short
  synthetic minimal pairs. Region recognition on real document crops is a
  different task and could be better or worse. If `FULL` performance leaves no
  room to observe degradation, the branch stops.
- **The dataset question is unresolved and may not clear.**
- **A null result is a realistic outcome**, and the protocol is written so that
  a null is reportable rather than a failure to be rescued.

## 6. Repository consistency — no amendment is required to execute

An earlier draft of this request claimed that running the branch would break
`scripts/check_research_consistency.py` and that four research documents would
need amending. **That was wrong, and the claim is withdrawn.**

`src/labbs2026/consistency.py` reads the text of the research documents. It has
no knowledge of what has been executed, so running an experiment cannot make it
fail. The relevant assertion (lines 99-101) is a conjunction of three separate
document statements:

```python
"Resolution Reduction is not post-encoder Token Pruning" in research
and "does not make Stage 1A a post-encoder pruning experiment" in architecture
and "Post-encoder Token Pruning and H3 remain `NOT TESTED`" in decisions
```

The first two are conceptual statements about intervention families and about
Stage 1A. They are true independently of this branch and **must not be
touched**. Nothing here re-opens, re-interprets, or rewrites Stage 1A history.

The third is a status line in `docs/DECISION_LOG.md`. Whether it becomes stale
is a question for results-recording time, not a precondition of execution, and
the answer is not obvious: under the evidence vocabulary in `docs/CLAIMS.md`,
`Tested` means "direct valid **locked** evidence exists". This branch produces
`Preliminary/Pilot` evidence only, which is explicitly not `Tested`. Whether the
line should then read `NOT TESTED` or gain a pilot qualifier is a judgement for
the human researcher once results exist.

**Practical consequence:** the consistency check passes now, passes during
execution, and is re-run after results are recorded. If a status line is
adjusted at that point, it is a deliberate one-line decision — never an edit
made to force a failing check green.

---

## 7. Proposed Decision Log entry — for human review

If the researcher approves, the following is the proposed text to add to
`docs/DECISION_LOG.md`. The researcher should edit it to reflect their actual
decision rather than accepting it verbatim.

```md
## 2026-09-__ — Region OCR token-pruning branch authorization

**Stage/Gate:** New intervention-family branch. Gate 0 remains `NOT_RUN`;
Gates 1-6 remain `BLOCKED`.

**Decision owner:** Human researcher

**Decision:** Authorize a separately-registered branch testing post-encoder
Token Pruning against Input Resolution Reduction within a single experiment on
Thai text regions, using `PaddlePaddle/PaddleOCR-VL-1.6` and
`wayu-ai/wayu-paxa-ocr-zero` at their pinned revisions. The frozen design is
`docs/stage0/REGION_OCR_TOKEN_PRUNING_PROTOCOL.md`, committed before any
inference.

### Evidence
- prior run: `kaggle-paddle-wayu-locked-panel-attempt5` (Resolution Reduction
  only; Wald 5.011636, df 3, p 0.170947;
  `NO_CONFIRMATORY_MODEL_BUDGET_INTERACTION_EVIDENCE`)
- terms basis: `docs/FALLBACK_PAIR_CLEARANCE.md` (`TERMS_CLEAR`), re-snapshotted
  in `docs/stage0/PAGE_OCR_MODEL_CLEARANCE.md` before execution
- geometry basis: `docs/stage0/PADDLE_WAYU_PROCESSOR_GEOMETRY.json`

### Reasoning
Post-encoder Token Pruning has never been tested. The Claims Registry forbids
inferring anything about it from the Resolution Reduction null. Establishing
whether the two families differ requires estimating the contrast inside one
design on shared stimuli at matched actual token counts, so Resolution Reduction
is re-run here rather than imported from the completed panel.

### Alternatives considered
- Comparing a new pruning run against the completed panel — rejected: a
  difference between a significant and a non-significant result across separate
  experiments is not evidence of a difference.
- Full-page OCR through a layout detector — rejected: the layout stage is not
  subject to the intervention and would dilute the estimand; the selected models
  are region recognizers and would be off-distribution.
- A new or newer backbone — rejected: no additional model is cleared, and
  Typhoon remains `NOT_PURSUED_DUE_TO_USAGE_TERMS`.

### Known limitations
New dataset, no sealed confirmatory split, two models from one architecture
family, synthetic-or-unvetted corpus. Evidence is `Preliminary/Pilot` and cannot
approve or reject any gate, confirm H1-H4, or justify a new method. Claim scope
is text-region recognition, not end-to-end document OCR.

### Consequence for next stage
Execute the authorized engineering smoke first. Stop for human review if model
capability at `FULL`, dataset terms, or token accounting fail. Report the
resulting table without a pre-set "worth it" threshold.

### Files/configs affected
- `docs/stage0/REGION_OCR_TOKEN_PRUNING_PROTOCOL.md` (new, frozen)
- `docs/stage0/REGION_OCR_DATASET_CANDIDATE_AUDIT.md` (new)
- `docs/stage0/PAGE_OCR_MODEL_CLEARANCE.md` (new, pre-execution)

No existing research document is amended to execute this branch, and
`src/labbs2026/consistency.py` is not modified. Stage 1A text is untouched.
```
