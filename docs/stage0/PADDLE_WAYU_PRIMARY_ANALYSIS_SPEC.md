# Paddle/Wayu Frozen Primary Analysis Specification

> Status: `PRE_REGISTERED_NOT_AUTHORIZED_NOT_RUN`
>
> This specification was chosen from design information and existing S0
> full-information artifacts only. It contains no locked outcome.

## Primary GLMM and global omnibus test

`BUDGET` is a categorical factor with ordered labels used only for display:
`B256_FULL`, `B196`, `B121`, `B64`. The statistical model does not impose a
linear trend. `BASE` and `B256_FULL` are reference levels.

Primary full model:

```text
exact_correct ~ MODEL * BUDGET
              + FONT + FONT_SIZE + MEMBER + COMPONENT
              + (1 | pair_id) + (1 | pair_id:member)
```

Nested null model:

```text
exact_correct ~ MODEL + BUDGET
              + FONT + FONT_SIZE + MEMBER + COMPONENT
              + (1 | pair_id) + (1 | pair_id:member)
```

Both models use a binomial logit GLMM fit by maximum likelihood in
`R==4.5.2`, `lme4==1.1-38`, `glmer`, `nAGQ=1`, optimizer `bobyqa`,
`maxfun=200000`, and derivative calculation enabled. The confirmatory omnibus
test is the likelihood-ratio statistic
`2 * (logLik(full) - logLik(null))`, compared with chi-square df=3 by
`anova(null, full, test="Chisq")`, two-sided alpha 0.05. The three tested
coefficients are `MODEL:SPECIALIZED x B196/B121/B64`; no budget is selected
after outcomes.

## Frozen probability-scale estimands

Marginal probabilities use design-standardized empirical cell means: average
the binary outcomes over the complete balanced registered distribution of
pair, member, font, size, and component rows after counterfactually selecting
the named `MODEL x BUDGET` cell. In this balanced panel this is empirical
g-computation; it does not plug empirical-Bayes random effects into predictions
and does not require 10,000 GLMM refits. For each reduced budget `b`:

```text
DID_b = [P(SPECIALIZED,b) - P(SPECIALIZED,B256_FULL)]
      - [P(BASE,b)        - P(BASE,B256_FULL)]
```

The three named estimands are `DID_196`, `DID_121`, and `DID_64`, reported in
percentage points. Uncertainty uses 10,000 nonparametric resamples of complete
`pair_id` clusters with seed `20260913`; all rows of a sampled pair remain
together. Report unadjusted percentile 95% CIs. For each contrast, center the
bootstrap replicates as `z*=DID*-DID_hat` and compute the two-sided p-value as
`(1 + count(abs(z*) >= abs(DID_hat))) / 10001`. Apply Holm's step-down procedure
across the three p-values at familywise alpha 0.05. Report every contrast
regardless of sign or significance.

## Why the target-aware random structure is frozen

The review in `PADDLE_WAYU_REPEATED_TARGET_REVIEW.json` residualized the 1,520
S0 binary outcomes for the registered main effects. Same-target residual
covariance was `0.07952`; cross-member covariance within the same pair was
`0.02407`. The target-level excess was `0.05545`, with pair-bootstrap 95% CI
`[0.03469, 0.07877]`, or about 27.55% of residual variance. Thus `(1|pair_id)`
alone cannot represent the observed dependence among repeated observations of
one target.

Structure B is identifiable by design: S0 has 95 pair levels, 190 target levels,
and eight observations per target; the locked panel has 100, 200, and 32,
respectively. Nevertheless, two nested variance components can reach a
boundary. This evidence supports selecting B before locked data; it does not
guarantee convergence or a non-singular locked fit.

## Registered GLMM diagnostics

The GLMM is valid only if both full and null fits satisfy every check:

1. optimizer convergence code equals zero;
2. `fit@optinfo$conv$lme4$messages` is empty;
3. all coefficients, standard errors, log-likelihoods, gradients, Hessian,
   and covariance entries are finite;
4. maximum absolute scaled gradient is at most `0.002`;
5. Hessian is positive definite under the `lme4` derivative check;
6. `isSingular(fit, tol=1e-4)` is false;
7. no fixed-effect coefficient has absolute magnitude at least 20 and no
   standard error is non-finite or at least 10;
8. a fixed-effects-only binomial separation diagnostic using
   `detectseparation==0.3` and the same fixed-effect design reports neither
   complete nor quasi-complete separation.

Any failed check yields `PRIMARY_GLMM_DIAGNOSTIC_FAILURE`. Preserve the fit,
warning, diagnostic values, and session manifest. Do not try alternate
optimizers, remove a random effect, collapse a budget, or change coding after
outcomes.

## Pre-registered fallback

If and only if the GLMM fails the diagnostics, use the following estimator,
which is independent of observed effect direction:

1. within every `pair_id x MODEL x BUDGET`, average exact correctness over the
   eight member/font/size observations;
2. compute each pair's three DID values relative to its own FULL cells;
3. report the mean DID vector across the 100 pairs;
4. resample whole `pair_id` clusters 10,000 times with seed `20260913` for
   percentile 95% CIs and the covariance matrix;
5. test the global null with `W = d' Sigma^-1 d`, chi-square df=3. If `Sigma`
   is non-finite or non-invertible, report `FALLBACK_GLOBAL_TEST_NOT_ESTIMABLE`;
6. calculate two-sided null-centered bootstrap p-values for all three DIDs and
   apply the same Holm procedure.

The report must state that the registered GLMM failed and that the
pair-clustered fallback, not the GLMM, supplies the primary result. Codepoint
CER remains a secondary sensitivity metric. No component interaction is
confirmatory.

## Interpretation boundary

If the FULL-validity condition fails, the primary analysis is labeled
`NOT_INTERPRETABLE_FULL_VALIDITY_FAILED` even if computed for integrity checks.
No reduced-budget result becomes a scientific claim. A PASS permits only the
overall primary `MODEL x BUDGET` interpretation; component capacity remains
descriptive/diagnostic.
