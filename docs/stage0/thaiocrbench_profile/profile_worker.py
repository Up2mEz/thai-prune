"""Profile ThaiOCRBench (typhoon-ai/ThaiOCRBench@ca610d1ab330) task by task.

NOT AN EXPERIMENT. No model weights are loaded. The question is which tasks can
carry the project's research question at all: a transcription ground truth that
supports a per-component (tone mark / vowel / consonant) error decomposition,
enough Thai marks, no formatting convention mixed into the target, and images in
a regime where the Qwen3-VL processor does not simply upsample them.

Token counts follow Typhoon OCR 1.5's own card: resize so the long side is
1,800 px whenever either side exceeds 300 px, then the processor's smart_resize
(factor 32, floor 65,536 px).
"""

import collections
import json
import math
import re

from datasets import load_dataset

REVISION = "ca610d1ab330"
FLOOR, CEILING, FACTOR = 65536, 16777216, 32
TONE = set("่้๊๋")
UPPER = set("ัิีึื็")
LOWER = set("ฺุู")
THAI = re.compile(r"[฀-๿]")
MARKUP = re.compile(r"(<[a-zA-Z/][^>]*>|\|\s*[-:]+\s*\||^#+\s|\*\*|^\s*[-*]\s|\{|\})", re.M)
OUT = "/kaggle/working/thaiocrbench_profile.json"


def smart_resize(height, width):
    h_bar = max(FACTOR, round(height / FACTOR) * FACTOR)
    w_bar = max(FACTOR, round(width / FACTOR) * FACTOR)
    if h_bar * w_bar > CEILING:
        beta = math.sqrt((height * width) / CEILING)
        h_bar = math.floor(height / beta / FACTOR) * FACTOR
        w_bar = math.floor(width / beta / FACTOR) * FACTOR
    elif h_bar * w_bar < FLOOR:
        beta = math.sqrt(FLOOR / (height * width))
        h_bar = math.ceil(height * beta / FACTOR) * FACTOR
        w_bar = math.ceil(width * beta / FACTOR) * FACTOR
    return h_bar, w_bar


def typhoon_policy(height, width):
    if width > 300 or height > 300:
        scale = 1800 / float(max(width, height))
        height, width = int(height * scale), int(width * scale)
    return smart_resize(height, width)


def quantile(values, fraction):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))] if ordered else None


dataset = load_dataset("typhoon-ai/ThaiOCRBench", split="test", revision=REVISION)
groups = collections.defaultdict(list)
for row in dataset:
    width, height = row["image"].size
    groups[row["Task"]].append({
        "h": height, "w": width, "q": row["question"] or "", "a": row["answer"] or "",
        "category": row["category"],
    })

summary = {"status": "BENCHMARK_PROFILE_NOT_EVIDENCE", "revision": REVISION,
           "total": len(dataset), "tasks": {}}
for task, rows in sorted(groups.items()):
    native = [r["h"] * r["w"] for r in rows]
    policy = [typhoon_policy(r["h"], r["w"]) for r in rows]
    tokens = [(h // 16) * (w // 16) // 4 for h, w in policy]
    native_scale = [(ph * pw) / (r["h"] * r["w"]) for (ph, pw), r in zip(policy, rows)]
    answers = [r["a"] for r in rows]
    tone = sum(sum(ch in TONE for ch in a) for a in answers)
    upper = sum(sum(ch in UPPER for ch in a) for a in answers)
    lower = sum(sum(ch in LOWER for ch in a) for a in answers)
    questions = collections.Counter(r["q"].strip()[:80] for r in rows)
    summary["tasks"][task] = {
        "n": len(rows),
        "native_area_p10_p50_p90": [quantile(native, f) for f in (0.1, 0.5, 0.9)],
        "native_below_qwen_floor": sum(1 for a in native if a < FLOOR),
        "typhoon_policy_visual_tokens_p10_p50_p90": [quantile(tokens, f) for f in (0.1, 0.5, 0.9)],
        "typhoon_policy_area_scale_p10_p50_p90": [round(quantile(native_scale, f), 3) for f in (0.1, 0.5, 0.9)],
        "answer_chars_p10_p50_p90": [quantile([len(a) for a in answers], f) for f in (0.1, 0.5, 0.9)],
        "answers_with_thai": sum(1 for a in answers if THAI.search(a)),
        "answers_with_markup": sum(1 for a in answers if MARKUP.search(a)),
        "answers_multiline": sum(1 for a in answers if "\n" in a.strip()),
        "tone_marks_in_answers": tone,
        "upper_vowels_in_answers": upper,
        "lower_vowels_in_answers": lower,
        "distinct_question_openings": len(questions),
        "top_questions": questions.most_common(3),
        "question_mentions_coordinates": sum(1 for r in rows if re.search(r"\[\s*\d+\s*,\s*\d+", r["q"])),
        "categories": collections.Counter(r["category"] for r in rows).most_common(6),
        "examples": [{"q": r["q"][:200], "a": r["a"][:240], "hw": [r["h"], r["w"]]} for r in rows[:2]],
    }

with open(OUT, "w", encoding="utf-8") as handle:
    json.dump(summary, handle, ensure_ascii=False, indent=1)
print(json.dumps({t: {k: v for k, v in s.items() if k not in ("examples", "top_questions")}
                  for t, s in summary["tasks"].items()}, ensure_ascii=False, indent=1))
