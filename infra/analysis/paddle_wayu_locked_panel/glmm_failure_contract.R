eligible_numerical_fit_calls <- c(
  "pwrssUpdate",
  "glmerPwrssUpdate",
  "bobyqa",
  "optwrap",
  "optimizeGlmer"
)

condition_call_name <- function(condition) {
  call <- conditionCall(condition)
  if (is.null(call) || length(call) == 0) return("")
  head <- call[[1]]
  if (is.symbol(head)) return(as.character(head))
  paste(deparse(head), collapse = " ")
}

run_registered_fit_stage <- function(stage, fit_function) {
  allowed_stages <- c("FULL_MODEL_FIT", "NULL_MODEL_FIT")
  if (!(stage %in% allowed_stages)) {
    stop("invalid registered GLMM fit stage", call. = FALSE)
  }
  tryCatch(
    list(fit_status = "FIT_SUCCESS", fit_result = fit_function()),
    error = function(error) {
      call_name <- condition_call_name(error)
      if (!(call_name %in% eligible_numerical_fit_calls)) {
        stop(error)
      }
      list(
        fit_status = "FIT_EXCEPTION_NUMERICAL_FALLBACK_ELIGIBLE",
        diagnostics_available = FALSE,
        fit_exception_class = class(error),
        fit_exception_message = conditionMessage(error),
        fit_exception_call = call_name,
        fit_stage = stage,
        fallback_eligibility = "NUMERICAL_GLMM_FIT_EXCEPTION_FALLBACK_AMENDMENT_APPROVED"
      )
    }
  )
}

write_fit_exception <- function(result, output_path) {
  out <- c(
    list(schema_version = 2),
    result
  )
  jsonlite::write_json(
    out,
    output_path,
    auto_unbox = TRUE,
    pretty = FALSE,
    digits = NA,
    null = "null"
  )
}
