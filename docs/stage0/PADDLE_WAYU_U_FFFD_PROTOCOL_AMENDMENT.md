# Paddle/Wayu U+FFFD Per-Call Protocol Amendment

วันที่: 2026-09-13

สถานะการอนุมัติ: `U_FFFD_PER_CALL_PROTOCOL_AMENDMENT_LOCAL_VALIDATION_AUTHORIZED`

Impact classification: `SCIENTIFIC_RUN_CONTROL_AND_FAILURE_TAXONOMY_AMENDMENT`

## 1. Decision timing และ evidence boundary

Amendment นี้เกิดขึ้น **หลัง** Attempt 4 หยุดระหว่าง partial locked execution แต่
**ก่อน** inspection ของ Attempt-4 scientific output ใด ๆ จึงเป็น post-failure
protocol amendment ที่ทำภายใต้ outcome blinding ไม่ใช่กฎที่ preregister ไว้ก่อน
Attempt 4

เหตุผลของ amendment ใช้เพียง:

- S0 open-calibration 1,520 outputs
- approved tokenizer-only synthetic diagnostic
- taxonomy `output_contract_failure` ที่มีอยู่ก่อนแล้ว
- frozen FULL validity threshold ที่กำหนด output-contract failure ไม่เกิน 1%
  ต่อ model

Attempt 4 ยังคง `PARTIAL_SCIENTIFIC_OUTPUTS_SEALED` และไม่มี prediction,
token tail, factor identity, accuracy, CER, DID, omnibus statistic หรือ component
result ถูกเปิดตรวจ

## 2. Exact amendment

OLD:

```text
successful processor.decode() result contains U+FFFD
-> abort the entire run as a fatal Unicode decoding error
```

NEW:

```text
successful processor.decode() result contains one or more U+FFFD codepoints
-> preserve raw decoded output and raw generated token IDs unchanged
-> output_contract_failure = true
-> output_contract_failure_reason = U_FFFD_REPLACEMENT_CHARACTER
-> primary exact = 0
-> retain observation in denominator and contract-failure rate
-> no retry, regeneration, repair, deletion, replacement, or normalization
-> continue to the next registered call
```

Amendment นี้ใช้เฉพาะกรณี decoder คืน Python string สำเร็จแล้วและ string นั้นมี
U+FFFD เท่านั้น Exception ก่อนมี scientifically valid generated token sequence,
model/CUDA failure, non-finite tensor, input/provenance/hash/revision mismatch,
token-prefix/output-boundary corruption และกรณีกำกวมยังคง fail closed

## 3. Scientific fields

ค่าที่ตรวจยืนยันว่าไม่เปลี่ยน:

- `GENERATION_FUNCTION_CHANGED = false`
- `DECODER_CHANGED = false`
- `PRIMARY_VALID_OUTPUT_SCORING_CHANGED = false`
- model IDs และ revisions
- processor และ tokenizer
- prompt `OCR:`
- `do_sample=false`, `num_beams=1`, `max_new_tokens=32`, `use_cache=true`
- EOS behavior และ output slicing
- `skip_special_tokens=True`
- `clean_up_tokenization_spaces=False`
- Unicode normalization และ primary parser
- target strings, pair allocation, images, fonts และ sizes
- four input-resolution budgets และ BICUBIC resize pipeline
- exact-match definition, CER formula และ denominator
- random-effects structure, statistical tests, SESOI, Holm procedure และ decision classifier
- output-contract-failure threshold 1% ต่อ model ที่ FULL

ค่าที่ตั้งใจเปลี่ยนเพียง:

- `INVALID_OUTPUT_RUN_BEHAVIOR_CHANGED = true`
- U+FFFD หลัง successful decode เปลี่ยนจาก fatal run abort เป็น retained per-call
  `output_contract_failure`

จึงไม่จัด amendment นี้เป็น engineering-only

## 4. Implementation

Runner ใช้ frozen generation call และ frozen decoder เดิม จากนั้นเรียก
`decode_generated_tokens()` เพื่อบันทึกข้อมูลต่อไปนี้ลง sealed scientific record:

- generated token count
- EOS reached
- `max_new_tokens` reached
- raw generated token IDs
- decoded raw output
- U+FFFD presence flag
- `output_contract_failure` และ reason code

ไม่มี field เหล่านี้ถูกเพิ่มใน live print การรายงานระหว่าง execution ยังคงเป็น
`ENGINEERING_PROGRESS completed_calls=<n>/6400` และไม่เปิด model, budget,
`pair_id`, decoded output, U+FFFD count, cap/EOS rate หรือ scientific identity

Analysis ตรวจซ้ำว่า sealed flags/reason ตรงกับ raw decoded string หากไม่ตรงจะ
fail closed จากนั้น U+FFFD ถูกจัดเป็น `output_contract_failure`, exact score เป็น
0 และ observation ยังคงอยู่ใน analysis rows

## 5. S0 open replay equivalence

Classification: **`S0_SCIENTIFIC_OUTPUT_EQUIVALENCE_PASS`**

ใช้ S0 open-calibration token IDs และ exact-decoder evidence เทียบ OLD กับ
AMENDED pipeline:

| Check | Result |
|---|---:|
| raw decoded output identical | 1,520/1,520 |
| primary parsed output identical | 1,520/1,520 |
| exact classification identical | 1,520/1,520 |
| output-contract taxonomy identical | 1,520/1,520 |
| existing per-call scientific fields identical | 1,520/1,520 |
| generated token IDs/counts identical | 1,520/1,520 |
| denominator | 1,520 -> 1,520 |
| new exclusions | 0 |
| all existing S0 scientific metrics identical | PASS |

Exact accuracy estimates คงเดิม:

- BASE: `0.29736842105263156` -> `0.29736842105263156`
- SPECIALIZED: `0.45526315789473687` -> `0.45526315789473687`

ตัวเลขเหล่านี้เป็น open S0 baseline เท่านั้น ไม่ใช่ locked-panel result หรือ
MODEL × BUDGET evidence

## 6. CER semantics audit

ผล: **`EXISTING_CER_RULE_UNAMBIGUOUS_AND_PRESERVED`**

Implementation เดิมคำนวณ CER สำหรับทุก observation ด้วย:

```text
parsed_output = raw_output.strip()
codepoint_cer = codepoint_edit_distance(parsed_output, target)
                / max(1, len(target))
```

กฎนี้ทำงานก่อน/โดยไม่ขึ้นกับการช่วยแก้ output และใช้ Unicode codepoint เป็นหน่วย
U+FFFD จึงยังอยู่ใน `parsed_output` และถูกนับด้วย edit-distance สูตรเดิม ตัวอย่าง
synthetic U+FFFD เทียบ target หนึ่ง codepoint ให้ exact=0 และ CER=1.0 ไม่มีการเพิ่ม
CER rule ใหม่

## 7. Synthetic failure injection และ continuation

ทั้ง BASE และ SPECIALIZED exact tokenizer/processor จาก approved diagnostic ให้:

```text
generated token IDs: [94377]
token piece: U+FFFD
processor.decode(): U+FFFD
tokenizer.decode(): U+FFFD
```

Validation ยืนยันว่า:

- observation แรกถูกเก็บเป็น `output_contract_failure`
- reason เท่ากับ `U_FFFD_REPLACEMENT_CHARACTER`
- exact score เท่ากับ 0 และ denominator retained
- U+FFFD คงอยู่ใน raw sealed output โดยไม่ถูก repair
- processing ไปยัง observation ถัดไปได้
- decoder ถูกเรียกหนึ่งครั้งต่อ observation และไม่มี retry
- live telemetry ไม่มี decoded output หรือ scientific identity
- synthetic decoder exception ที่ไม่ใช่ successful-U+FFFD return ยังคง fatal

## 8. Attempt 4 integrity

ตรวจเฉพาะ byte/container-level identity โดยไม่เปิด ZIP content:

- state: `PARTIAL_SCIENTIFIC_OUTPUTS_SEALED`
- completed calls ที่อนุญาตให้รายงาน: 4,136
- phase: `model_execution`
- ZIP size: 13,052,397 bytes
- read-only: true
- SHA-256:
  `e6db8c69b530464bbebdcfa0c8640c1b3c1f771d4b5f89fcb71ef2af8cca8127`
- scientific outputs inspected: false
- failure scientific identity mapped: false
- Attempt-4 observations reused: 0

Attempt 4 ต้องไม่ถูก resume, merge, compare หรือใช้ใน future confirmatory dataset

## 9. Local validation

- focused amendment, synthetic, locked-analysis และ bootstrap/core integration:
  `31 passed`
- full pytest: `191 passed, 1 skipped`
- skipped test เป็น optional Kaggle-package import เพราะ local environment ไม่มี
  package `kaggle`; ไม่เกี่ยวกับ amendment logic
- `scripts/check_research_consistency.py`: `valid=true`, issues 0
- clean detached-worktree preflight: `valid=true`, `git_clean=true`,
  `missing_paths=[]`
- S0 replay: `S0_SCIENTIFIC_OUTPUT_EQUIVALENCE_PASS`
- no locked image generation
- no locked inference
- no SaveKernel call
- no Attempt 5 identity

Machine-readable evidence:

`docs/stage0/evidence/paddle_wayu_u_fffd_protocol_amendment/AMENDMENT_VALIDATION.json`

## 10. Changed files

Core amendment:

- `src/labbs2026/stage0/paddle_wayu_locked_panel.py`
- `src/labbs2026/stage0/locked_panel_analysis.py`
- `src/labbs2026/stage0/paddle_wayu_u_fffd_protocol_amendment.py`
- `scripts/paddle_wayu_u_fffd_protocol_amendment.py`
- `tests/test_paddle_wayu_locked_panel.py`
- `tests/test_paddle_wayu_u_fffd_protocol_amendment.py`

Protocol/evidence:

- `docs/EXPERIMENT_PROTOCOL.md`
- `docs/DECISION_LOG.md`
- `docs/stage0/PADDLE_WAYU_U_FFFD_PROTOCOL_AMENDMENT.md`
- `docs/stage0/evidence/paddle_wayu_u_fffd_protocol_amendment/AMENDMENT_VALIDATION.json`

Accepted open diagnostic files are committed with this local amendment because
the validator depends on their immutable evidence; unrelated existing untracked
presentation/paper files are not included

## 11. Publication disclosure draft

> An initial locked execution was terminated after a decoded model output
> contained the Unicode replacement character U+FFFD. No locked predictions or
> performance statistics from that partial execution were inspected. Using only
> open calibration outputs and tokenizer-level synthetic diagnostics, we found
> that U+FFFD could arise through multiple decoding or token-sequence
> mechanisms. Before rerunning the locked experiment, we amended the protocol
> so that such outputs were retained as per-example output-contract failures and
> scored incorrect for primary exact accuracy rather than aborting the full run.
> Model generation, decoding parameters, data, budgets, and primary statistical
> analysis were unchanged. The failed partial execution was excluded from all
> scientific analyses.

ข้อความนี้ไม่อ้างว่า truncation เป็นสาเหตุของ Attempt 4

## 12. Recommendation และ stop state

คำแนะนำเพียงหนึ่งอย่าง:

**`KEEP_ATTEMPT5_BLOCKED_PENDING_EXPLICIT_HUMAN_AUTHORIZATION`**

Terminal state:

**`U_FFFD_PROTOCOL_AMENDMENT_VALIDATED_PENDING_ATTEMPT5_AUTHORIZATION`**

เอกสารนี้ไม่อนุมัติ Attempt 5
