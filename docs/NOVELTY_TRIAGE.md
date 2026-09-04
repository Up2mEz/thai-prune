# Novelty Triage Decision Memo

**Date:** 2026-09-04  
**Status:** `GO_EVALUATION_DIAGNOSTIC_PROVISIONAL`

**Decision owner:** Human researcher

## Human-approved decision

Proceed under an evaluation/diagnostic framing, provisionally with respect to
the bounded literature search. Do not begin a new-method track.

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

## Refresh condition

Re-open this decision if a directly comparable controlled study is found,
compatibility evidence closes the remaining gap, or advisor review judges the
novelty insufficient.
