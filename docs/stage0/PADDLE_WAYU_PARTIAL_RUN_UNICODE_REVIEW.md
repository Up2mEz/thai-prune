# Paddle/Wayu Partial-Run Unicode Review

วันที่ตรวจ: 2026-09-13
ขอบเขต: `OPEN_DATA_UNICODE_FAILURE_DIAGNOSTIC_ONLY`

## 1. Attempt 4 integrity และ execution blinding

Attempt 4 ยังคงมีสถานะ `PARTIAL_SCIENTIFIC_RUN_FAILURE_PENDING_HUMAN_REVIEW` และ scientific-integrity state เป็น `PARTIAL_SCIENTIFIC_OUTPUTS_SEALED`

- failure เกิดระหว่าง `model_execution` หลังจบ scientific calls แล้ว 4,136 calls
- ไม่ได้เปิด อ่าน decode หรือวิเคราะห์ scientific outputs ของ Attempt 4
- ไม่ได้ map failure location ไปยัง model, budget, `pair_id`, member, font, font size หรือ component
- ตรวจเฉพาะระดับ container: ZIP ขนาด 13,052,397 bytes, read-only และ SHA-256 ตรงกับค่าที่มนุษย์อนุมัติ คือ `e6db8c69b530464bbebdcfa0c8640c1b3c1f771d4b5f89fcb71ef2af8cca8127`
- ไม่ได้สร้าง locked images, ไม่ได้ทำ model inference, ไม่ได้สร้างหรือ submit Attempt 5

ดังนั้น Attempt 4 **ยัง sealed และ immutable** ภายใต้ขอบเขตการตรวจครั้งนี้

## 2. คำถามและแหล่ง open data

คำถามคือ U+FFFD สามารถเกิดจากการตัด generation ที่ `max_new_tokens=32` กลางชุด byte-fallback ได้หรือไม่ และหลักฐาน S0 ที่เปิดแล้วช่วยแยกสาเหตุได้เพียงใด

ใช้เฉพาะ S0 open-calibration artifact:

`runs/kaggle/kaggle-paddle-wayu-s0-a7f3eec06bce-832fe44f/fetched/artifacts/kaggle-paddle-wayu-s0-a7f3eec06bce-832fe44f`

| Artifact | SHA-256 |
|---|---|
| `raw_outputs.jsonl` | `c94fdcb2c82cba5d1b6b8dcb6876b21bc41362d21c2fe17af0acea60f774442e` |
| `model_revision_manifest.json` | `0b502e6a37b8e199aa16ebfcdbc2eb06b8a1a83114ce90d2881ab384180f2c21` |
| `environment_manifest.json` | `2e0ef4581f8f96e44e6414bd8d19c8c5cc5377fb4bc04bc52ae63710103e3edd` |

Exact processors ถูกโหลดแบบ tokenizer/processor-only ที่ revisions เดิม:

| Role | Model | Revision | Processor / tokenizer |
|---|---|---|---|
| BASE | `PaddlePaddle/PaddleOCR-VL-1.6` | `c5630abae1d940eafe0697512a0325494b02ab42` | `PaddleOCRVLProcessor` / `LlamaTokenizer` |
| SPECIALIZED | `wayu-ai/wayu-paxa-ocr-zero` | `af0204b4f334a6d5068b6bac2b3738932d6e289b` | `PaddleOCRVLProcessor` / `LlamaTokenizer` |

Diagnostic ใช้ Python 3.12.13 และ `transformers==5.12.0` ตรงกับ S0 environment พร้อม frozen decode settings:

```text
skip_special_tokens=True
clean_up_tokenization_spaces=False
max_new_tokens=32
```

ไม่มีการโหลด model weights และไม่มี model inference

## 3. S0 token-length และ U+FFFD audit

### Token-length distribution

| Generated tokens | BASE | SPECIALIZED | รวม |
|---:|---:|---:|---:|
| 2 | 198 | 172 | 370 |
| 3 | 466 | 524 | 990 |
| 4 | 67 | 16 | 83 |
| 5 | 10 | 31 | 41 |
| 6 | 5 | 1 | 6 |
| 7 | 4 | 11 | 15 |
| 8 | 4 | 2 | 6 |
| 9 | 2 | 0 | 2 |
| 10 | 1 | 0 | 1 |
| 11 | 2 | 0 | 2 |
| 32 | 1 | 3 | 4 |
| **รวม** | **760** | **760** | **1,520** |

ผลที่ตรวจพบ:

- จบด้วย EOS: 1,516/1,520 outputs
- ถึง `max_new_tokens=32` โดยไม่มี EOS: 4/1,520 = **0.2632%**
- พบ U+FFFD: 0/1,520 = **0%**
- ใน 4 cap-reaching outputs decode ถูกต้องโดยไม่มี U+FFFD ทั้ง 4/4 = **100%**
- `processor.decode()` ต่างจาก `tokenizer.decode()`: 0/1,520
- re-decode ต่างจาก `raw_output` ที่บันทึกใน S0: 0/1,520

ผลนี้แปลว่า “ถึง cap” ไม่เพียงพอที่จะทำให้เกิด U+FFFD และ S0 ไม่มี U+FFFD tail pattern ให้หาความสัมพันธ์ อย่างไรก็ดี จำนวน cap hits มีเพียง 4 จึงไม่สามารถใช้ปฏิเสธกลไก truncation ได้

## 4. Tokenizer-only synthetic reproduction

ทดสอบโดยไม่ใช้ภาพและไม่ทำ inference ตัวอย่าง byte fallback ที่สัมพันธ์กับอักขระไทย:

| Text | Codepoint | UTF-8 bytes | Token IDs | Token pieces |
|---|---|---|---|---|
| `ก` | `U+0E01` | `E0 B8 81` | `237 197 142` | `<0xE0> <0xB8> <0x81>` |
| `่` | `U+0E48` | `E0 B9 88` | `237 198 149` | `<0xE0> <0xB9> <0x88>` |
| `ำ` | `U+0E33` | `E0 B8 B3` | `237 197 192` | `<0xE0> <0xB8> <0xB3>` |

ทั้งสอง exact tokenizers ให้ผลเหมือนกัน:

- byte sequence ครบ 3 bytes decode เป็น codepoint เดิมโดยไม่มี U+FFFD
- ตัดหลัง byte ที่ 1 หรือ 2 แล้ว decode ทำให้เกิด U+FFFD
- สร้าง sequence ยาว 32 tokens ที่ token สุดท้ายเป็น byte prefix ไม่ครบ ทำให้เกิด U+FFFD ภายใต้สถานการณ์จำลอง `MAX_NEW_TOKENS`
- byte prefix ไม่ครบแล้วตามด้วย EOS ก็ทำให้เกิด U+FFFD ได้ จึงพิสูจน์ว่า U+FFFD **ไม่จำเป็นต้องเกิดจาก max-token truncation เท่านั้น**
- vocabulary มี token เดี่ยว ID `94377` ซึ่ง token piece และ decoded string เป็น U+FFFD โดยตรงสำหรับทั้งสอง tokenizers จึงยังมี alternative mechanism ที่ไม่เกี่ยวกับ incomplete byte tail
- ทั้ง 48 Thai byte-fallback synthetic cases ให้ `processor.decode()` เท่ากับ `tokenizer.decode()`; literal-U+FFFD case ก็เท่ากัน

นี่เป็น engineering/tokenizer observation เท่านั้น ไม่ใช่หลักฐาน model accuracy หรือ model behavior ใน Attempt 4

## 5. H_TRUNC evaluation

สถานะ: **`SUPPORTED_MECHANISTICALLY`**

พิสูจน์ได้ว่า `max_new_tokens` สามารถตัด sequence หลัง byte-fallback prefix ที่ยังไม่ครบและทำให้ frozen decoder คืน U+FFFD ได้จริง

แต่ยังพิสูจน์ไม่ได้ว่า Attempt 4 เกิดจากกลไกนี้ เพราะ:

1. scientific token tail ของ Attempt 4 ยัง sealed และไม่ได้ตรวจ
2. S0 cap hits ทั้ง 4 ไม่เกิด U+FFFD
3. synthetic reproduction แสดง U+FFFD โดยไม่ต้องถึง cap ได้
4. tokenizer สามารถ decode token U+FFFD โดยตรงได้

ดังนั้น `SUPPORTED_MECHANISTICALLY` หมายถึงรองรับความเป็นไปได้ของกลไก ไม่ใช่ยืนยัน root cause ของ Attempt 4

## 6. Alternative mechanisms

| Mechanism | Open-data status | การตีความ |
|---|---|---|
| cap ตัด incomplete byte fallback | reproduced | เป็นไปได้ทางกลไก แต่ไม่ยืนยันว่าเกิดใน Attempt 4 |
| incomplete byte fallback ก่อน EOS | reproduced | U+FFFD เกิดได้โดยไม่ชน cap |
| generated token แทน U+FFFD โดยตรง | tokenizer-only reproduced | ID `94377` decode เป็น U+FFFD; ยังไม่ทราบว่า model สร้าง token นี้ใน Attempt 4 หรือไม่ |
| `processor.decode` เฉพาะทางต่างจาก tokenizer | ไม่พบ | ทั้ง S0 และ synthetic ที่ทดสอบให้ผลตรงกัน แต่ยังไม่ใช่ proof สำหรับ token sequences ทุกแบบ |
| tokenizer decode defect | ไม่ยืนยัน | behavior ที่พบสอดคล้องกับ replacement decoding ของ incomplete UTF-8; ไม่มีหลักฐานว่า implementation ผิดสเปก |

## 7. OLD_PIPELINE กับ candidate NEW_PIPELINE

นิยาม OLD_PIPELINE:

```text
processor.decode(tokens,
  skip_special_tokens=True,
  clean_up_tokenization_spaces=False)
```

เกณฑ์ engineering-only repair ต้องรักษา Unicode-codepoint output ของทุก valid token sequence เดิม และต้องทำให้ execution จบได้โดยไม่เปลี่ยน scientific prediction function

| Candidate | Open S0 equivalence | แก้ failure ได้หรือไม่ | Classification |
|---|---|---|---|
| เพิ่ม observability แต่ใช้ decoder เดิม | เท่ากันโดยโครงสร้าง; output function ไม่เปลี่ยน | ไม่ได้ เพียงอธิบาย failure ได้ดีขึ้น | engineering-only instrumentation แต่ไม่ใช่ repair ที่ทำให้ panel จบ |
| เปลี่ยนเป็น `tokenizer.decode` ด้วย kwargs เดิม | เท่ากัน 1,520/1,520 และ synthetic ที่ทดสอบ | ไม่ได้ เพราะยังคืน U+FFFD ในทุก reproduction | ไม่เพียงพอ |
| เพิ่ม `max_new_tokens` | ไม่สามารถรับประกัน; 4 S0 cap outputs อาจยาวขึ้น | อาจลด truncation แต่ไม่แก้ direct-U+FFFD/EOS mechanism | `SCIENTIFIC_CONTRACT_AMENDMENT_REQUIRED` |
| accept/score/strip/replace U+FFFD | เปลี่ยน handling ของ token sequence ที่เป็นเหตุ | ทำให้เดินหน้าต่อได้ตามกฎใหม่ | `SCIENTIFIC_CONTRACT_AMENDMENT_REQUIRED` |
| strict/manual byte decoding | valid S0 อาจเท่ากัน แต่ invalid sequence จะเปลี่ยน exception/output | ไม่แก้จนกว่าจะกำหนด handling ใหม่ | `SCIENTIFIC_CONTRACT_AMENDMENT_REQUIRED` |
| generate ต่อจน EOS หรือจน byte sequence ครบ | เปลี่ยน termination และอาจเปลี่ยน exact output | อาจหลีกเลี่ยง incomplete tail | `SCIENTIFIC_CONTRACT_AMENDMENT_REQUIRED` |

คำตอบต่อ decision question คือ **NO หรืออย่างน้อย UNKNOWN สำหรับ repair ที่ทำให้ run จบได้** การเพิ่ม observability เพียงอย่างเดียวรักษา exact function ได้แต่ไม่แก้ failure; candidate ที่อนุญาตให้ execution เดินหน้าผ่าน U+FFFD ล้วนเปลี่ยนหรือยังพิสูจน์ไม่ได้ว่าจะรักษา scientific prediction function

## 8. Repair และ protocol impact

### Repair Class A — engineering-only observability

ทำได้บน open data และไม่เปลี่ยน prediction function เช่นบันทึก generated-token count, EOS/cap stop class และ safe token-tail context ก่อน decode แต่ **ไม่เพียงพอเป็น operational repair** เพราะ frozen guard ยังต้องหยุดเมื่อพบ U+FFFD

### Repair Class B — เปลี่ยน `max_new_tokens`

`SCIENTIFIC_CONTRACT_AMENDMENT_REQUIRED` เพราะ generation function เปลี่ยน อาจเปลี่ยน outputs ที่เคยชน cap และ future outputs ต้อง rerun/recalculate S0 ภายใต้ contract ใหม่, re-freeze Gate criteria และหากอนุมัติในอนาคตต้องใช้ full locked run ใหม่ การตีพิมพ์ต้องเปิดเผย Attempt 4 partial failure และ amendment ก่อน rerun

### Repair Class C — เปลี่ยน U+FFFD handling

`SCIENTIFIC_CONTRACT_AMENDMENT_REQUIRED` การ accept, score as incorrect, classify เป็น output-contract failure, strip หรือ replace เปลี่ยน validity/scoring semantics แม้ S0 ที่มีอยู่ 0 occurrences จะไม่เปลี่ยนค่าตัวเลข ต้อง revalidate S0 analysis ภายใต้กฎใหม่, re-freeze Gate/validity rules และทำ full locked run ใหม่หากภายหลังได้รับอนุมัติ พร้อม disclosure เช่นเดียวกัน

### Repair Class D — เปลี่ยน decoding method

`tokenizer.decode` แบบเดิมเท่ากับ OLD_PIPELINE บน S0 1,520/1,520 แต่ไม่แก้ U+FFFD ส่วน strict/manual/alternative error handling เปลี่ยน behavior สำหรับ problematic sequences จึงเป็น `SCIENTIFIC_CONTRACT_AMENDMENT_REQUIRED` จนกว่าจะมีข้อกำหนดใหม่และหลักฐาน equivalence ที่ครอบคลุม domain ที่เกี่ยวข้อง

## 9. Root cause และคำแนะนำ

Root-cause classification เพียงหนึ่งรายการ:

**`E. MULTIPLE_PLAUSIBLE_CAUSES_REMAIN`**

เหตุผลคือ open evidence รองรับอย่างน้อยสามเส้นทางที่ก่อ U+FFFD ได้ แต่ไม่มีหลักฐาน open ที่ระบุว่าเส้นทางใดเกิดใน Attempt 4 และห้ามเปิด sealed tail เพื่อจำแนก

Next-action classification เพียงหนึ่งรายการ:

**`B. SCIENTIFIC_PROTOCOL_AMENDMENT_REQUIRED`**

ไม่ควร implement amendment ใน task นี้ มนุษย์ต้องเลือกระหว่าง termination rule, token budget และ invalid-decode semantics ใหม่ จากนั้น re-freeze protocol/Gate ก่อนพิจารณา run ใหม่ ไม่อนุญาตให้ reuse Attempt 4 partial outputs หรือสร้าง Attempt 5 โดยอัตโนมัติ

Terminal state:

**`SCIENTIFIC_PROTOCOL_AMENDMENT_PENDING_HUMAN_REVIEW`**

## 10. Reproducible evidence

Machine-readable evidence:

`docs/stage0/evidence/paddle_wayu_unicode_diagnostic/UNICODE_DIAGNOSTIC.json`

- records ต่อ S0 output: 1,520
- ขนาด: 1,562,159 bytes
- SHA-256: `a35881aa75b31ea9355253863970ea8c1e2071cef723c0f41de543793abe5ea8`
- รวม raw generated token IDs, token pieces, tail IDs/pieces, EOS/cap status, processor/tokenizer decode และ synthetic token sequences

Diagnostic code ถูกแยกจาก locked runner ที่:

- `src/labbs2026/stage0/paddle_wayu_unicode_diagnostic.py`
- `scripts/paddle_wayu_unicode_diagnostic.py`
- `tests/test_paddle_wayu_unicode_diagnostic.py`

ไม่มีไฟล์ frozen scientific design, frozen analysis หรือ locked-panel execution contract ถูกแก้ไข
