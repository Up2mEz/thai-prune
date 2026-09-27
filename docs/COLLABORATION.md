# การทำงานร่วมกันสองคน — git, Kaggle, และการแบ่งงาน

**สถานะ: มีผลตั้งแต่ 2026-09-27** (branch ค้างถูก merge แล้วใน PR #1). จุดเริ่มต้นสำหรับคนใหม่คือ `ONBOARDING.md`. เขียนขึ้นเพราะโปรเจกต์นี้
เปลี่ยนจากทำคนเดียวเป็นสองคน ทั้งคู่ใช้ Claude Code และ `AGENTS.md` ที่ checked-in
ไว้ใน repo จะถูกโหลดอัตโนมัติในทุก session ของทั้งสองคน — กฎวิจัย
(pre-registration, Decision Log, ห้ามเปลี่ยนเงื่อนไขเงียบ ๆ) จึงบังคับใช้เหมือนกัน
โดยไม่ต้องตั้งค่าเพิ่ม

ไม่ใช้ plugin หรือ multi-agent extension ใด ๆ สำหรับการทำงานร่วมกันนี้ —
GitHub PR review (ผ่าน `gh` / ccd_pr tools ที่ Claude Code มีอยู่แล้ว) เป็นกลไก
ประสานงานที่เพียงพอ และเป็นมาตรฐานที่ทั้งสองฝั่งใช้ได้แน่นอนไม่ว่าจะรัน
Claude Code แบบไหน

## 1. ก่อนเริ่ม (เสร็จแล้ว)

branch ค้าง 100 commits ถูก merge เข้า `main` ใน PR #1 เมื่อ 2026-09-27 เป็น
one-time bootstrap ไม่ใช่รูปแบบปกติที่จะทำซ้ำ

## 2. Branch model หลังจากนี้

```
main                                    ← integration branch, ทุก PR merge เข้านี่
 ├─ <ชื่อ>/<track-slug>                  ← branch งานของแต่ละคน แต่ละ track
 └─ <ชื่อ>/<track-slug>-fix-xyz          ← แก้บั๊กเล็ก ๆ ระหว่างทาง
```

- แตก branch จาก `main` เสมอ ไม่แตกจาก branch คนอื่น
- ตั้งชื่อ `<ชื่อของคุณ>/<เรื่องที่ทำ>` เช่น `thanakrit/thai-marks-remedy`,
  `<เพื่อน>/wayu-followup`
- เปิด PR เข้า `main` ทุกครั้ง ไม่ push ตรงเข้า `main`
- PR เล็กและถี่ดีกว่า branch ยาว 100 commits แบบที่เพิ่งเกิด — ถ้างานเริ่มยาว
  เกิน 2-3 วัน ให้ PR บางส่วนที่นิ่งแล้วก่อน

## 3. ใครต้อง review อะไร

| ไฟล์ | ใครต้อง approve |
|---|---|
| ไฟล์ในของ track ตัวเอง (ดู §4) | ตัวเอง merge ได้หลัง CI (`light-checks`) ผ่าน **และ** รัน `uv run pytest -q` ครบในเครื่องแล้ว — CI เป็นแค่ชุดตรวจเบา ไม่รัน test ที่ต้องใช้ torch |
| `collab/messages/` ที่ตัวเองเขียน และ `collab/status/<ตัวเอง>.md` | ตัวเอง merge ได้ทันทีหลัง CI ผ่าน — ข้อความต้องถึงอีกฝั่งเร็ว |
| `docs/DECISION_LOG.md`, `docs/RESEARCH_SPEC.md`, `docs/CLAIMS.md`, `docs/EXPERIMENT_PROTOCOL.md`, `docs/ARCHITECTURE.md`, `AGENTS.md` | **อีกคนต้อง approve เสมอ** — เป็นเอกสารกำกับงานวิจัยร่วม แก้เงียบ ๆ ไม่ได้ |
| `src/labbs2026/kaggle.py`, `pyproject.toml`, `uv.lock`, `.github/`, config ระดับ repo | อีกคนต้อง approve — กระทบทั้งสอง track |

เหตุผล: กฎ "ห้ามเปลี่ยนเงื่อนไขการทดลองเงียบ ๆ" ใน `AGENTS.md` เดิมออกแบบมาสำหรับ
คนเดียวคุยกับตัวเอง ตอนนี้มีสองคน PR review บนไฟล์ร่วมคือกลไกที่ทำให้กฎนั้นยังคง
ทำงานจริง

## 4. แบ่งงานตาม track — ขอบเขตไฟล์ที่ไม่ชนกัน

แต่ละ track ได้ namespace ของตัวเอง มองตามที่มีอยู่แล้วในโปรเจกต์
(`region_ocr/`, `thai_marks/` เป็นตัวอย่าง):

| | เจ้าของ | ไฟล์ |
|---|---|---|
| region-OCR (Paddle/wayu, รอบ 1-3) | `Up2mEz` | `src/labbs2026/region_ocr/`, `docs/stage0/REGION_OCR_*`, `configs/region_ocr/`, `scripts/region_ocr_*.py`, `infra/kaggle/region_ocr_worker.py` |
| Thai-marks T1/T2 (Qwen3-VL/Typhoon) | `Up2mEz` | `src/labbs2026/thai_marks/`, `docs/stage0/THAI_MARKS_*`, `configs/thai_marks/`, `scripts/thai_marks_*.py`, `infra/kaggle/thai_marks_worker.py` |
| *track ใหม่ของเพื่อน* | GitHub username ของเพื่อน | `src/labbs2026/<track_ใหม่>/`, `docs/stage0/<TRACK>_*`, `configs/<track_ใหม่>/`, `scripts/<track_ใหม่>_*.py`, `infra/kaggle/<track_ใหม่>_worker.py` |

เมื่อเริ่ม track ใหม่ ให้ตั้งชื่อ package ใหม่เสมอ (ห้ามเขียนทับ `region_ocr`/
`thai_marks`) — วิธีนี้ทำให้สอง track แทบไม่มีทางแก้ไฟล์เดียวกันโดยไม่ตั้งใจ

## 5. `docs/DECISION_LOG.md` — ไฟล์เดียวที่จะชนกันแน่ ๆ

entry ใหม่ทุกอันแทรกไว้บนสุด (ใต้ H1) ถ้าสองคนเขียน entry ใกล้เวลากัน **จะ
conflict ที่บรรทัดเดียวกันแน่นอน** วิธีแก้เมื่อเกิดขึ้น:

1. `git pull --rebase origin main` ก่อนเริ่มเขียน entry ทุกครั้ง
2. commit ที่แก้ `DECISION_LOG.md` แยกเป็น commit ของตัวเอง ไม่ปนกับโค้ด —
   ทำให้ resolve ง่ายเพราะ entry ของสองคนเป็นก้อนอิสระต่อกัน
3. ถ้า conflict เกิดขึ้นตอน merge: **เก็บทั้งสอง entry** เรียงตามวันที่ใหม่ไปเก่า
   แล้วรัน `uv run python scripts/check_research_consistency.py` ยืนยันว่ายัง
   valid

## 6. Kaggle — คนละบัญชี ไม่ต้องจัดคิว

โควตารวม 60 ชม./สัปดาห์ (30 คนละบัญชี) ไม่ชนกัน แต่ script ปัจจุบันมี
kernel id / branch อ้างอิงติดชื่อผู้ใช้ของผมอยู่ ผมแก้ให้ generic แล้ว (ดู
`configs/kaggle_local.example.yaml`) — ก่อนรันครั้งแรก แต่ละคน copy เป็น
`configs/kaggle_local.yaml` (อยู่ใน `.gitignore` แล้ว ไม่ต้อง commit) แล้วใส่
username ของตัวเอง

ขั้นตอนแบบละเอียด ทำตามได้ทีละคำสั่ง (ออกแบบมาให้ AI agent ของอีกฝ่ายรันตามได้
เองด้วย ไม่ต้องพิมพ์ทุกบรรทัดเอง) อยู่ที่ [`docs/KAGGLE_SETUP.md`](KAGGLE_SETUP.md)

## 7. มองเห็นว่าใครทำอะไรอยู่ และคุยกันระหว่าง AI

- `docs/exec-plans/active/INDEX.md` — ตารางว่า track ไหนใครทำ อยู่ branch ไหน
  สถานะอะไร เจ้าของ track อัปเดตแถวของตัวเอง
- `collab/` — ช่องทางระหว่าง AI สองฝั่ง ข้อความละหนึ่งไฟล์ ไม่แก้ไขหลังเขียน
  ตอบกลับด้วยไฟล์ใหม่ที่ระบุ `in_reply_to` จึงไม่มีวัน conflict — กติกาเต็มอยู่ใน
  `collab/README.md` เช็ก inbox ด้วย
  `uv run python scripts/collab_inbox.py --me <github-username>`
- `collab/status/<username>.md` — สถานะล่าสุดของแต่ละคน แก้ได้เฉพาะของตัวเอง
  อัปเดตทุกครั้งที่จบ session

## 8. Checklist ก่อนเริ่มงานแต่ละ session

1. `git checkout main && git pull`
2. `uv run python scripts/collab_inbox.py --me <github-username>` แล้วอ่าน
   `collab/status/` ของอีกฝั่ง และ `docs/exec-plans/active/INDEX.md`
3. แตก branch ใหม่จาก `main` ถ้าเริ่มงานใหม่ หรือ `git pull --rebase` บน branch
   เดิมถ้าทำต่อ
4. ทำงาน → PR → ตามตาราง §3 ว่าใครต้อง review
