# Region OCR Branch — Pre-execution Model Terms Re-snapshot

> Status: `TERMS_CLEAR_RESNAPSHOT_COMPLETE`
>
> Snapshot date: 2026-09-20
>
> Authorization: `docs/DECISION_LOG.md` entry 2026-09-20
>
> Inference performed: **NONE**. Only public licence and model-card text was
> retrieved. No weights were downloaded and no model was loaded.

`docs/FALLBACK_PAIR_CLEARANCE.md` (audited 2026-09-12) classified this model
pair `TERMS_CLEAR` and required: *"Re-snapshot and hash the applicable model
cards, licenses, and Wayu Terms before any authorized run because the Wayu page
says its terms may change."* This document discharges that precondition.

## 1. Retrieved artifacts and hashes

| Artifact | Source | SHA-256 | Bytes |
|---|---|---|---|
| PaddleOCR-VL-1.6 model card | `huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6/raw/c5630abae1d940eafe0697512a0325494b02ab42/README.md` | `d6c5b77a660577f6e18021defccd835bdc93a8c6538f5a479d597f3e94288abf` | 21,424 |
| wayu-paxa-ocr-zero model card | `huggingface.co/wayu-ai/wayu-paxa-ocr-zero/raw/af0204b4f334a6d5068b6bac2b3738932d6e289b/README.md` | `92bfe0d09e87bb50979f213b454b48bb664e49611c166a25dc7cd848ba5af3c3` | 10,811 |
| Wayu Research Terms of Use | `www.wayuresearch.org/terms` | `9c089d2fe052b4f1eaecffdf816ff805489a91c836a3037214dfb3b8b715c777` | 48,413 |

Model cards were fetched at the **pinned revisions**, not at `main`, so these
hashes are stable. The Wayu Terms page is not version-pinnable and its hash is
therefore a point-in-time snapshot only; it must be re-taken before any later
authorized run.

## 2. Declared licences

Both model cards declare `license: apache-2.0` in their metadata header. The
wayu card adds, as the only incorporated condition:

> "**Acceptable use.** By downloading or using this model you agree to the Wayu
> Research Acceptable Use terms."

## 3. Wayu Acceptable Use — full list as of this snapshot

Section 05 prohibits using the site, artifacts, or generated content to:

1. impersonate any person, including synthetic speech resembling a real
   person's voice, without that person's verifiable consent;
2. deceive, defraud or mislead, including presenting generated material as an
   authentic recording or as a person's own work;
3. create or distribute unlawful content (defamatory, harassing, threatening,
   or sexualising/exploiting minors);
4. violate others' rights or any applicable law, including Thai law such as the
   Computer Crime Act B.E. 2550 (2007) and the Personal Data Protection Act
   B.E. 2562 (2019);
5. make a decision with legal or similarly significant effects on a person —
   credit, employment, insurance, housing, education, healthcare, immigration,
   or law enforcement — on the sole basis of the models or their output, or
   deploy them in a safety-critical system;
6. probe, disrupt, overload, or gain unauthorised access to the site, or access
   it by automated means at a burdening rate;
7. claim that Wayu is affiliated with you, or endorses you or your work, when
   it does not;
8. anything else Wayu "reasonably consider[s] abusive, or harmful to others or
   to us."

The section closes: "An artifact's licence may add conditions of its own. Where
it does, both apply."

## 4. Benchmarking and publication — verified clear

The current text was scanned for any restriction on comparative evaluation or
on publishing results. Two keyword hits exist and **neither is a restriction on
this project**:

- `benchmark` occurs once, in §04 *Research artifacts*: "Our models, datasets,
  code and benchmarks are provided as they are." This is a warranty disclaimer
  covering Wayu's own benchmarks, not a limit on third-party benchmarking.
- `consent` occurs once, in §05 item 1, concerning impersonation of a person's
  voice or identity. It has no connection to evaluation or publication.

The terms contain no occurrence of "comparative", "competitive", or
"publication", and no clause requiring prior approval to publish results.

**Finding:** the 2026-09-12 classification still holds against the current text.
Publishing truthful comparative benchmark results is permitted.

**The single publication constraint** is item 7: the write-up must not state or
imply that Wayu Research is affiliated with, or endorses, this work.

## 5. Model-card statement relevant to the experimental design

The wayu card states, unprompted:

> "**This is a region recognizer, not a page reader.** It is trained on crops
> and has never seen a whole page. Reading a page takes two models —
> PP-DocLayoutV3 finds the regions and orders them, this model transcribes each
> one — which is what the `PaddleOCRVL` pipeline [does]."

This independently corroborates the protocol's decision to measure at the text
region rather than the page, and to introduce no layout stage.

## 6. Scope and residual risk

- This clearance covers the two models only. The TEMS dataset (CC BY 4.0) is
  recorded separately in `docs/stage0/REGION_OCR_DATASET_CANDIDATE_AUDIT.md`;
  its attribution obligation is independent of these model terms.
- The Wayu Terms page is mutable. This snapshot is valid for the currently
  authorized run only.
- This is a research-governance reading, not legal advice.
