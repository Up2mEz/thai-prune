---
pipeline_tag: image-text-to-text
library_name: transformers
language:
- th
base_model:
- Qwen/Qwen3-VL-2B-Instruct
license: apache-2.0
---
# Pathumma Vision 3.0.0-Re

**Pathumma Vision 3.0.0-Re** is a vision-language model developed by **NECTEC** for Thai OCR .

The model is based on **Qwen3-VL-2B-Instruct** and further trained on a large-scale OCR dataset with **377K training samples**. The training focuses on improving OCR capabilities, particularly for Thai and challenging real-world document and scene-text images.

This model also uses **Quantization-Aware Training (QAT)** to improve the model's suitability for efficient deployment while maintaining strong OCR performance.

## Model Highlights

* 🧠 Based on **Qwen3-VL-2B-Instruct**
* 🇹🇭 Optimized for **Thai OCR**
* 📚 Trained on **377K OCR samples**
* ⚡ Quantization-Aware Training (QAT)
* 🖼️ Vision-language image-to-text understanding
* 📄 Designed for OCR and document/image understanding
* 🚀 Intended for efficient deployment and inference

## Benchmark

We evaluate our models on **ThaiOCRBench**, a benchmark designed to assess OCR and document understanding capabilities across Thai and challenging real-world visual content.
### ThaiOCRBench Results

| Model                                 | Document Parsing | Fine-grained Text Recognition | Full-page OCR | Handwritten Content Extraction | Text Recognition | Document Classification | Diagram VQA | Cognition VQA | Infographics |    Overall |
| ------------------------------------- | ---------------: | ----------------------------: | ------------: | -----------------------------: | ---------------: | ----------------------: | ----------: | ------------: | -----------: | ---------: |
| **Typhoon-OCR1.5-2B**                 |           0.2355 |                        0.1274 |    **0.7724** |                         0.2808 |           0.5922 |                  0.4093 |      0.4063 |        0.5690 |       0.5839 |     0.4419 |
| **Pathumma-LLM-Vision-3.0.0-re**      |           0.4117 |                    **0.1478** |        0.7361 |                     **0.3675** |       **0.6742** |              **0.4326** |      0.4363 |        0.6623 |       0.5951 |     0.4960 |
| **Pathumma-LLM-Vision-3.0.0-preview** |       **0.4872** |                        0.1458 |    **0.7831** |                         0.3286 |           0.6443 |                  0.2558 |  **0.5784** |    **0.6763** |   **0.6451** | **0.5050** |

## Training

The model was fine-tuned on **377K OCR training samples**.

### Training Configuration

| Parameter             | Value                             |
| --------------------- | --------------------------------- |
| Base model            | Qwen3-VL-2B-Instruct              |
| Training data         | 377K OCR samples                  |
| Training method       | Quantization-Aware Training (QAT) |
| Learning rate         | `9e-6`                            |
| Epochs                | `2`                               |
| Gradient accumulation | `4`                               |
| Hardware              | 8 × NVIDIA A100                   |
| Model size            | 2B parameters                     |

### Training Hardware

Training was performed using:

**8 × NVIDIA A100 GPUs**

with gradient accumulation of 4.

## Intended Use

Pathumma Vision 3.0.0-Re is intended for:

* Thai OCR
* Scene text recognition
* Document text extraction
* Thai document understanding

## Quickstart

### Installation

```bash
pip install -U transformers
pip install torch torchvision
```

### Using 🤗 Transformers

```python
import torch
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor

model_id = "nectec/Pathumma-llm-vision-3.0.0-re"

model = Qwen3VLForConditionalGeneration.from_pretrained(
    model_id,
    dtype=torch.bfloat16,
    device_map="auto",
)

processor = AutoProcessor.from_pretrained(model_id)

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "image",
                "image": "path/to/your/image.jpg",
            },
            {
                "type": "text",
                "text": "อ่านข้อความในภาพนี้",
            },
        ],
    }
]

inputs = processor.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    return_dict=True,
    return_tensors="pt",
)

inputs = inputs.to(model.device)

generated_ids = model.generate(
    **inputs,
    max_new_tokens=512,
)

generated_ids_trimmed = [
    out_ids[len(in_ids):]
    for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
]

output_text = processor.batch_decode(
    generated_ids_trimmed,
    skip_special_tokens=True,
    clean_up_tokenization_spaces=False,
)

print(output_text[0])
```

## Contributors

This model was developed by:

* **Kun Kerdthaisong**
* **Thanaporn Pintobtang**
* **Theerawat Phromchai**
* **Khemjira Prachumkhong**
* **Teepakorn Lilek**
* **Theerasit Issaranon**
* **Sarawoot Kongyoung**

## Acknowledgements

We thank the **NECTEC** team and contributors involved in the development of Pathumma and the underlying Thai-language and vision-language resources.

This model is built upon the Qwen3-VL architecture and benefits from the work of the Qwen team.

## Citation

If you find Pathumma-llm-vision-3.0.0-re useful in your research, please cite:

```bibtex
@misc{PathummaVision3,
  author = {
    Kerdthaisong, Kun and
    Pintobtang, Thanaporn and
    Phromchai, Theerawat and
    Prachumkhong, Khemjira and
    Lilek, Teepakorn and
    Issaranon, Theerasit and
    Kongyoung, Sarawoot
  },
  title = {Pathumma Vision 3.0.0-Re},
  year = {2026},
  url = {https://huggingface.co/nectec/Pathumma-llm-vision-3.0.0-re}
}
```

Please also cite the original Qwen3-VL work:

```bibtex
@misc{qwen3technicalreport,
  title={Qwen3 Technical Report},
  author={Qwen Team},
  year={2025},
  eprint={2505.09388},
  archivePrefix={arXiv},
  primaryClass={cs.CL},
  url={https://arxiv.org/abs/2505.09388}
}
```