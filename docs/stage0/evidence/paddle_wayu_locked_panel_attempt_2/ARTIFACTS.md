# Attempt 2 engineering evidence

- `submission_failure.json` records the exact pre-execution Kaggle API failure.
- Local run directory preserves `submission.json`, the deterministic packaged
  source bundle, rendered worker, preflight, and authorization-only validation.
- Authorization-only validation SHA-256:
  `7cffe11c908585b46c80c3986557cac5c759028169a5ac873ea0a356263ba997`.
- Submission manifest SHA-256:
  `6eb0595cf05cec928bdcfcd2c765deb97ed0157c375a7b11ed9a95672b007eef`.
- No Attempt 2 Kaggle version or scientific-output artifact exists.
- The separately authorized HTTP 400 diagnostic is recorded under
  `../paddle_wayu_locked_panel_attempt_2_http400/` and in
  `docs/stage0/PADDLE_WAYU_ATTEMPT_2_HTTP400_DIAGNOSTIC.md`.
