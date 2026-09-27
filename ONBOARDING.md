# ONBOARDING — for the second researcher and their AI

> **สำหรับเพื่อน (คน):** ส่งลิงก์ไฟล์นี้ให้ Claude Code ของคุณแล้วบอกว่า
> *"clone repo นี้ อ่าน ONBOARDING.md ทั้งไฟล์ แล้วทำตาม §3 ทีละขั้น"* —
> ทุกอย่างที่ AI ต้องรู้อยู่ในไฟล์นี้ ส่วนที่ต้องทำเองในเบราว์เซอร์มีแค่สร้าง
> Kaggle API token และยืนยันเบอร์โทรเพื่อเปิด GPU (ดู §3.3)
> AI จะคุยกับฝั่งเจ้าของ repo ผ่านโฟลเดอร์ `collab/` (ดู §4) และต้องตกลงเรื่อง
> track งานก่อนเริ่มรันการทดลองใด ๆ (ดู §7)

---

## 0. Instructions to the AI reading this

You are joining a two-person research project as the assistant of the second
researcher. Read this entire file before doing anything. Then:

1. Complete §3 (setup) in order, stopping to report the exact error if a step
   fails.
2. Run the start-of-session protocol in §4 and tell your human what is waiting.
3. **Do not run any model inference, submit any Kaggle job other than the
   §3 smoke, or edit any file outside your own track until your human and the
   repo owner have agreed on a track through `collab/` (§7).**
4. Write to your human in Thai, keeping technical terms in English — this is
   the project's rule (`AGENTS.md`, "Language and Communication").

`AGENTS.md` is loaded automatically for every Claude Code session in this
repo. Its research rules bind you exactly as they bind the owner's session.
This file adds what `AGENTS.md` cannot know: who is who, what is current, what
is history, and how the two sessions communicate.

## 1. The project in one screen

**Repository:** https://github.com/Up2mEz/thai-prune (default branch `main`).

**Current objective** (`docs/RESEARCH_SPEC.md`, section "2026-09-27 Objective
amendment"): reduce Thai vowel and tone-mark transcription errors made by a
page-level OCR vision-language model, **without training**, at comparable or
better inference speed, and explain the mechanism of the errors removed.

- **RQ-A** — are Thai mark errors driven by missing visual evidence, or by the
  language prior overriding the evidence?
- **RQ-B** — does a training-free remedy reduce mark-specific error without
  raising other errors, and at what latency?
- **RQ-C** — does OCR specialization change the balance between evidence and
  prior for Thai marks?

**Models** (pinned by SHA — never load `main` of either repo):

| role | Hugging Face repo | revision |
|---|---|---|
| general-purpose base | `Qwen/Qwen3-VL-2B-Instruct` | `89644892e4d85e24eaac8bacfd4f463576704203` |
| Thai OCR specialist | `typhoon-ai/typhoon-ocr1.5-2b` | `9c8a8fa14905041d793f1e4e922312147956dcc0` |

The Typhoon pin matters for licensing, not just reproducibility: that revision
was published under Apache-2.0 alone; later revisions bind users to the
OpenTyphoon Terms. See `docs/DECISION_LOG.md` entry 2026-09-25.

**Benchmark:** `typhoon-ai/ThaiOCRBench@ca610d1ab330` (CC-BY-SA-4.0; report
numbers freely, never redistribute images or crops). Tasks in scope:
Full-page OCR and Text recognition (primary), Fine-grained text recognition
(secondary). Items are split once, seeded, into **calibration (≈30%, 178
items)** and **locked (≈70%)**. **The locked split is closed**; opening it
needs a human decision recorded in the Decision Log.

**Claim level of everything so far:** `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`.

## 2. People and channels

| who | GitHub | role |
|---|---|---|
| repo owner | `Up2mEz` | owns tracks `region_ocr` and `thai_marks`; approves shared-file changes |
| you (the collaborator) | your own GitHub username | will own the track agreed in §7 |

Channels, in order of use:

1. **`collab/`** — the AI-to-AI channel. Every message is a file (§4).
2. **Pull requests** — code and documents, reviewed per `docs/COLLABORATION.md`.
3. **The two humans directly** — for anything that needs a human decision.
   Your job is to surface those decisions to your human, not to make them.

## 3. Setup (do once)

### 3.1 Clone and install

```bash
git clone https://github.com/Up2mEz/thai-prune.git
cd thai-prune
git checkout main && git pull
uv sync --all-extras
uv run pytest -q
```

Expected: everything passes except tests in
`tests/test_glmm_failure_contract.py` (pre-existing, need Docker, unrelated).
If anything else fails, stop and report it.

```bash
uv run python scripts/check_research_consistency.py
```

Expected: `"valid": true`.

### 3.2 Identity

```bash
gh auth status            # must be logged in as your human's GitHub account
gh api user -q .login     # this is YOUR participant name in collab/
```

Use exactly this login wherever this document says `<you>`.

### 3.3 Kaggle (separate account from the owner's)

Follow `docs/KAGGLE_SETUP.md` from start to finish, including its final smoke
submission. Two steps there require your human in a browser: creating the
Kaggle API token and phone-verifying the account for GPU. Each researcher has
their own 30 h/week GPU quota; you never share or schedule around the owner's.

### 3.4 Announce yourself

1. Create `collab/status/<you>.md` from the shape of `collab/status/Up2mEz.md`.
2. Read `collab/messages/20260927T1500Z_Up2mEz_to_all_welcome-choose-a-track.md`.
3. Do **not** reply yet — replying means proposing a track, which needs §5–§7.

## 4. Every session: start and end

**Start:**

```bash
git checkout main && git pull
uv run python scripts/collab_inbox.py --me <you>
```

Read every listed message, read `collab/status/Up2mEz.md`, read
`docs/exec-plans/active/INDEX.md`, then tell your human, in Thai, what is
waiting and what changed since last time.

**Write a message** (protocol in `collab/README.md`):

```bash
uv run python scripts/collab_inbox.py --new --me <you> --to Up2mEz --slug "short subject"
# prints collab/messages/<timestamp>_<you>_to_Up2mEz_<slug>.md
cp collab/templates/message.md <that path>   # then fill it in
```

Never edit an existing message; reply with a new one whose `in_reply_to` is the
original's filename. A PR that only adds your messages or edits only your own
status file may be merged by you as soon as CI passes.

**End:** update `collab/status/<you>.md` (what you did, what is running, what
you are waiting on), commit, push, and merge it the same way.

## 5. What is current and what is history

The repository carries the full record of an earlier phase — a robustness
evaluation under visual-token compression — because `AGENTS.md` forbids
deleting research records. Most files in `docs/` and `scripts/` belong to that
phase. **Read the CURRENT column. Open HISTORY only when a current document
points you there.**

### CURRENT — read these

| path | what it is |
|---|---|
| `AGENTS.md` | research and engineering rules; auto-loaded |
| `ONBOARDING.md` | this file |
| `docs/COLLABORATION.md` | branch/PR model, who reviews what, file ownership, Decision Log conflicts |
| `docs/KAGGLE_SETUP.md` | Kaggle account and first-run steps |
| `collab/` | AI-to-AI messages and status |
| `docs/RESEARCH_SPEC.md` — **top section only** ("2026-09-27 Objective amendment") | current objective and RQs |
| `docs/DECISION_LOG.md` — **entries dated 2026-09-21 and later** | recent human decisions; newest first |
| `docs/exec-plans/active/INDEX.md` | which tracks exist, who owns them, their state |
| `docs/exec-plans/active/QWEN3VL_TYPHOON_EXPERIMENT_PLAN.md` | the research plan: foundations, literature by remedy family, proposed method, what is deferred and why |
| `docs/stage0/THAI_MARKS_T1_T2_REGISTRATION.md` | the registered T1/T2 protocol — the model for how you register your own tests |
| `docs/stage0/QWEN3VL_TYPHOON_ARCHITECTURE_GAPS.md` | Qwen3-VL-2B layer by layer (DeepStack, M-RoPE, patch geometry) and training-free entry points |
| `docs/stage0/THAI_MARK_FAILURE_MODES.md` | how Thai marks fail (measured on the earlier backbone): mostly deletion, rarely confusion; mark-specific tone error ~26% vs ~8% for vowels |
| `docs/stage0/THAIOCRBENCH_TASK_SELECTION.md` | why these three tasks, and conditions any registration must meet |
| `docs/stage0/BEYOND_PRUNING_LITERATURE_SCAN.md` | search-level literature beyond compression |
| `docs/stage0/TYPHOON_TERMS_RECHECK_2026-09-24.md` | licence evidence behind the Typhoon pin |
| `docs/stage0/REGION_OCR_ROUND3_RESULTS.md` | the one earlier-phase result you should know: model scale preference, and why post-encoder pruning bought no speed |
| `src/labbs2026/thai_marks/` | current instrument: `orthography.py` (mark sites and variants), `normalize.py`, `split.py`, `decompose.py`, `lexicon.py`, `runtime.py` (generation and teacher-forced scoring on Qwen3-VL), `analysis.py`, `remote.py` (Kaggle entry point) |
| `src/labbs2026/kaggle.py` | shared Kaggle helpers incl. `load_local_config`, `kernel_id`, `local_remote_ref` |
| `src/labbs2026/collab.py` | the message protocol |
| `src/labbs2026/consistency.py` | checks governance invariants across the docs; must stay `valid` |
| `configs/thai_marks/` | T1/T2 parameters and the pinned Typhoon prompt |
| `configs/kaggle_local.example.yaml` | template for your git-ignored `configs/kaggle_local.yaml` |
| `scripts/thai_marks_kaggle.py`, `scripts/thai_marks_analyze.py` | stage/submit and fetch/analyse — the template for your own track's scripts |
| `infra/kaggle/thai_marks_worker.py` | Kaggle bootstrap: fetch exact SHA, verify hashes, `uv sync`, run both models in parallel on 2×T4 |
| `scripts/collab_inbox.py`, `scripts/check_research_consistency.py` | inbox; consistency check |

### HISTORY — do not act on

| path | what it was |
|---|---|
| `docs/archive/` | superseded plans, moved out of `active/` on 2026-09-27 |
| `docs/RESEARCH_SPEC.md` below the top section | the robustness-phase specification |
| `docs/EXPERIMENT_PROTOCOL.md`, `docs/ARCHITECTURE.md` (model-specific parts), `docs/LITERATURE.md` | robustness phase; each now opens with a phase note pointing here |
| `docs/CLAIMS.md` | experiment-specific entries are history — **but its claim vocabulary and prohibitions still bind you** |
| `docs/DECISION_LOG.md` before 2026-09-21 | Qwen2.5/3.5 and Paddle/Wayu gates |
| `docs/stage0/` files other than those listed above; `docs/stage0/debug/` | Stage 0 and region-OCR records |
| `docs/*` at top level not listed above (`FALLBACK_PAIR_CLEARANCE`, `NOVELTY_TRIAGE`, `OVERALL_MODEL_BUDGET_FREEZE`, `PADDLE_WAYU_*`, `SPECIALIZATION_PIVOT_REVIEW`, `MEASUREMENT_READINESS_AUDIT`, `CONSISTENCY_REVIEW`) | earlier-phase audits and reports |
| `src/labbs2026/region_ocr/`, `src/labbs2026/stage0/`, `src/labbs2026/step3.py`, `src/labbs2026/adapters/` | earlier-phase code |
| `scripts/` other than those listed above (`paddle_wayu_*`, `stage0_*`, `region_ocr_*`, `build_*`, …) | earlier-phase entry points |
| `configs/region_ocr/`, `configs/stage0/`, `configs/step3/` | earlier-phase configs |

Owner's tracks are `region_ocr` (history, complete) and `thai_marks` (current,
a registered run in flight). **Do not edit either without a `collab/`
agreement.**

## 6. Rules you must follow

### 6.1 Research rules (from `AGENTS.md`, restated because they bite)

- Never silently change experimental conditions; never overwrite results.
- Every run records config, seed, model revision, git commit, environment and
  actual token counts.
- Do not assume tone marks degrade faster, that any remedy works, or that a new
  method is needed. The current plan keeps the gate logic: diagnose, then
  evaluate existing training-free remedies fairly, then a new method only if a
  gap remains.
- Synthetic results are not real-world evidence. One architecture family is not
  "VLMs".
- Keep the distinction between input resolution reduction and post-encoder
  token reduction.

### 6.2 How a test gets from idea to result here

This is the path T1/T2 followed; follow the same one.

1. **Plan** — a file in `docs/exec-plans/active/<TRACK>_PLAN.md`; add a row to
   `docs/exec-plans/active/INDEX.md`.
2. **Registration, before any output exists** —
   `docs/stage0/<TRACK>_<TEST>_REGISTRATION.md`: fixed inputs with SHAs, split,
   prompts, every metric and normalization rule, what each outcome would mean
   **stated in advance**, what is out of scope. Model it on
   `docs/stage0/THAI_MARKS_T1_T2_REGISTRATION.md`.
3. **Human authorization** — a `docs/DECISION_LOG.md` entry recording the
   humans' decision. You may draft it; a human approves it. Because this file
   is shared, the other researcher reviews the PR (`docs/COLLABORATION.md` §3,
   §5).
4. **Code** in `src/labbs2026/<your_track>/`, parameters in
   `configs/<your_track>/`, thin scripts in `scripts/<your_track>_*.py`, unit
   tests for every metric in `tests/`.
5. **CPU checks** of anything that needs no weights (processor, tokenizer,
   templates) — model inference itself always runs on Kaggle, never on a laptop
   CPU.
6. **Smoke** (`--limit 1` or `2`) on Kaggle; inspect it properly: dtype used,
   failures, any consistency guard, output text, time per item.
7. **Full run** on the calibration split; fetch; verify checksums; analyse with
   the registered analysis only.
8. **Results document** `docs/stage0/<TRACK>_<TEST>_RESULTS.md`, including a
   plain statement of what the result does **not** show, and a `result`
   message in `collab/`.

### 6.3 Git and review (full detail in `docs/COLLABORATION.md`)

- Branch from `main` as `<you>/<track-slug>`; open PRs into `main`; never push
  to `main` directly.
- **CI** is the `light-checks` GitHub Actions workflow
  (`.github/workflows/light-checks.yml`): consistency check, `collab/` protocol,
  onboarding paths — no GPU, about a minute. It does **not** run the full suite;
  for any code change, run `uv run pytest -q` locally before merging and say so
  in the PR description.
- Your own track's files: you merge after CI and the local full suite pass. Shared files
  (`docs/DECISION_LOG.md`, `docs/RESEARCH_SPEC.md`, `docs/CLAIMS.md`,
  `docs/EXPERIMENT_PROTOCOL.md`, `docs/ARCHITECTURE.md`, `AGENTS.md`,
  `src/labbs2026/kaggle.py`, `src/labbs2026/consistency.py`, `pyproject.toml`,
  `uv.lock`): the other researcher must approve.
- `collab/` messages and your own status file: self-merge as soon as CI passes.
- Decision Log entries go at the top, under the H1. Pull first; commit the
  entry alone; on conflict keep both entries, newest first, and re-run the
  consistency check.

## 7. Open tracks — choose one with the owner before starting

T1 and T2 (owner's `thai_marks` track, running now) answer RQ-A for both models:
whether the correct mark variant already wins under teacher forcing with the
image (so a decoding-time remedy has headroom) or does not (so the remedy must
act on the input), and whether errors look prior-shaped or perception-shaped.
Tracks are listed by how much they depend on those results.

| track | question | depends on T1/T2? | where to start |
|---|---|---|---|
| **A. Speed without changing output** | Can speculative decoding make page OCR on Qwen3-VL-2B / Typhoon faster on a T4 while the greedy output stays identical? | **No** — exact verification keeps outputs byte-identical, so it composes with any accuracy remedy | plan §2 (HSD row); `BEYOND_PRUNING_LITERATURE_SCAN.md`; measured cost profile in `REGION_OCR_ROUND3_RESULTS.md` §7 and the T1 manifests |
| **B. Existing training-free remedies on Thai** | Do VCD/M3ID, attention amplification (PAI) or OCR-head sink redistribution reduce mark-specific error on ThaiOCRBench? | **Partly** — implementation can start now; evaluation should be compared against T2's oracle upper bound | plan §2 table and its sources |
| **C. Finding versus reading** | On Fine-grained text recognition, does an oracle crop of the given box remove mark errors that the whole-image run makes? | **No** | `THAIOCRBENCH_TASK_SELECTION.md` (Fine-grained section) |
| **D. Input-side remedies** | Scale selection and patch-phase shift on pages | **Yes** — worth running only if T2 says the evidence is missing from the representation | `QWEN3VL_TYPHOON_ARCHITECTURE_GAPS.md` G2–G3 |

Track A is the most independent of the owner's in-flight work. The choice is
the humans'. Your first `collab/` message is a `proposal` replying to the
welcome message: the track, the package name you will create under
`src/labbs2026/`, your first registered test, and a rough GPU-hour estimate.

## 8. Running on Kaggle in this repo

Copy the `thai_marks` pattern rather than inventing a new one:

- `scripts/<track>_kaggle.py` builds a run spec (git SHA, SHA-256 of every
  file the run depends on, locked package versions, parameters from
  `configs/<track>/`) and stages `infra/kaggle/<track>_worker.py` with the spec
  embedded. Kernel ids come from `kaggle.kernel_id(root, "<slug>")`, so they land
  in your account; the remote ref from `kaggle.local_remote_ref(root)`.
- The worker fetches **the exact commit SHA** (not a branch tip — a queued job
  once failed because the branch moved while it waited), verifies file hashes,
  runs `uv sync --frozen`, and then the track's `remote.py`.
- Kaggle's "T4" machine gives two T4 GPUs; the `thai_marks` worker runs one
  model per GPU in parallel. Session wall-clock, not GPU count, is what your
  weekly quota measures.
- Always set up a poller when you submit, and tell your human the run id —
  queues of 40–70 minutes before a job even starts are normal.
- Fetch with `kaggle kernels output`, verify `checksums.sha256`, and refuse to
  analyse a run that has `FAILURE.json`.

## 9. Pitfalls this project has already paid for

| pitfall | what happened | where it is written up |
|---|---|---|
| Crops below the processor's pixel floor | "resolution reduction" on TEMS never discarded information; it only changed magnification | `REGION_OCR_ROUND3_RESULTS.md` §8 |
| Qwen3-VL keeps `rope_deltas` as model state | scoring a no-image prefix after an image item would silently inherit the wrong M-RoPE offset; T2 passes explicit positions and checks cached against uncached scores | `src/labbs2026/thai_marks/runtime.py` docstring |
| DeepStack | Qwen3-VL adds vision layers 5, 11, 17 into LLM layers 0–2; removing tokens from the input alone would not remove them from the model | `QWEN3VL_TYPHOON_ARCHITECTURE_GAPS.md` |
| fp16 on T4 | T4 has no native bf16; runs check logits are finite and fall back to fp32, recording which was used | T1/T2 registration §1 |
| Decode dominates cost | at batch 1 on T4, decode is ~10× its memory-bandwidth floor; pruning only shortens prefill and does not shrink the model; quantization has little to act on at this size | `THAI_MARK_FAILURE_MODES.md` §8 |
| Selection bias | choosing the best setting on the data you then score inflates it; hence calibration/locked | `THAI_MARK_FAILURE_MODES.md` §5 |
| Formatting in targets | pipe separators and Markdown in references measure format, not reading; normalization is registered | T1/T2 registration §4 |
| Contamination | ThaiOCRBench and Typhoon come from the same group; Typhoon's report makes no decontamination statement — read its absolute scores with care | `DECISION_LOG.md` 2026-09-27 |
| Scorer licence | ThaiOCRBench's `eval.py` carries no licence; BMFL is not computed | T1/T2 registration addendum |
| Local CPU inference | tens of times slower than a T4; inference always goes to Kaggle | — |

## 10. Quick reference

```bash
# orient
git checkout main && git pull
uv run python scripts/collab_inbox.py --me <you>
cat collab/status/Up2mEz.md docs/exec-plans/active/INDEX.md

# work
git checkout -b <you>/<track-slug>
uv run pytest -q
uv run python scripts/check_research_consistency.py

# talk
uv run python scripts/collab_inbox.py --new --me <you> --to Up2mEz --slug "subject"

# ship
git push -u origin <you>/<track-slug>
gh pr create --base main --fill
```
