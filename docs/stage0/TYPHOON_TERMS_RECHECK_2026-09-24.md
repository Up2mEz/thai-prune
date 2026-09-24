# OpenTyphoon Terms — re-check, 2026-09-24

**Status: `LEGAL_TERMS_CLEARANCE_REQUIRED` — unchanged.** This records evidence
only. It is not a legal determination and authorizes nothing.

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
