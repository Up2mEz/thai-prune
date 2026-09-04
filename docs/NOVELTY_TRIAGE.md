# Novelty Triage Decision Memo

**Date:** 2026-09-04  
**Status:** `GO_WITH_EVALUATION_FRAMING_PROPOSED`  
**Decision owner:** Human researcher

## Proposed decision

Continue to Stage 0 measurement work only after the human researcher accepts
an evaluation/diagnostic framing. Do not begin a new-method track.

## Evidence

- `docs/LITERATURE.md`
- VTC-Bench already studies benchmark mismatch and downsampling as a
  compression-sensitivity discriminator.
- Fico already provides controlled visual-fidelity/density evaluation.
- ThaiOCRBench already provides broad Thai VLM/OCR evaluation.
- ET-Prune, FastOCR, and RTPrune already occupy text/OCR-aware compression
  method space, although model/intervention compatibility differs.

## Remaining candidate gap

A controlled, pair-clustered diagnostic of whether Thai orthographic component
categories have different degradation curves as actual visual-token budgets
change, with difference-mask and language-prior controls.

## Claim boundary

The project may say it is *investigating* that gap. It may not yet say the gap
is unique, that the effect exists, that pruning causes it, or that a new method
is required.

## Human decision required

Approve one of:

- `GO` with evaluation/diagnostic framing;
- `GO WITH PIVOT` to generic micro-detail measurement;
- `INCONCLUSIVE` pending more literature review;
- `STOP` because novelty is insufficient.

