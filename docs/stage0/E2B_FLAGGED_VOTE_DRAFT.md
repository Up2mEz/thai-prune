# E2b — majority vote of re-reads at flagged places (offline dev check)

**Status: `DRAFT_DEV_CHECK`.** Written 2026-10-04 after E2, before this rule was
computed. Offline on the same 21 pages and reads as E2; exploratory.

## 1. Why

E2: at places E1 flags, a full-width band re-read at 1.85× is right on half of
the page read's mark errors, but replacing every flagged place with it would
break as many correct clusters as it fixes. ROVER-style voting (Fiscus 1997)
keeps a change only when several independent reads agree; views must differ
to help (resized views were highly correlated: arXiv 2509.09722). Here the
page read, the zoom views and the no-zoom perturbations are five reads.

## 2. Rule (fixed; the reference is never used)

1. **Flag** each consonant-led grapheme cluster of the page read
   (`TYPHOON_CARD` greedy) whose `s_min` ≥ 0.043 (E1's 5% threshold).
2. For a flagged cluster, take its raw output line (≥ 8 characters). For each
   view, align that line (anchored) to each read of the view, keep the read
   with the lowest CER; if CER < 0.4, the view's **vote** is its cluster
   (consonant plus following combining marks) at the position aligned to the
   cluster's consonant; otherwise the view abstains.
3. Votes: the page's own cluster plus the views'. If one string has a strict
   majority of the votes cast and differs from the page's, replace the
   cluster with it.

Variants: **V5** = page + `bands` + `tiles` + `pad` + `scale90` (primary);
**V3** = page + `bands` + `pad`.

## 3. Measures

On the 21 pages: order-free v2 mark R/P/F1 against the greedy page read, with
a paired page bootstrap (seed 20261003); replacements made; among E1-labelled
clusters, **fixed** (error → correct) and **broken** (correct → error).

## 4. Readings fixed in advance

- **Passes** (per variant) if fixed > broken and F1 rises.
- If V5 passes, the method to register for a confirmatory run is:
  E1 confidence → re-read only the flagged pages' bands (+ one perturbed page
  read) → vote at flagged places. Its cost is reported per page.
- If neither passes, voting at flagged places does not select well enough
  with these reads; reported as such.

## 5. Result (2026-10-04): both variants pass §4, with a caveat

`runs/e2/e2b_vote_dev.json` (rule `92630b3`, measurement `fix2`, computed
once; a first attempt timed out before writing, and alignments were then
cached per line without changing the rule). 21 pages, `TYPHOON_CARD`:

| variant | edits | fixed | broken | other | order-free mark F1 (Δ, 95% CI) |
|---|---|---|---|---|---|
| V5 (page + bands + tiles + pad + scale90) | 74 | 8 | 1 | 65 | 96.06 → **96.23** (+0.17 [+0.05, +0.29]) |
| V3 (page + bands + pad) | 70 | 8 | 3 | 59 | 96.06 → **96.24** (+0.18 [+0.07, +0.31]) |

Side check (not in §3; done before reporting because the edit list looked
odd): mean anchored CER on the 21 pages 0.1699 → 0.1690 under V5, 8 pages
better and 1 worse, so the gain is not paid for in other text. **But** of
V5's 74 edits only 8 change marks on the same consonant; 35 change one
consonant for another and 31 put a non-consonant where a consonant was
(`หายใจ` → `ะายใจ`). These come from voting cluster by cluster at aligned
positions inside lines the page read misread as a whole; "other" (65) means
the place is outside E1's labelled lines, so these edits are not counted as
fixed or broken.

**Reading.** Re-reads at E1-flagged places, combined by majority, raise
Typhoon's mark F1 slightly on these pages without hurting text overall. The
effect is small (+0.17 points, 8 fixes on 21 pages), shown on data seen
during design, and the positional cluster vote makes crude edits. Before any
confirmatory run the method needs: votes over whole words or lines rather
than single clusters, re-reading only the band(s) holding flagged lines
(cost), and a fresh split.
