# Attempt 4 — Debug handoff

## 1. Executive summary

Attempt 4 ถูกส่งไป Kaggle ด้วย SaveKernel call เพียงครั้งเดียวและหยุดแบบ
fail-closed ที่ phase `model_execution` เพราะ `RuntimeError: Unicode decoding
corruption` หลังบันทึก engineering ledger ครบ `4,136 / 6,400` calls แล้ว
Kaggle kernel version ใหม่มีอยู่จริงและจบด้วย `ERROR`; authenticated API ที่ใช้
ยืนยัน session/output ไม่คืน numeric version จึงไม่บันทึกเลข version เป็น FACT
(เลข 3 เป็นเพียง inference)

CUDA/T4 preflight ผ่านและมีการโหลด weights สองครั้งตามลำดับ runner. มี partial
scientific outputs สองไฟล์ แต่ไม่เคยเปิด อ่าน parse แสดง หรือคำนวณ metric ใด ๆ
จากไฟล์เหล่านั้น ไม่มี retry/resubmission และไม่รัน registered analysis.

## 2. Exact identities

- `run_id`: `kaggle-paddle-wayu-locked-panel-attempt4`
- `attempt`: `4`
- authorization: `LOCKED_PANEL_RERUN_AUTHORIZED`
- `SCIENTIFIC_DESIGN_COMMIT`: `871996221a36a56a401fa040c239f55768561210`
- `EXECUTION_COMMIT`: `1f028e243ad3890377159f04efc35c01a3bac6a7`
- local/remote commit: `1f028e243ad3890377159f04efc35c01a3bac6a7`
- Dataset: `thanakritsamoena/labbs2026-paddle-wayu-locked-source`, ID
  `12006749`, version `1`, private
- frozen-design SHA-256:
  `6143c454337570217c9cd028522de510b4fd5b4f9f361fa0ea206014eed185a1`
- content-manifest SHA-256:
  `5b0983c7cc75e2904ac240ef0adc0472a9bf2bbe4695fb0669f7f9f36e2eaebb`
- source-bundle SHA-256:
  `9edff88382c51ed4d48a073813b4309535fb34ba5318ea85ca8ea6da75bc229e`
- runtime-config SHA-256:
  `626484d85f252852f2b97e2ab18f529c55c56a5e62a06955ca90858adc829e5a`
- Kaggle kernel:
  `thanakritsamoena/labbs2026-paddle-wayu-locked-model-budget-panel`
- Kaggle output session ID: `349542013`

## 3. Exact exception

Exception class: `RuntimeError`

Message: `Unicode decoding corruption`

```text
Traceback (most recent call last):
  File "/tmp/labbs2026-source/src/labbs2026/stage0/paddle_wayu_locked_panel.py", line 518, in execute_remote_panel
    manifest, runtime, completed = _run_model(
                                   ^^^^^^^^^^^
  File "/tmp/labbs2026-source/src/labbs2026/stage0/paddle_wayu_locked_panel.py", line 419, in _run_model
    raise RuntimeError("Unicode decoding corruption")
RuntimeError: Unicode decoding corruption
```

Full subprocess stderr, including both weight-loading records, warnings, and the
exact traceback, is preserved byte-for-byte in
`runs/kaggle/kaggle-paddle-wayu-locked-panel-attempt4/failure_fetch/artifacts/_bootstrap_failures/kaggle-paddle-wayu-locked-panel-attempt4.json`
(SHA-256
`a0f6749e22ef39d639352dd374f14242586f03293f6d1458d84f6dd946112734`).
The earlier `wrapt` sitecustomize warning was non-fatal; execution proceeded
through CUDA, model loading, and 4,136 completed calls.

## 4. Last successful phase

`CALL_4136` — confirmed only from engineering ledger line count and the failure
record's `scientific_completed_call_count`.

## 5. First failing phase

`model_execution`, during decoded Unicode validation before the next raw record
and ledger row could be appended.

## 6. Artifact inventory

Present:

- `engineering/AUTHORIZATION_VALIDATED.json`
- `engineering/CORE_OWNERSHIP_CLAIMED.json`
- `engineering/environment_manifest.json`
- `engineering/call_ledger.jsonl` — 4,136 lines
- `engineering/FAILURE.json`
- `sealed/raw_outputs_base.jsonl` — preserved unopened
- `sealed/raw_outputs_specialized.jsonl` — preserved unopened
- `sealed/source_448/`
- `sealed/stimuli/`

Missing because finalization was never reached:

- `engineering/model_revision_manifest.json`
- `engineering/runtime_report.json`
- `engineering/execution_manifest.json`
- `checksums.sha256`
- `SUCCESS.json`

Kaggle listed 4,013 output files. The immutable ZIP contains those files plus
`__huggingface_repos__.json`: 4,014 entries, 13,052,397 bytes, SHA-256
`e6db8c69b530464bbebdcfa0c8640c1b3c1f771d4b5f89fcb71ef2af8cca8127`.
The ZIP is read-only at
`runs/kaggle/kaggle-paddle-wayu-locked-panel-attempt4/attempt4_remote_failure_artifacts_v2.zip`.
Directories `failure_fetch/` and `failure_fetch_complete/` and the zero-byte
`attempt4_remote_failure_artifacts.zip` are incomplete local download attempts;
they are not canonical evidence and were not used in place of the immutable ZIP.

Raw-output SHA-256 values were computed without parsing content:

- base: `d50360c46a19bdfe425b89dbdb081e489cfe0af123dd5aee00975f4483cd1782`
- specialized: `757502614cec647704335af04955ff665799856617adefb1a461a6aae3284ec0`

## 7. Remote Kaggle state

- status: `ERROR`
- `lastRunTime`: `2026-09-13T14:30:22.317000Z`
- failure timestamp: `2026-09-13T14:42:04.170281Z`
- remote log exists; local CLI rendering hit a CP874 encoding error on Thai text
- exact stderr was nevertheless preserved by the worker failure channel
- numeric kernel version: UNKNOWN from the authenticated API; a new version
  existed because SaveKernel succeeded, `lastRunTime` changed, a new output
  session exists, and its artifacts were downloaded

## 8. Scientific-integrity assessment

`PARTIAL_SCIENTIFIC_OUTPUTS_SEALED`

เหตุผล: มี ledger 4,136 calls และ raw files สองไฟล์ แต่ยังไม่ครบ 6,400 calls,
ไม่มี final checksums, ไม่มี `SUCCESS.json`, ไม่ผ่าน local `VERIFIED`, และไม่เคย
เปิด scientific output หรือรัน accuracy/CER/DID/omnibus/component analysis.

## 9. Root-cause analysis

### FACT

- guard ที่ `paddle_wayu_locked_panel.py:418-419` ล้มหลัง
  `processor.decode(...)`.
- เงื่อนไขรวมจะล้มเมื่อ decoded string มี U+FFFD แม้ U+FFFD เอง round-trip ผ่าน
  strict UTF-8 ได้ (`ef bf bd`).
- T4/CUDA preflight และ model weight loading ผ่าน.
- ไม่มี NaN, token-accounting, provenance, authorization หรือ ownership failure
  ถูกบันทึก.

### INFERENCE

- immediate trigger คือการพบ Unicode replacement character U+FFFD ไม่ใช่
  Python UTF-8 round-trip failure.
- การตัด byte-level token sequence ที่ `max_new_tokens` เป็นกลไกหนึ่งที่เป็นไปได้.

### UNKNOWN

- U+FFFD เกิดจาก generation truncation, tokenizer byte fallback หรือ decode path
  อื่น เพราะ failing token tail ไม่ถูกบันทึกก่อน exception.
- ไม่ทราบว่า failing generation ชน `max_new_tokens` หรือไม่.
- numeric Kaggle kernel version ไม่ถูกเปิดเผยโดย endpoint ที่ authenticated อยู่.

## 10. Root-cause classification

`UNICODE_DECODE_VALIDATION_FAILURE`

## 11. Minimal reproduction

```powershell
uv run python -c "s='\ufffd'; print(s.encode('utf-8').decode('utf-8') == s, '\ufffd' in s)"
```

ผลคือ `True True`: แสดงว่า compound guard แยก "valid U+FFFD code point" ออกจาก
"failed UTF-8 round trip" ไม่ได้ แต่ไม่ได้พิสูจน์ต้นกำเนิดของ U+FFFD ใน model
output.

## 12. Narrowest proposed repair

ยังไม่ implement patch เพราะเกิด scientific calls แล้วและ absolute failure rule
กำหนดให้หยุดเพื่อ human review.

diagnostic-only proposal:

1. แยก strict UTF-8 round-trip check กับ U+FFFD-presence check ใน
   `src/labbs2026/stage0/paddle_wayu_locked_panel.py::_run_model`.
2. ก่อน raise ให้บันทึกเฉพาะ engineering fields:
   `generated_token_count`, `hit_max_new_tokens`, `generated_token_tail_ids`,
   `utf8_roundtrip_ok`, `replacement_character_present`, `call_index`, `call_id`
   โดยไม่บันทึก decoded text ใน engineering channel.
3. เพิ่ม unit tests ใน `tests/test_paddle_wayu_locked_panel.py` สำหรับ U+FFFD
   round trip และ diagnostic evidence.

ข้อเสนอนี้ช่วยหาสาเหตุแต่ยังไม่ทำให้ rerun ผ่าน. หากจะยอมให้ U+FFFD เข้า raw
output, เปลี่ยน `max_new_tokens`, เปลี่ยน `processor.decode`, parser หรือ Unicode
scoring จะกระทบ frozen scientific contract และต้องมี human scientific-design
review ใหม่: `SCIENTIFIC_DESIGN_CHANGE_REQUIRED`.

## 13. Forbidden repairs

- silently allow/replace U+FFFD
- เปลี่ยน decoding หรือ `max_new_tokens`
- เปลี่ยน prompt, parser, Unicode scoring, models, budgets หรือ inputs
- ตัด/แทน observation ที่ล้ม
- วิเคราะห์ partial 4,136 outputs
- retry หรือ submit Kaggle version ใหม่

## 14. Recommended next action

`SCIENTIFIC_PARTIAL_RUN_REVIEW_REQUIRED`

ไม่มี scientific design change, ไม่มี local code patch, ไม่มี push เพิ่ม และไม่มี
resubmission.
