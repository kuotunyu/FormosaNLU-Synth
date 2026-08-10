---
license: mit
base_model: microsoft/Phi-4-mini-instruct
base_model_relation: adapter
library_name: peft
pipeline_tag: text-generation
language:
  - zh
tags:
  - lora
  - qlora
  - nlu
  - intent-classification
  - slot-filling
  - synthetic-data
datasets:
  - steven0226/formosa-nlu-synth-v1
---

# Phi-4-mini FormosaNLU LoRA

這是 `microsoft/Phi-4-mini-instruct` 的 4-bit QLoRA adapter，用於正體中文口語 NLU：
joint intent classification、slot filling，以及嚴格 JSON output。此 repository **不含 base model
weights**。

它是 FormosaNLU-Synth 的第二個 student model family。相同 frozen paired contract 下，
`real + filtered synthetic` 相較於 `real only`，在 Gemma 與 Phi 兩個 families 都得到正向、
且 hierarchical 95% CI 下界大於零的 intent accuracy 與 exact match 改善。

## Artifact identity

| 欄位 | 值 |
|---|---|
| Base model | `microsoft/Phi-4-mini-instruct` |
| Frozen revision | `cfbefacb99257ffa30c83adab238a50856ac3083` |
| Training arm | `real_syn_filtered` |
| Seed | `42` |
| Adapter type | LoRA，`r=16`、`alpha=32`、dropout `0.05` |
| Target modules | `qkv_proj`、`o_proj`、`gate_up_proj`、`down_proj` |
| Steps | `500` |
| Public Dataset | [`steven0226/formosa-nlu-synth-v1`](https://huggingface.co/datasets/steven0226/formosa-nlu-synth-v1) |
| Source | [`kuotunyu/FormosaNLU-Synth`](https://github.com/kuotunyu/FormosaNLU-Synth) |
| DOI | [`10.5281/zenodo.21767492`](https://doi.org/10.5281/zenodo.21767492) (all versions) |

`release_manifest.json` 記錄 adapter SHA-256、byte size、tensor count、base revision、training
arm 與 source commit。上傳 bundle 僅允許 inference 所需檔案；optimizer state、checkpoints、
`training_args.bin` 與本機路徑不會發布。

## Results

所有數字都來自未進入訓練的 frozen MASSIVE zh-TW Test（2,974 rows）。下表只描述本 repo
發布的 seed-42 adapter；跨 seeds 與跨 model-family 結論請以 source reports 為準。

| Metric | Real only | Real + filtered synthetic | Delta (pp) |
|---|---:|---:|---:|
| Intent accuracy | 72.49% | **74.28%** | **+1.78** |
| Intent macro-F1 | 73.14% | **74.02%** | **+0.88** |
| Slot micro-F1 | 59.55% | **60.08%** | **+0.53** |
| Exact match | 45.49% | **46.70%** | **+1.21** |
| JSON-valid rate | 96.67% | **97.88%** | **+1.21** |

三個 seeds（42/43/44）的 filtered-minus-real-only mean delta：intent accuracy `+5.09 pp`
（hierarchical 95% CI `[+1.83, +9.02]`），exact match `+4.71 pp`
（`[+1.36, +7.59]`）。完整 paired statistics 與 cross-family criterion：

- [Phi paired statistics](https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.2/reports/m15_phi4mini_paired_statistics.md)
- [Cross-family replication](https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.2/reports/m15_cross_model_replication.md)
- [Technical report](https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.2/paper/formosanlu_synth.pdf)

## Load the adapter

```python
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

base_id = "microsoft/Phi-4-mini-instruct"
base_revision = "cfbefacb99257ffa30c83adab238a50856ac3083"
adapter_id = "steven0226/phi-4-mini-formosanlu-lora"

tokenizer = AutoTokenizer.from_pretrained(base_id, revision=base_revision)
model = AutoModelForCausalLM.from_pretrained(
    base_id,
    revision=base_revision,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    ),
)
model = PeftModel.from_pretrained(model, adapter_id)
model.eval()
```

請沿用 source repository 的 `formosanlu_nlu.v1` prompt 與 label catalog。這個 adapter 不是一般聊天
模型；若改變 prompt、label set、parser 或 decoding contract，以上指標不再可直接比較。

## Limitations

- 證據限於 MASSIVE zh-TW、一個 frozen split 與三個 training seeds。
- 公開 artifact 是 seed 42；三-seed 結論來自獨立 runs，不代表任一單一 adapter 的保證。
- Exact-match 對 JSON、intent label、slot type 與 span formatting 都很敏感。
- Synthetic data 可能延續 teacher 或原始資料的偏誤；部署前仍需 domain-specific safety audit。
- `microsoft/Phi-4-mini-instruct` 的 license、notices 與使用限制仍適用。

## Citation

```bibtex
@software{kuotunyu_formosanlu_synth_2026,
  author  = {kuotunyu},
  title   = {FormosaNLU Synthetic Data Distillation for Traditional Chinese NLU},
  year    = {2026},
  version = {1.2.2},
  doi     = {10.5281/zenodo.21767492},
  url     = {https://github.com/kuotunyu/FormosaNLU-Synth}
}
```
