# MODEL_SURVEY W3 — results: T2 (prior vs image) on Pathumma and Qwen3-VL-4B

Registration: `MODEL_SURVEY_W3_REGISTRATION.md` (written before any output).
Claim level: `PRELIMINARY_PILOT_NOT_GATE_EVIDENCE`. Calibration only.

| run | model | status |
|---|---|---|
| W3a `kaggle-model-survey-w3a-4994f0110e0f` | Pathumma `@08bb11dc` | 178/178 items, fp32, no failures, nothing not run, checksums verified; 4,598 s and 4,211 s per shard; consistency guard max 3.6e-5 nats (limit 0.001) |
| W3b `kaggle-model-survey-w3b-afe5126bedd7` | Qwen3-VL-4B `@ebb281ec` | 178/178 items, fp32 over both T4s (`device_map="auto"`), one unit, no failures, nothing not run, checksums verified; 15,386 s (about 8.5 T4-hours); consistency guard max 2.1e-4 nats (limit 0.001) |

Analysis: `docs/stage0/data/MODEL_SURVEY_W3_pathumma_4994f0110e0f.json` and
`docs/stage0/data/MODEL_SURVEY_W3_qwen3vl4b_afe5126bedd7.json`
(`scripts/model_survey_w3_analyze.py`; no reference or output text in
either). Greedy column: M5's archived `BENCHMARK_QUESTION` outputs for
Pathumma (run `8252b99e735d`), M1's for Qwen3-VL-4B (run `3431d9f9dccf`), both
scored with scoring v2's chance-located rule. Budget: W3a about 2.4 and W3b
about 8.5 T4-hours, about 11 of the cap of 24.

**Markup.** W3 generates nothing. Its greedy column is M5's outputs, which were
audited in M5 (§4 of `MODEL_SURVEY_M5_RESULTS.md`): Pathumma writes Typhoon's
format, including `<figure>` blocks, and extraction v2 swallows the text after
a never-closed tag. Sites in swallowed text count as not produced below, so the
"all sites" greedy figure is a lower bound on that account; the
"produced sites" figure is not affected.

## 1. Pathumma at the registered sites

Oracle = legal variant with the highest summed log-probability with the image;
prior = without it; greedy = M5's output at that site. Item bootstrap, 95%
intervals.

| task | mark | sites | oracle | prior | image gain | greedy, all sites | greedy, produced sites (share) | oracle on those |
|---|---|---|---|---|---|---|---|---|
| Full-page (69) | tone | 1,495 | 99.7 [99.4, 99.9] | 98.7 [97.9, 99.4] | +1.0 | 87.9 [80.9, 93.9] | 98.1 [96.6, 99.3] (89%) | 99.8 |
| | upper | 815 | 99.5 [99.0, 99.9] | 98.7 [97.9, 99.4] | +0.8 | 88.8 [82.5, 94.2] | 98.2 [96.9, 99.3] (90%) | 99.5 |
| | lower | 482 | 100.0 | 98.1 [96.6, 99.4] | +1.9 | 87.1 [80.0, 93.6] | 98.1 [96.2, 99.5] (89%) | 100.0 |
| Text rec. (109) | tone | 1,038 | 99.0 [98.3, 99.6] | 97.8 [96.8, 98.6] | +1.2 | 92.8 [87.3, 96.9] | 97.1 [94.4, 98.9] (95%) | 99.1 |
| | upper | 820 | 99.4 [98.7, 99.9] | 96.0 [94.0, 97.6] | +3.4 | 91.7 [86.5, 96.0] | 97.2 [95.2, 98.7] (94%) | 99.6 |
| | lower | 296 | 100.0 | 97.3 [95.0, 99.0] | +2.7 | 90.5 [84.2, 95.7] | 95.7 [92.1, 98.4] (95%) | 100.0 |

Image gain is oracle − prior in points (point estimates; no interval is
registered for it). Share of sites with a positive log-probability gain from the
image: 84–93% per cell.

**Contrastive re-scoring** (`score_image − λ·score_no_image`): Full-page tone
94.8% at λ = 0.5 and 31.6% at λ = 1.0; Text recognition tone 94.7% and 40.7%.
Below the oracle at both λ for every mark and task.

**Scoring convention.** Summed and per-token-mean agree (Full-page tone 99.7%
/ 99.6%). First-divergent-token is lower (86.4%), as in T2, for the reason T2
gives.

**"Produced sites" is defined here, not taken from T2.** The T2 results quote
greedy accuracy "restricted to sites inside text the greedy read produced",
but no code for it is in `thai_marks`. W3's analysis script defines it: a site
is produced when its base consonant (the site itself for a bare consonant) is
aligned to an output character in the v2 alignment (fate correct or
substituted). If T2's figure was computed another way, the Typhoon numbers
below are not strictly the same measure.

## 2. Against the registered patterns (§3)

| pattern | Pathumma |
|---|---|
| oracle ≥ 97% on tone, greedy at produced sites close to it | **Holds.** Tone oracle 99.7% / 99.0%; greedy at produced sites 98.1% / 97.1%, about 1.7–2 points below the oracle on the same sites, with intervals reaching 99.3% / 98.9%. Typhoon in T2: 98.5% vs 99.8% (Full-page). |
| oracle clearly below T2's models (< 95%) | Does not occur. |
| image gain near 0 or negative (as the base) | Does not occur. |
| image gain clearly positive (as Typhoon, +0.9) | **Holds**: +1.0 (Full-page tone), +1.2 (Text tone), larger for upper and lower on Text recognition. |
| contrastive below the oracle at both λ | **Holds**, every mark and task. |

**Reading (registered).** Given the correct text, Pathumma reads marks; its
mark loss is mostly not-reading. Claim (2) extends to Pathumma on
teacher-forced evidence: 10–11% of Full-page sites are in text the greedy read
did not produce, and that is where most of the gap between greedy on all sites
(about 88%) and the oracle (about 99.7%) lies. The image adds evidence at mark
sites, as for Typhoon, and image-contrastive re-scoring would cost marks (R1's
§6.4 reading extends).

Caveats:

- Pathumma is a fine-tune of the same base as Typhoon and writes Typhoon's
  format (M5); this is a second Thai OCR fine-tune, not an independent
  family. W3b (Qwen3-VL-4B) is the different-size general model.
- The greedy column comes from `BENCHMARK_QUESTION`, while T2 scores with
  `TYPHOON_CARD` context. Pathumma's primary prompt in M5 is its card prompt;
  W3 registered BQ for comparability with T2's base column.
- Teacher-forced site accuracy is not reading accuracy: the oracle is given the
  correct preceding text, which a looping or skipping greedy read does not
  have.

## 3. Qwen3-VL-4B (W3b)

**Markup.** The greedy column is M1's outputs, audited in M1. Qwen3-VL-4B
writes no `<figure>`, so no unclosed-tag bound applies.

| task | mark | sites | oracle | prior | image gain | greedy, all sites | greedy, produced sites (share) | oracle on those |
|---|---|---|---|---|---|---|---|---|
| Full-page (69) | tone | 1,495 | 98.7 [97.8, 99.4] | 99.1 [98.5, 99.6] | −0.5 | 68.1 [61.1, 74.8] | 80.1 [75.1, 84.5] (84%) | 98.8 |
| | upper | 815 | 98.5 [97.0, 99.5] | 98.8 [97.9, 99.5] | −0.2 | 68.2 [60.9, 75.2] | 80.1 [74.5, 85.0] (85%) | 98.6 |
| | lower | 482 | 98.3 [96.6, 99.6] | 99.2 [98.1, 100.0] | −0.8 | 64.5 [55.8, 73.0] | 76.0 [68.8, 82.5] (84%) | 98.3 |
| Text rec. (109) | tone | 1,038 | 98.0 [96.9, 98.9] | 97.9 [96.8, 98.7] | +0.1 | 80.7 [73.9, 86.3] | 88.4 [84.6, 91.6] (91%) | 98.1 |
| | upper | 820 | 98.0 [97.1, 98.9] | 96.5 [95.0, 97.7] | +1.6 | 75.0 [68.9, 80.6] | 83.9 [79.7, 87.6] (88%) | 98.3 |
| | lower | 296 | 99.0 [97.7, 100.0] | 98.6 [97.2, 99.7] | +0.3 | 80.1 [72.1, 87.3] | 87.5 [82.0, 92.0] (92%) | 99.3 |

**Contrastive re-scoring:** Full-page tone 88.7% at λ = 0.5 and 20.1% at
λ = 1.0; Text recognition tone 85.1% and 16.4%. Below the oracle at both λ for
every mark and task. **Convention:** summed 98.7%, per-token-mean 99.0%,
first-divergent 84.2% (Full-page tone).

**Diagnostic, not registered: tone sites whose base consonant the greedy read
got right.** "Produced" also counts sites whose base was substituted, so it
mixes base errors into the mark figure. On sites with a correct base (fate
"correct"):

| model | Full-page greedy / oracle | Text rec. greedy / oracle |
|---|---|---|
| Pathumma | 99.4% / 99.8% (1,311 sites) | 98.5% / 99.1% (969) |
| Qwen3-VL-4B | 91.3% / 99.1% (1,021) | 95.6% / 98.7% (826) |

### Against the registered patterns (§3)

| pattern | Qwen3-VL-4B |
|---|---|
| oracle ≥ 97% on tone, greedy at produced sites close to it | Oracle part holds (98.7% / 98.0%). Greedy part does **not**: 80.1% / 88.4%, 10–19 points below the oracle on the same sites, intervals far apart. |
| oracle ≥ 97% but greedy at produced sites far below it | **Holds.** |
| oracle clearly below T2's models (< 95%) | Does not occur. |
| image gain near 0 or negative (as the base, −0.8) | **Holds**: −0.5 (Full-page tone), +0.1 (Text tone); the prior is at or above the oracle on Full-page for every mark. |
| image gain clearly positive (as Typhoon) | Does not occur. |
| contrastive below the oracle at both λ | **Holds**, every mark and task, and by more than for Pathumma. |

**Reading (registered).** Given the correct text, Qwen3-VL-4B knows the marks
as well as the Thai fine-tunes do (oracle about 98–99%). But its misreads
happen in generation, not in its mark knowledge, so claim (2) holds only
partly for it:

- About 15% of Full-page sites are in text it did not produce. That is
  not-reading, as for the others.
- On text it did produce, it still gets about one tone mark in five wrong
  (80.1%). With a correct base consonant, it gets about one in eleven wrong
  (91.3%) where the oracle gets 99.1%.

The prior carries the mark choice in context, with no image gain, as for the
base Qwen3-VL-2B in T2. Image-contrastive re-scoring would cost marks (R1's
§6.4 reading extends).

What this means for the paper's claim (2), as an inference:

- The "not reading" account fits the Thai OCR fine-tunes (Typhoon, Pathumma)
  on teacher-forced evidence.
- For the general models (base, Qwen3-VL-4B), a misreading component in
  generation is real.
- W1's attribution also has general models losing more to not reading than
  to misreading on a correct base: Qwen3-VL-4B 31.4% vs 4.3%, a ratio of
  7.3 (`W1_PROFILE_8252b99e735d.json`). The two measures agree on direction
  but not on size. T2/W3 compares at the same sites given the
  correct context, while W1 counts what the free output lost.

Caveats:

- The greedy column is `BENCHMARK_QUESTION` from M1. Qwen3-VL-4B often frames
  or translates its answer (M1 results §5); framing text adds no reference marks, so
  it does not lower the produced-site figure, but a translated or paraphrased
  span would be counted as produced if its alignment lands on a base.
- One model, calibration only, as everything here.
