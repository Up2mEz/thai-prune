# OpenTyphoon Terms — re-check, 2026-09-24

**Status: `CLEARED_BY_HUMAN_DECISION` at revision `9c8a8fa149` only** — see
`docs/DECISION_LOG.md`, entry 2026-09-25. The body below records the evidence
as it stood before that decision and is left unchanged. It is not a legal
determination, and it authorizes no inference.

## Why this was re-checked

The researcher reported that their advisor considers Typhoon usable. The
2026-09-12 Decision Log entry closed the Typhoon branch as
`NOT_PURSUED_DUE_TO_USAGE_TERMS`, and §6 of the terms allows them to change at
any time, so the current text was read again rather than relying on the earlier
snapshot.

## Source

| | |
|---|---|
| URL | https://opentyphoon.ai/tac |
| read | 2026-09-24 |
| SHA-256 of rendered page text | `d84f95960fd75dd394748863c9926a5caf1c2152c213cc586097c62971e50015` |
| length | 23,995 characters |

The full text is not reproduced here; the hash identifies the version read.

## Clauses that bear on this project

Paraphrased; section numbers are the page's own.

1. **§2, benchmarking.** Competitive benchmarking, data scraping and model
   extraction are prohibited unless the Company — SCB DataX Co., Ltd. — has
   given *prior express written consent*. Present on 2026-09-12 and still
   present.
2. **§2, modification.** The licence prohibits imitating, modifying,
   deconstructing, reverse engineering or changing any function of the
   Services. §1 defines Services to include the use or download of the Model.
   **This was not flagged in the 2026-09-12 record and matters more for this
   project than the benchmarking clause does**: every compression arm here
   alters the model's forward pass — removing visual tokens after the encoder,
   subsetting M-RoPE positions, averaging projector features.
3. **§3, channel.** The terms govern use regardless of access method, including
   open-source distribution and third-party platforms, and prevail over the
   third party's terms where they conflict. The Hugging Face `apache-2.0` tag
   does not displace them on the terms' own reading.
4. **§6, change.** The Company may revise the terms at any time, effective on
   publication.

## What would clear it

Written consent from SCB DataX / the Typhoon team that explicitly covers:

- comparative evaluation of Typhoon against other models, and publication of
  the results;
- modifying the model's inference path — post-encoder token pruning and
  merging, and input resolution reduction;
- the specific checkpoint and revision to be used.

An advisor's view that academic use is acceptable is not that consent, unless
the advisor holds such a written grant. If one is obtained it should be archived
under `docs/stage0/` alongside this record and cited in a Decision Log entry
before any Typhoon inference.

## Technical notes for if it is cleared

Recorded now so the cost is visible before the decision, not after.

- The previously audited checkpoint, `typhoon-ai/typhoon-ocr1.5-2b`, declares
  `Qwen/Qwen3-VL-2B-Instruct` as its fine-tuning base with a compatible
  625-tensor state dict. That base/descendant pair is architecturally cleaner
  than Paddle/Wayu, whose exact fine-tuning parent revision is not established.
- Its model card describes a page reader — Markdown, HTML tables, pages resized
  up to 1,800 px. That fits the `mekpro/ocr_th` `official` pages, on which the
  current region recogniser falls into repetition loops.
- **The existing pruning code does not port directly.** It is written against
  PaddleOCR-VL's `get_image_features`, `compute_3d_position_ids` and
  `get_placeholder_mask`. Qwen3-VL additionally injects visual features into
  several decoder layers (DeepStack), so removing tokens from the input
  sequence alone would leave them present deeper in the model. Pruning would
  need re-implementing and re-verifying for that architecture before any result
  meant anything.
- The Qwen3-VL-2B base's own licence must be re-read at the pinned revision.

---

## Addendum — independent re-check against primary sources, same day

The researcher asked for a re-check that ignored this repository's earlier
conclusions. Reading the Hugging Face revision history directly, rather than the
current model card alone, changes the picture in one respect the 2026-09-12
record never examined.

### What the revision history shows

| checkpoint | released | terms sentence added to card | weights changed then? |
|---|---|---|---|
| `typhoon-ai/typhoon-ocr1.5-2b` | 2025-11-10 | **2026-06-11**, commit `15b381a2d6` | **no** — that commit touches `README.md` only; `model.safetensors` has the same LFS oid |
| `typhoon-ai/typhoon-ocr-7b` | 2025-05-14 | **2026-06-11**, commit `a8d3f50458` | README-only commit |

- For seven months, `typhoon-ocr1.5-2b` was distributed with a card whose only
  licence statement was `license: apache-2.0`. Revision `9c8a8fa149`
  (2026-01-22) is the last such revision; its README contains no terms, consent,
  benchmarking or use-restriction language at all.
- No revision of any Typhoon OCR repository contains a `LICENSE` file. None is
  gated; no click-through acceptance is required to download.
- The base, `Qwen/Qwen3-VL-2B-Instruct`, is `apache-2.0` with no additional
  terms in its card.

So byte-identical weights exist at a pinned revision that was published under
Apache-2.0 alone.

### What that does and does not establish

**Established from source:** the facts in the table above.

**An argument, not a conclusion:** Apache-2.0 §2 grants a perpetual and
irrevocable copyright licence. On that reading, a revision distributed under
Apache-2.0 alone remains usable under Apache-2.0 terms, and a sentence added to
a later README does not retroactively attach a contract to an earlier release.

**Against that argument:** the OpenTyphoon terms §3 assert that they govern use
regardless of access channel and prevail over third-party terms; a copyright
licence and a contract of use are different instruments that can coexist; and
whether either binds a user who pins an earlier revision is a question of
contract law this document cannot answer.

**Not a legal matter but real:** the vendor's current stated position is
unambiguous. Publishing a comparison that relies on a pinned pre-terms revision
while the current terms forbid it could create friction with a group that is
central to Thai NLP and may be among the reviewers.

### Revised status

`APACHE_ONLY_REVISION_EXISTS_LEGAL_INTERPRETATION_REQUIRED` for
`typhoon-ai/typhoon-ocr1.5-2b@9c8a8fa149`. Still not authorized for inference.

Asking for written consent remains the lowest-risk route, and this finding
makes the request easier to put: the model was released under Apache-2.0, and
the request is only to confirm that academic evaluation of that release —
including modifying its inference path and publishing results — is acceptable.
