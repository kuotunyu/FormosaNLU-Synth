---
base_model: google/gemma-4-E4B-it
library_name: peft
pipeline_tag: text-generation
license: apache-2.0
language:
- zh
datasets:
- steven0226/formosa-nlu-synth-v1
tags:
- peft
- lora
- qlora
- gemma4
- zh-TW
- traditional-chinese
- natural-language-understanding
- intent-classification
- slot-filling
---

# Gemma 4 E4B FormosaNLU LoRA

這是 `google/gemma-4-E4B-it` 的 text-tower QLoRA adapter，針對正體中文
（台灣，`zh-TW`）口語 NLU 進行 supervised fine-tuning。輸出 contract 是：

```json
{"intent": "intent_label", "slots": [{"type": "slot_type", "value": "原句片段"}]}
```

本 repo 只包含 **LoRA adapter 與 tokenizer artifacts**，不包含完整 Gemma 4
base weights。完整程式碼、frozen config、資料與實驗報告：
[kuotunyu/FormosaNLU-Synth](https://github.com/kuotunyu/FormosaNLU-Synth)。

## Model details

| 項目 | 內容 |
|---|---|
| Base model | `google/gemma-4-E4B-it` |
| Adapter | PEFT LoRA，rank 16，alpha 32，dropout 0.05 |
| Training group | 1,176 real 20-shot + 3,760 F1–F6 filtered synthetic |
| Seed | 42 |
| Steps | 500 |
| Effective batch size | 16 |
| Quantization | NF4 double-quant QLoRA，BF16 compute |
| Training GPU | NVIDIA RTX 4090 24 GB |
| License | Apache-2.0 |

發布的是 primary filtered seed-42 adapter；seeds 43/44 僅用於 uncertainty
評估，不另行發布。

## Evaluation

Untouched MASSIVE `zh-TW` Test，2,974 rows：

| Metric | real-only seed 42 | 此 filtered adapter |
|---|---:|---:|
| Intent accuracy | 73.54% | **76.19%** |
| Intent macro-F1 | 75.20% | **76.09%** |
| Slot micro-F1 | 62.14% | **66.54%** |
| Exact match | 49.06% | **52.12%** |
| JSON-valid rate | 98.02% | 97.98% |

Paired seeds 42–44 中，filtered 相對 real-only 的 intent accuracy 平均提升
+4.14 ± 1.39 個百分點，exact match 平均提升 +3.86 ± 0.73 個百分點。
5,000 次 hierarchical paired bootstrap 的 95% CI 分別為
[+2.60, +5.59] 與 [+2.75, +4.92] 個百分點；每個 seed 的 exact McNemar
tests 經 Holm correction 後均 `p ≤ 0.00017`。**上表所有數字都是這個
Gemma 4 adapter 本身的成效。**

訓練這個 adapter 所用的 corpus，其效益已在第二個 student family
（`microsoft/Phi-4-mini-instruct`）以相同的 paired contract 複製成功：
intent accuracy 與 exact match 在兩個 family 都是正向平均提升，且
hierarchical 95% CI 下界都大於零，判準在看到結果前即凍結。那是**資料**
的證據，不是這個 adapter 的成效；此處列出是為了說明 corpus 的效益不限於
單一 student model。細節見
[FormosaNLU-Synth](https://github.com/kuotunyu/FormosaNLU-Synth) 的
cross-model 報告。

### v1.2.1 evidence release 與 M19 equal-N ablation

[GitHub v1.2.1 evidence release](https://github.com/kuotunyu/FormosaNLU-Synth/releases/tag/v1.2.1)
只更新 publication metadata、technical report 與 card 說明。**Dataset rows and
Model tensors did not change.** 此 Gemma adapter 仍是相同的 155,609,536-byte
artifact，SHA-256 仍為
`f70f423814dcd47943c92c0beb8b08a4e7f65e60a44355d3dcd95bed9f0bd60a`。

M19 以 Gemma seed 42 做 equal-N composition comparison；control 與四個
leave-one-recipe-out 組都使用 1,176 real + 2,246 synthetic rows：

| 排除 recipe | Exact-match Δ vs control（percentage points） |
| --- | ---: |
| `paraphrase` | +0.50 |
| `slot_substitution` | +2.02 |
| `noise_codeswitch` | -0.74 |
| `hard_negative` | +1.31 |

預先登記的 detectability threshold 是 **2.5 percentage points**；沒有任何組別
達到。這是 **single seed (n=1); descriptive comparison only**。This does not support a recipe-level causal claim.
這是 Dataset composition 的限制性證據，
不是這個公開 adapter 的額外 headline evaluation，也沒有可下載的 Phi adapter。

Seed-42 的 8,922-row deterministic robustness probe：

| Group | Intent accuracy | Slot F1 | Exact match |
|---|---:|---:|---:|
| real-only | 71.61% | 60.59% | 46.33% |
| 此 filtered adapter | **73.27%** | **64.13%** | **48.79%** |

跨 seeds 42–44 的 paired delta（filtered − real-only，百分點）：intent
accuracy **+3.63 ± 1.72**、exact match **+3.58 ± 2.05**、slot F1 +2.75 ± 2.76、
intent macro-F1 +2.11 ± 2.19、JSON-valid +1.49 ± 2.35。五項平均皆為正，但只有
前兩項的 mean 明顯大於 SD。**只看 seed 42 會誤導**——該 seed 的 intent
macro-F1（−0.40）與 JSON-valid（−0.38）其實是負的。

## 載入方式

Gemma 4 E4B 是 multimodal checkpoint；本專案只載入 text tower，使用與訓練
相同的 key mapping：

```python
import torch
from peft import PeftModel
from transformers import AutoTokenizer, BitsAndBytesConfig
from transformers import Gemma4Config, Gemma4ForCausalLM

base_id = "google/gemma-4-E4B-it"
adapter_id = "steven0226/gemma-4-e4b-formosanlu-lora"

tokenizer = AutoTokenizer.from_pretrained(adapter_id)
tokenizer.padding_side = "left"

quantization = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)
multimodal_config = Gemma4Config.from_pretrained(base_id)
base = Gemma4ForCausalLM.from_pretrained(
    base_id,
    config=multimodal_config.text_config,
    key_mapping={r"^model\.language_model\.": "model."},
    quantization_config=quantization,
    dtype=torch.bfloat16,
    device_map={"": 0},
)
model = PeftModel.from_pretrained(base, adapter_id, is_trainable=False)
model.eval()
```

輸入 prompt／chat template 與完整 inference 範例請參考 GitHub 的
`src/evaluation/run_adapter.py` 與 `src/nlu_prompt.py`。

## Intended use

- 正體中文（台灣）intent classification 與 slot filling 研究
- Synthetic-data augmentation 的下游比較
- PEFT／QLoRA、structured output 與 NLU Demo

## Limitations

- 只針對 MASSIVE taxonomy：60 intents、55 slot types。
- Test 來源具有翻譯語料特性，不等同所有自然台灣口語。
- 可能輸出無效 JSON、錯誤 intent 或不在原句中的 slot value。
- 沒有 constrained decoding；JSON-valid rate 是實測指標。
- Robustness 已涵蓋 seeds 42–44，但**這個 Gemma adapter 所屬的 family** 五項
  指標中只有 intent accuracy 與 exact match 的效果明顯大於 seed 間的變異；其
  餘三項在 `n=3` 下無法與零區分。擾動是 deterministic probes，不是自然 ASR
  logs。
- 不適用醫療、法律、金融或安全關鍵決策。

## Training data

- Real seed：MASSIVE `zh-TW` 20-shot sampling，共 1,176 rows
- Synthetic：`steven0226/formosa-nlu-synth-v1`
- Validation／Test：只使用 untouched real MASSIVE，未回流生成或訓練

## Environmental information

所有本機 model workloads 使用單張 RTX 4090。專案可追溯 local GPU total
為 42.412 小時；以 450 W TDP 計算的 GPU-only 保守上限為 19.085 kWh，
不是 wall-socket measurement。API 花費為 $0。

## License

Gemma 4 與此 adapter 使用 Apache License 2.0。
