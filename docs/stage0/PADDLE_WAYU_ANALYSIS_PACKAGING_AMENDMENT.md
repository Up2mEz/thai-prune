# Paddle/Wayu Registered Analysis Packaging Amendment

วันที่: 2026-09-14

Classification: `ANALYSIS_ENVIRONMENT_PACKAGING_AMENDMENT`

## Timing and boundary

Amendment นี้เกิดหลัง Attempt 5 ทำครบ `6,400 / 6,400` calls และผ่าน local
verification แต่ก่อนเปิด Attempt-5 scientific output เพื่อวิเคราะห์
`write_analysis_inputs(...)` และ frozen `analyze` command ยังไม่เคยรัน

นี่เป็น packaging-only amendment ไม่ใช่ statistical-method, hypothesis,
estimand, R-version, R-package-version หรือ model-formula change และไม่อ้างว่า
originally frozen Docker image reproducible as-is

## Observed defect

Original Dockerfile ขาด system capabilities ที่ `nloptr` และ `fs` ต้องใช้,
ไม่ได้ copy frozen `run_glmm.R` เข้า image และปล่อยให้ Docker build คืน exit code
0 ได้แม้ R package installation ล้มเหลว

## Authorized repair

- Pin original resolved base image:
  `rocker/r-ver:4.5.2@sha256:fd4ccdd3a4a6f7ef805e2daeee2a0fe3bf126bc231f36351223baecf5a595a4c`
- Add only `cmake` and `libuv1-dev` to the existing Ubuntu apt install list
- Copy the unchanged frozen `run_glmm.R` to
  `/opt/locked-panel/run_glmm.R`
- Copy and execute a no-data validator as the final Docker build assertion
- Require exact R/package versions, successful library loading, R parseability,
  and exact source/container `run_glmm.R` SHA-256
- Add host-side no-mount validation and regression tests

Canonical `run_glmm.R` SHA-256 จาก clean Git checkout ที่ใช้เป็น Docker build
context คือ
`e30341f261995fb15a7136132a9edc94b7b4752c604e95af7c45c2b966aaec1e`.
ค่า hash จาก Windows working-tree bytes ที่ถูกแปลงเป็น CRLF ไม่ใช้เป็น
cross-platform container identity; ตัว statistical source ไม่ได้ถูกแก้ไข

## Frozen scientific identity

The following files remain byte-identical to execution commit
`1fa4cdda6ebe37faf215e574a6a5db467beda1cb`:

- `configs/stage0/overall_model_budget_design.yaml`
- `configs/stage0/paddle_wayu_locked_panel_execution.yaml`
- `infra/analysis/paddle_wayu_locked_panel/run_glmm.R`
- `scripts/paddle_wayu_locked_panel.py`
- `src/labbs2026/stage0/interaction_decision.py`
- `src/labbs2026/stage0/locked_panel_analysis.py`

Therefore:

`ANALYSIS_STATISTICAL_LOGIC_DIFF = EMPTY`

## Required no-data validation

Build and validation must occur from the exact amendment commit without an
Attempt-5 path or volume mount. The generated environment manifest records the
amendment commit, repaired image digest, Ubuntu release, resolved system package
versions, exact R/package versions, source/container entrypoint hashes and the
packaging/statistical diff audit.

Successful terminal state:

`REGISTERED_ANALYSIS_PACKAGING_REPAIR_VALIDATED_PENDING_DATA_ACCESS_AUTHORIZATION`

The frozen `analyze` command remains forbidden until a separate human decision.
