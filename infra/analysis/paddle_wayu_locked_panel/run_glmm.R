args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) stop("usage: run_glmm.R INPUT_CSV OUTPUT_JSON")

suppressPackageStartupMessages(library(lme4))
suppressPackageStartupMessages(library(detectseparation))
suppressPackageStartupMessages(library(jsonlite))

if (as.character(packageVersion("lme4")) != "1.1.38") stop("lme4 version mismatch")
if (as.character(packageVersion("detectseparation")) != "0.3") stop("detectseparation version mismatch")
if (getRversion() != "4.5.2") stop("R version mismatch")
source("/opt/locked-panel/glmm_failure_contract.R", local = TRUE)

dat <- read.csv(args[[1]], stringsAsFactors = FALSE, check.names = FALSE)
if (nrow(dat) != 6400 || length(unique(dat$call_id)) != 6400) stop("analysis row mismatch")
required_columns <- c(
  "call_id", "pair_id", "MODEL", "BUDGET", "FONT", "FONT_SIZE",
  "MEMBER", "member", "COMPONENT", "exact_correct"
)
if (!all(required_columns %in% names(dat))) stop("analysis columns mismatch")
if (anyNA(dat[, required_columns])) stop("analysis input contains missing values")
if (!all(dat$exact_correct %in% c(0, 1))) stop("exact_correct must be binary")
if (!setequal(unique(dat$MODEL), c("BASE", "SPECIALIZED"))) stop("MODEL coding mismatch")
if (!setequal(unique(dat$BUDGET), c("B256_FULL", "B196", "B121", "B64"))) stop("BUDGET coding mismatch")
dat$MODEL <- factor(dat$MODEL, levels = c("BASE", "SPECIALIZED"))
dat$BUDGET <- factor(dat$BUDGET, levels = c("B256_FULL", "B196", "B121", "B64"))
dat$FONT <- factor(dat$FONT)
dat$FONT_SIZE <- factor(dat$FONT_SIZE)
dat$MEMBER <- factor(dat$MEMBER)
dat$member <- factor(dat$member)
dat$COMPONENT <- factor(dat$COMPONENT)
dat$pair_id <- factor(dat$pair_id)

full_formula <- exact_correct ~ MODEL * BUDGET + FONT + FONT_SIZE + MEMBER + COMPONENT +
  (1 | pair_id) + (1 | pair_id:member)
null_formula <- exact_correct ~ MODEL + BUDGET + FONT + FONT_SIZE + MEMBER + COMPONENT +
  (1 | pair_id) + (1 | pair_id:member)
control <- glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 200000), calc.derivs = TRUE)

full_fixed_matrix <- model.matrix(lme4::nobars(full_formula), data = dat)
null_fixed_matrix <- model.matrix(lme4::nobars(null_formula), data = dat)
if (!all(is.finite(full_fixed_matrix)) || !all(is.finite(null_fixed_matrix))) {
  stop("registered model matrix contains non-finite values")
}

fit_with_warnings <- function(formula) {
  seen <- character()
  fit <- withCallingHandlers(
    glmer(formula, data = dat, family = binomial(link = "logit"), nAGQ = 1, control = control),
    warning = function(w) {
      seen <<- c(seen, conditionMessage(w))
      invokeRestart("muffleWarning")
    }
  )
  list(fit = fit, warnings = seen)
}

full_attempt <- run_registered_fit_stage(
  "FULL_MODEL_FIT",
  function() fit_with_warnings(full_formula)
)
if (full_attempt$fit_status != "FIT_SUCCESS") {
  write_fit_exception(full_attempt, args[[2]])
  quit(save = "no", status = 0)
}
full_result <- full_attempt$fit_result

null_attempt <- run_registered_fit_stage(
  "NULL_MODEL_FIT",
  function() fit_with_warnings(null_formula)
)
if (null_attempt$fit_status != "FIT_SUCCESS") {
  write_fit_exception(null_attempt, args[[2]])
  quit(save = "no", status = 0)
}
null_result <- null_attempt$fit_result
full <- full_result$fit
null <- null_result$fit
comparison <- anova(null, full, test = "Chisq")

fit_diagnostics <- function(fit, captured_warnings) {
  derivs <- fit@optinfo$derivs
  hessian <- derivs$Hessian
  gradient <- derivs$gradient
  scaled_gradient <- tryCatch(solve(chol(hessian), gradient),
                              error = function(e) rep(Inf, length(gradient)))
  hessian_values <- tryCatch(eigen(hessian, symmetric = TRUE, only.values = TRUE)$values,
                             error = function(e) rep(-Inf, 1))
  coefs <- fixef(fit)
  covariance <- vcov(fit)
  ses <- sqrt(diag(covariance))
  optimizer_code <- fit@optinfo$conv$opt
  lme4_messages <- fit@optinfo$conv$lme4$messages
  if (is.null(lme4_messages)) lme4_messages <- character()
  values <- list(
    optimizer_code_zero = identical(as.integer(optimizer_code), 0L),
    lme4_messages_empty = length(lme4_messages) == 0,
    finite_derivatives = all(is.finite(gradient)) && all(is.finite(hessian)),
    max_absolute_scaled_gradient_at_most_0_002 = all(is.finite(scaled_gradient)) && max(abs(scaled_gradient)) <= 0.002,
    hessian_positive_definite = all(is.finite(hessian_values)) && min(hessian_values) > 0,
    singular_fit_false = !isSingular(fit, tol = 0.0001),
    finite_coefficients_covariance_loglikelihood = all(is.finite(coefs)) && all(is.finite(covariance)) && is.finite(as.numeric(logLik(fit))),
    absolute_fixed_coefficient_below_20 = max(abs(coefs)) < 20,
    standard_error_below_10 = all(is.finite(ses)) && max(ses) < 10
  )
  list(checks = values, max_absolute_scaled_gradient = max(abs(scaled_gradient)),
       minimum_hessian_eigenvalue = min(hessian_values),
       singular_fit = isSingular(fit, tol = 0.0001), optimizer_code = optimizer_code,
       lme4_messages = lme4_messages, max_absolute_fixed_coefficient = max(abs(coefs)),
       max_standard_error = max(ses), captured_warnings = unique(captured_warnings))
}

full_diag <- fit_diagnostics(full, full_result$warnings)
null_diag <- fit_diagnostics(null, null_result$warnings)
coefs <- fixef(full)
ses <- sqrt(diag(vcov(full)))

fixed_formula <- exact_correct ~ MODEL * BUDGET + FONT + FONT_SIZE + MEMBER + COMPONENT
separation_fit <- glm(fixed_formula, data = dat, family = binomial(link = "logit"),
                      method = detect_separation)
separation_detected <- any(is.infinite(coef(separation_fit)))

checks <- c(full_diag$checks, null_diag$checks, list(separation_false = !separation_detected))
names(checks) <- c(paste0("full_", names(full_diag$checks)),
                   paste0("null_", names(null_diag$checks)), "separation_false")

out <- list(
  schema_version = 2,
  fit_status = if (all(unlist(checks))) "FIT_SUCCESS_DIAGNOSTICS_PASS" else "FIT_SUCCESS_DIAGNOSTICS_FAIL",
  diagnostics_available = TRUE,
  environment = list(
    R = as.character(getRversion()),
    lme4 = as.character(packageVersion("lme4")),
    detectseparation = as.character(packageVersion("detectseparation")),
    jsonlite = as.character(packageVersion("jsonlite"))
  ),
  formulas = list(full = paste(deparse(full_formula), collapse = " "),
                  null = paste(deparse(null_formula), collapse = " ")),
  implementation = list(function_name = "glmer", nAGQ = 1, optimizer = "bobyqa", maxfun = 200000),
  omnibus = list(statistic = unname(comparison$Chisq[[2]]), df = unname(comparison$`Chi Df`[[2]]),
                  p_value = unname(comparison$`Pr(>Chisq)`[[2]])),
  diagnostics = list(checks = checks, full = full_diag, null = null_diag,
                     separation_detected = separation_detected),
  diagnostics_pass = all(unlist(checks)),
  fixed_effects = setNames(as.list(unname(coefs)), names(coefs)),
  fixed_effect_standard_errors = setNames(as.list(unname(ses)), names(ses)),
  log_likelihood = list(full = unname(as.numeric(logLik(full))), null = unname(as.numeric(logLik(null))))
)

write_json(out, args[[2]], auto_unbox = TRUE, pretty = FALSE, digits = NA)
