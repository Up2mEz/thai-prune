expected_r_version <- "4.5.2"
expected_packages <- c(
  lme4 = "1.1.38",
  detectseparation = "0.3",
  jsonlite = "2.0.0"
)
run_glmm_path <- "/opt/locked-panel/run_glmm.R"
expected_run_glmm_sha256 <- "e30341f261995fb15a7136132a9edc94b7b4752c604e95af7c45c2b966aaec1e"

fail <- function(message) {
  stop(message, call. = FALSE)
}

actual_r_version <- as.character(getRversion())
if (actual_r_version != expected_r_version) {
  fail(sprintf("R version mismatch: expected %s, got %s", expected_r_version, actual_r_version))
}

actual_packages <- character()
for (package_name in names(expected_packages)) {
  if (!requireNamespace(package_name, quietly = TRUE)) {
    fail(sprintf("required R package is missing: %s", package_name))
  }
  actual_version <- as.character(packageVersion(package_name))
  if (actual_version != expected_packages[[package_name]]) {
    fail(sprintf(
      "R package version mismatch for %s: expected %s, got %s",
      package_name,
      expected_packages[[package_name]],
      actual_version
    ))
  }
  suppressPackageStartupMessages(library(package_name, character.only = TRUE))
  actual_packages[[package_name]] <- actual_version
}

if (!file.exists(run_glmm_path)) {
  fail(sprintf("registered analysis entrypoint is missing: %s", run_glmm_path))
}
invisible(parse(file = run_glmm_path, keep.source = FALSE))

hash_output <- system2("sha256sum", run_glmm_path, stdout = TRUE, stderr = TRUE)
hash_status <- attr(hash_output, "status")
if (!is.null(hash_status) && hash_status != 0) {
  fail("sha256sum failed for registered analysis entrypoint")
}
actual_run_glmm_sha256 <- strsplit(hash_output[[1]], "[[:space:]]+")[[1]][[1]]
if (actual_run_glmm_sha256 != expected_run_glmm_sha256) {
  fail(sprintf(
    "run_glmm.R SHA-256 mismatch: expected %s, got %s",
    expected_run_glmm_sha256,
    actual_run_glmm_sha256
  ))
}

manifest <- list(
  status = "REGISTERED_ANALYSIS_ENVIRONMENT_VALIDATED",
  R_VERSION = actual_r_version,
  package_versions = as.list(actual_packages),
  libraries_loaded = as.list(stats::setNames(rep(TRUE, length(actual_packages)), names(actual_packages))),
  RUN_GLMM_PATH = run_glmm_path,
  RUN_GLMM_PRESENT = TRUE,
  RUN_GLMM_PARSEABLE = TRUE,
  RUN_GLMM_SHA256 = actual_run_glmm_sha256
)
cat(jsonlite::toJSON(manifest, auto_unbox = TRUE), "\n")
