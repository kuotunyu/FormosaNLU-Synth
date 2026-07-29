---
language:
- zh
license: cc-by-4.0
pretty_name: FormosaNLU Synth
task_categories:
- text-classification
- token-classification
size_categories:
- 1K<n<10K
tags:
- zh-TW
- traditional-chinese
- taiwan
- synthetic-data
- natural-language-understanding
- intent-classification
- slot-filling
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train.jsonl
---

# FormosaNLU Synth

FormosaNLU Synth 是一份以正體中文（台灣，`zh-TW`）為主的口語 NLU
synthetic training dataset，涵蓋 60 種 intent 與 55 種 slot type。資料由
本機 open-weight teacher 產生，經 deterministic F1–F6 filters 與不同家族
independent judge（F7）稽核後，發布 3,754 筆 training rows。

本資料集對應的完整程式碼、決策紀錄與實驗報告：
[kuotunyu/FormosaNLU-Synth](https://github.com/kuotunyu/FormosaNLU-Synth)。

## 內容

```text
data/train.jsonl       3,754 rows
schema.json            JSON Schema
release_manifest.json  來源 artifact、SHA-256、筆數與版本
```

每筆資料包含：

| 欄位 | 說明 |
|---|---|
| `id` | 穩定 synthetic sample ID |
| `utt` | 正體中文（台灣）utterance |
| `intent` | MASSIVE intent label |
| `slots` | `{type, value}` slot spans |
| `style` | `massive_like` 或 `tw_colloquial` |
| `recipe` | synthetic recipe |
| `teacher_model` | 生成模型 |
| `prompt_version` | prompt recipe version |
| `seed_sample_id` | 來源 MASSIVE seed identifier |
| `generation_params` | frozen generation parameters |
| `filter_scores` | F5/F6 contamination 與 similarity evidence |

載入方式：

```python
from datasets import load_dataset

dataset = load_dataset("steven0226/formosa-nlu-synth-v1")
train = dataset["train"]
print(train.num_rows)  # 3754
```

## 資料來源與生成

- Upstream seed data：Amazon Science MASSIVE `zh-TW`
- Seed sampling：約每 intent 20-shot，共 1,176 筆
- Teacher：`qwen3.6:27b`，本機 Ollama、open-weight
- 原始生成：11,264 筆
- F1–F6 accepted：3,760 筆
- F7 release：3,754 筆

過濾包含 schema、label／slot span、script／language、duplicate、seed-copy、
Test contamination、embedding outlier 與 independent judge audit。Frozen
thresholds、hashes、漏檢率與完整 funnel 見 GitHub repository 的 README、
`reports/generation_report.json` 與 `reports/m6_f7_release.json`。

## 下游證據

在完全未參與生成或訓練的 2,974-row MASSIVE `zh-TW` Test 上，Gemma 4 E4B
QLoRA 三個 paired seeds（42–44）顯示：

- Intent accuracy：filtered 相較 real-only 平均 **+4.14 ± 1.39** 個百分點
- Exact match：平均 **+3.86 ± 0.73** 個百分點
- Seed-42 robustness：filtered adapter 在 ASR-noise、colloquial、lexical
  三種 probes 的 intent accuracy、slot F1、exact match 均高於 real-only

`n=3` intervals 是 descriptive uncertainty，不代表廣泛統計顯著性。

使用 frozen row-level predictions 執行 5,000 次 hierarchical paired
bootstrap 後，intent accuracy 的平均提升為 +4.14 個百分點（95% CI
[+2.60, +5.59]），exact match 為 +3.86（[+2.75, +4.92]）。每個 seed
的 intent accuracy 與 exact match exact McNemar tests 經 Holm correction
後均 `p ≤ 0.00017`。這些結果只適用目前的 frozen Test 與 Gemma 4 contract，
不代表跨模型泛化。

## 適合用途

- 正體中文 intent classification／slot filling 研究
- Synthetic-data filtering、distillation 與 low-resource augmentation
- NLU pipeline、schema-constrained output 與 robustness 實驗

## 限制與不適合用途

- `zh-TW` seed 源自翻譯型 MASSIVE，無法代表所有自然台灣口語。
- Synthetic records 可能保留 teacher bias 或未偵測品質問題。
- F7 random stratum 觀察漏檢率為 6.0%，但樣本只有 50 筆，interval 很寬。
- Robustness 是 deterministic probes，不是真實 ASR log。
- 不應把 intent／slot predictions 當作醫療、法律、金融或安全決策。
- 未發布 MASSIVE Test／validation；使用者應自行依 MASSIVE 授權取得評估資料。

## 授權與 Attribution

本發布資料使用 **CC BY 4.0**。上游 seed data 為 Amazon Science MASSIVE
`zh-TW`，亦採 CC BY 4.0。使用或再發布時請：

1. 標示 MASSIVE 與 FormosaNLU Synth；
2. 連結 CC BY 4.0；
3. 說明資料經 synthetic generation 與 filtering 修改。

MASSIVE：

> Jack FitzGerald et al. MASSIVE: A 1M-Example Multilingual Natural Language
> Understanding Dataset with 51 Typologically-Diverse Languages. ACL 2023.

FormosaNLU Synth：

```text
kuotunyu. FormosaNLU Synthetic Data Distillation for Traditional Chinese
(Taiwan) NLU, version 1.0.0. 2026.
https://github.com/kuotunyu/FormosaNLU-Synth
```

## 可重現性

`release_manifest.json` 提供發布檔 SHA-256、原始 release artifact SHA-256、
Git source commit 與確切筆數。完整生成、過濾與評估程式位於 GitHub。
