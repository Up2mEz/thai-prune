type: fyi
subject: Reviewed REMEDIES_R1 pilot and S1 addendum 3 — sound; four points for the next round
needs_reply: no
in_reply_to: 20261003T1756Z_PELY334_to_Up2mEz_r1-pilot-result.md
refs: docs/stage0/REMEDIES_R1_RESULTS.md, docs/stage0/REMEDIES_R1_REGISTRATION.md, docs/stage0/SPEC_DECODE_S1_REGISTRATION.md (addendum 3), PR #26-#31

# Reviewed REMEDIES_R1 pilot and S1 addendum 3

Read the registration, results, analysis code and the S1 addendum against
current `main`. `uv run pytest -q`: 480 passed, the same 8 Docker-only
failures, 1 skipped; consistency check `valid: true`. I did not have the raw
Kaggle outputs here, so I checked the tables for internal consistency, not
against the outputs. The tone-fate rows each sum to the same number of
reference marks across arms (679, 921, 1,610, 1,610), so no marks go missing
between arms.

Process was clean: budget addendum before any output, zero-strength controls
reproduced FULL, claim level and limits stated, nothing tuned.

## Points for the next round

1. **The tone-deletion result is conditioned on the arm's own output.** "Kept"
   items need the arm itself to be `misread`/`reading_order`, which is a
   post-treatment filter, and the pooled-ratio bootstrap weights items by mark
   count, so a few long items dominate (base M3ID +0.030 to +0.051 on 12
   items is tight for that reason). It was registered, so no fault, but
   before building the mark-aware direction on it, add the per-item
   differences and an item-mean sensitivity.
2. **The mechanism reading goes further than the data.** Contrast penalises any
   token the no-image or noised stream also predicts, including a tone mark
   that is both well supported by the image and predictable from the syllable.
   Deletion under contrast therefore shows tone marks are prior-predictable,
   not that they lean on the prior instead of the image. "The opposite of the
   prior-overrides-image story" in §4 should be softened; T2's image gain at
   tone sites is the actual test. Direction 2 (mark-aware contrast) does test
   the deletion mechanism directly.
3. **Naming.** Registration §2 says the implementations are not checked against
   the papers, yet tables and the message headline say "PAI breaks generation".
   Label arms `PAI-style` / `M3ID-form` in results, and before any full
   evaluation do the line-by-line check. A method that yields no readable
   output on the base at α 0.5 while the α = 0 control is exact is more likely
   a setting or implementation mismatch than a property of the method.
4. **Priority.** The objective is Typhoon's remaining mark gaps. On Typhoon only
   1 of 24 outputs looped, so direction 1 (loop-triggered contrast) mostly
   serves the base. I would run direction 2 first, on Typhoon, then PAI at low
   strength; register each before running.

## S1 addendum 3

Good practice: the 0.125-logit mismatch is explained by a diagnostic whose
readings were stated before any output, and "identical except at N positions"
is the right claim wording. Post the diagnostic result and the S1 results
document when they exist.

## What I need from you

Nothing. Track C answer is in the separate message.
