# Fine-tune Qwen3.5-4B on Multimodal-Mind2Web

Trains a web navigation agent on screenshot + task → next action prediction using [Multimodal-Mind2Web](https://huggingface.co/datasets/osunlp/Multimodal-Mind2Web).

**Model:** [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) — natively multimodal (early fusion), 2.74 GB Q4_K_M GGUF.

## Models


| Variant      | Link                                                                                                        |
| ------------ | ----------------------------------------------------------------------------------------------------------- |
| LoRA adapter | [schnetzlerjoe/qwen35-4b-mind2web-lora](https://huggingface.co/schnetzlerjoe/qwen35-4b-mind2web-lora)       |
| Merged bf16  | [schnetzlerjoe/qwen35-4b-mind2web-merged](https://huggingface.co/schnetzlerjoe/qwen35-4b-mind2web-merged)   |
| GGUF Q4_K_M  | [schnetzlerjoe/qwen35-4b-mind2web-gguf-q4](https://huggingface.co/schnetzlerjoe/qwen35-4b-mind2web-gguf-q4) |
| GGUF Q8_0    | [schnetzlerjoe/qwen35-4b-mind2web-gguf-q8](https://huggingface.co/schnetzlerjoe/qwen35-4b-mind2web-gguf-q8) |


