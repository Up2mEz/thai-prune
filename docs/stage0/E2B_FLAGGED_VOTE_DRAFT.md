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
