# Project

Research codebase for studying orthographic micro-feature
robustness under visual-token compression in VLMs.

# Source of truth

Research questions and hypotheses:
docs/RESEARCH_SPEC.md

Exact experimental protocol:
docs/EXPERIMENT_PROTOCOL.md

VLM architecture assumptions:
docs/ARCHITECTURE.md

Research decisions:
docs/DECISION_LOG.md

Permitted scientific claims:
docs/CLAIMS.md

Current implementation task:
docs/exec-plans/active/

# Non-negotiable research rules

- Do not assume Thai tone marks degrade faster.
- Do not assume token pruning is the cause.
- Do not assume a new method is required.
- Do not advance to a later research stage unless its gate
  is explicitly marked PASS in DECISION_LOG.md.
- Never silently change experimental conditions.
- Never overwrite previous experiment results.
- Every run must record config, seed, model revision,
  git commit, environment, and actual token counts.
- Synthetic results must not be described as real-world evidence.
- Qwen-only results must not be generalized to all VLMs.
- Distinguish input-resolution reduction from post-encoder
  token reduction.

# Engineering rules

- Research logic belongs in src/, not notebooks.
- scripts/ are thin CLI entrypoints only.
- Every metric must have unit tests.
- Dataset generation must be deterministic given a seed.
- Experiment parameters come from configs/, not hard-coded values.
- Run tests before declaring a task complete.

# Verification

uv run pytest
uv run python scripts/preflight.py

# Language and Communication

- Use **Thai as the primary language** for all user-facing communication in this project.
    
- Keep established technical terms in English when using the English term is clearer or more precise, for example:  
    `Vision Encoder`, `Visual Token`, `Token Pruning`, `Token Merging`,  
    `Resolution Reduction`, `Forced-choice`, `Baseline`, `Ablation`,  
    `Confound`, `Effect Size`, `Confidence Interval`, `Inference`,  
    `Embedding`, `Attention`, `Patch`, `FLOPs`, and `Latency`.
    
- When a technical term may be unfamiliar or ambiguous, explain its meaning in Thai the first time it is used. Do not translate technical terminology into unnatural Thai merely for consistency.
    
- Prefer sentences such as:  
    "ขั้นนี้ใช้ Token Pruning เพื่อลดจำนวน visual tokens หลัง Vision Encoder"  
    rather than translating every technical term into Thai.
    
- Code identifiers, class names, function names, filenames, CLI commands,  
    configuration keys, model names, metric names, API names, and library names  
    must remain in their original language and spelling.
    

## Explanations and Reasoning Summaries

- Write plans, progress updates, implementation explanations, experiment interpretations,  
    debugging explanations, research critiques, and decision rationales in Thai.
    
- When presenting a reasoning summary, explain:
    
    1. กำลังพยายามตอบคำถามอะไร
        
    2. หลักฐานหรือข้อมูลที่ตรวจพบคืออะไร
        
    3. ตีความได้อย่างไร
        
    4. ยังมีสิ่งใดที่ไม่แน่ใจหรือยังพิสูจน์ไม่ได้
        
    5. สิ่งนี้มีผลต่อขั้นตอนถัดไปอย่างไร
        
- Keep technical terminology in English where precision matters.
    
- Do not hide uncertainty behind confident wording.
    
- Explicitly distinguish:
    
    - สิ่งที่ตรวจพบจาก code / experiment / source
        
    - สิ่งที่เป็น inference
        
    - สิ่งที่เป็น hypothesis
        
    - สิ่งที่ยังไม่ทราบ
        
- Do not present an inference as an established fact.
    

## Planning

- Plans produced in Plan mode must be written primarily in Thai.
    
- Technical filenames, modules, classes, functions, commands, schemas,  
    configuration keys, and research terminology may remain in English.
    
- Explain **why** each major implementation step is necessary, not only what files will be changed.
    
- For research work, connect each planned task to the relevant  
    Research Question, Stage, or Decision Gate when applicable.
    

## Final Responses

Unless the user explicitly requests another language:

- Summarize completed work in Thai.
    
- Describe changed files in Thai while preserving exact file paths.
    
- Report test and experiment results in Thai.
    
- Explain failures and unresolved issues directly.
    
- Keep commands and code snippets unchanged.
    
- Avoid excessive English prose when the same idea can be explained clearly in Thai.