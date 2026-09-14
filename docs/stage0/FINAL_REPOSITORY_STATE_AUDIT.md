# Final Repository State Audit

> Audit status: `COMPLETE_PENDING_HUMAN_REVIEW`
>
> Scientific terminal state: `HUMAN_REVIEW_AFTER_LOCKED_MODEL_BUDGET_PANEL`

## Audited identities

- repository content commit: `cffb3663bf652a09aba3149b85eae68844ccd6aa`
- GLMM exception-eligibility amendment commit:
  `1145dcea76d19d7fb4492b460f2eee3667439232`
- original scientific design commit:
  `871996221a36a56a401fa040c239f55768561210`
- U+FFFD protocol amendment commit:
  `ee9f8c4f85feea935f8c99d05005deea16c30442`
- Attempt-5 execution commit:
  `1fa4cdda6ebe37faf215e574a6a5db467beda1cb`
- accepted analysis image:
  `sha256:7328bb5ac82d574e2d895018981a8cf18b0ae8e73c9b90bf1ce0b350ed7091df`
- frozen design SHA-256:
  `6143c454337570217c9cd028522de510b4fd5b4f9f361fa0ea206014eed185a1`

## Scientific state reconciliation

| Item | Final state | Evidence |
|---|---|---|
| Attempt 5 workload | `COMPLETE`, 6,400/6,400 | local verifier `VERIFIED` |
| Unauthorized/out-of-workload locked pairs | 0 | verification manifest |
| FULL validity | `PASS` | `analysis/full_validity.json` |
| Registered GLMM | `FIT_EXCEPTION_NUMERICAL_FALLBACK_ELIGIBLE` | `analysis/glmm_result.json` |
| Diagnostics | unavailable; not fabricated | `diagnostics_available=false` |
| Primary estimator | unchanged registered pair-clustered fallback | `analysis/registered_analysis.json` |
| Global result | Wald 5.011636, df 3, p 0.170947 | registered fallback global test |
| Frozen classifier | `NO_CONFIRMATORY_MODEL_BUDGET_INTERACTION_EVIDENCE` | registered analysis |
| Component role | `DESCRIPTIVE_DIAGNOSTIC_ONLY` | registered analysis |

The strongest permitted claim is limited to no confirmatory interaction
evidence under the exact model pair, synthetic testbed, prompt/parser, budget
grid, and controlled BICUBIC Input Resolution Reduction. Equivalence, equal
robustness, post-encoder compression, mechanism, causal training effects, and
external validity remain unsupported.

## Analysis artifact preservation

Canonical directory:
`runs/kaggle/kaggle-paddle-wayu-locked-panel-attempt5/analysis/`

| File | Bytes | SHA-256 |
|---|---:|---|
| `analysis_rows.csv` | 1,324,006 | `4456be1bdf509f17c2739179f4d7d9d58d0fdcc3ebf9a9486b94e2c957964cb0` |
| `analysis_state.json` | 194 | `a007950cd538652c284173286272a781d8ba14b27f5b8804ddaac413d924d78a` |
| `full_validity.json` | 561 | `2599596e977a418f307e8cdae605afc26f0bbca363b759da43a83806d397c159` |
| `glmm_result.json` | 377 | `be83e48659cb237aacfc4e415e7373628d6a848c9450b6730912dbd36d4112ff` |
| `registered_analysis.json` | 12,512 | `10aa81a469ea7cdb5cac3780111ad6ae9bc378e2ac0a91704c690179315ee1c0` |
| `ANALYSIS_COMPLETION_MANIFEST.json` | 2,093 | `325bee6f61fd62326130285d2eef9551ad8dbf7dffc83a75fac6a3619e3b509b` |

ทุกไฟล์ข้างต้นถูกตั้ง read-only หลังตรวจ hash ส่วน analysis ที่หยุดก่อน
exception-eligibility amendment ถูกเก็บแยกโดยไม่ overwrite ที่
`analysis_pre_exception_eligibility_amendment/` และตั้ง read-only เช่นกัน

## Method and implementation audit

- `STATISTICAL_METHOD_DIFF = ONLY_FALLBACK_ELIGIBILITY_TRIGGER_CHANGED`
- `FALLBACK_IMPLEMENTATION_DIFF = EMPTY`
- `GLMM_FORMULA_DIFF = EMPTY`
- `FALLBACK_ESTIMAND_DIFF = EMPTY`
- `DECISION_CLASSIFIER_DIFF = EMPTY`

หลัง analysis เสร็จ พบ test portability issue: R-script byte hash ที่ลงทะเบียน
เป็น CRLF แต่ main working tree อาจ materialize เป็น LF โดยมี text เดียวกัน
จึงเพิ่ม path-specific `.gitattributes` และตรวจ hash ด้วย canonical CRLF bytes
พร้อม test สำหรับ LF/CRLF equivalence และ rejection ของ bare CR การแก้นี้ไม่
เปลี่ยน R source, model formula, fallback หรือ scientific result และไม่มีการรัน
analysis ซ้ำ

## Validation

- focused runner suite: `12 passed`
- full suite: `228 passed, 1 skipped`
- skip: optional `kaggle` module unavailable in
  `test_kaggle_savekernel_diagnostic.py`
- research consistency: `valid=true`, `issues=[]`
- clean detached-worktree preflight at
  `cffb3663bf652a09aba3149b85eae68844ccd6aa`:
  `git_clean=true`, `missing_paths=[]`, `valid=true`
- detached-worktree R identities:
  - `run_glmm.R` =
    `c03e97127da934a338146de0487bdb774f085289444fdd0e99a9195d4b9be3a1`
  - `glmm_failure_contract.R` =
    `82d0e2461f2f5be04e7cd1da3d5838cfd0fb690c1d947ec1fbffb3f900c99365`

The Windows parent process emitted one background reader-thread
`cp874 UnicodeDecodeError` after structured analysis outputs were produced.
The registered command exited 0, artifacts were complete and hashable, and no
rerun occurred. This is retained as an engineering observation.

## Source-of-Truth synchronization

Updated and reconciled:

- `docs/stage0/PADDLE_WAYU_LOCKED_MODEL_BUDGET_REPORT.md`
- `docs/DECISION_LOG.md`
- `docs/CLAIMS.md`
- `docs/RESEARCH_SPEC.md`
- `docs/EXPERIMENT_PROTOCOL.md`
- `docs/OVERALL_MODEL_BUDGET_FREEZE.md`
- `docs/stage0/PADDLE_WAYU_PRIMARY_ANALYSIS_SPEC.md`
- `docs/stage0/PADDLE_WAYU_GATE0_LOCKED_PROTOCOL.md`
- `docs/exec-plans/active/ADVISOR_READINESS.md`

Pre-execution labels retained in frozen historical documents are explicitly
marked historical and point to the final report. Failure and amendment history
was preserved.

User-owned untracked paths were deliberately left untouched and excluded from
the synchronization commit: `README.md`, `assets/presentation/`,
`docs/paper/`, `docs/presentation/`, and `docs/stage0/debug/`.

## Final boundary

ไม่มี experiment หรือ analysis เพิ่มเติมที่ได้รับอนุญาต ข้อเสนอแนะเดียวคือ
human review ของ registered result, claim boundary และ post-data-access
amendment disclosure ก่อนตัดสินขั้นต่อไป

`HUMAN_REVIEW_AFTER_LOCKED_MODEL_BUDGET_PANEL`
