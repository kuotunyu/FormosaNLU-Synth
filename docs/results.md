# 完整結果

本頁收錄從 [README](../README.md) 移出的完整數字表。差距補回率與跨 student family 對照表仍在 README；本頁與 README 的主要數字由 `python -m scripts.verify_readme` 對照 `reports/` 內的原始檔。

## Seed-42 primary 實驗矩陣

| Group | Training data | intent acc | intent macro-F1 | slot F1 | exact match | JSON-valid |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `zero_shot` | 未訓練 | 10.66% | 23.12% | 0.00% | 8.10% | 17.38% |
| `real_only` | 20-shot real | 73.54% | 75.20% | 62.14% | 49.06% | 98.02% |
| `real_std_aug` | + classical augmentation | 74.31% | 75.59% | 62.58% | 46.81% | 96.23% |
| `real_syn_unfiltered_full` | + 全部 unfiltered synthetic | 75.99% | 76.42% | 65.01% | 51.21% | 97.75% |
| `real_syn_unfiltered_eqn` | + equal-N unfiltered synthetic | 76.03% | 75.59% | 64.37% | 51.01% | 97.95% |
| `real_syn_filtered` | + filtered synthetic | 76.19% | 76.09% | 66.54% | 52.12% | 97.98% |
| `full_real` | 完整 MASSIVE train | 84.53% | 81.65% | 71.58% | 60.66% | 99.73% |

以 `real_only` 定義 0%、`full_real` 定義 100% 的差距補回率表在 [README](../README.md#結果)；原始報告為 [`reports/m10_main_results.md`](../reports/m10_main_results.md)。

## 三種子不確定性分析

`real_only` 與 `real_syn_filtered` 使用完全相同之 frozen data/config，分別在 seeds 42、43、44 訓練與評估；每個 run 都使用完整 2,974-row Test。

| Metric | real-only mean ± SD | filtered mean ± SD | paired Δ mean ± SD | paired Δ 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Intent accuracy | 73.34% ± 0.32% | 77.47% ± 1.14% | +4.14% ± 1.39% | [+0.68%, +7.59%] |
| Intent macro-F1 | 74.55% ± 1.27% | 76.56% ± 0.41% | +2.01% ± 1.48% | [-1.67%, +5.70%] |
| Slot micro-F1 | 62.95% ± 1.18% | 65.86% ± 0.76% | +2.92% ± 1.92% | [-1.86%, +7.69%] |
| Exact match | 48.67% ± 0.65% | 52.52% ± 0.88% | +3.86% ± 0.73% | [+2.03%, +5.68%] |
| JSON-valid rate | 96.54% ± 2.01% | 98.11% ± 0.14% | +1.57% ± 2.02% | [-3.44%, +6.58%] |

95% intervals 使用 Student's t (df=2)；完整逐 seed 報告與原始統計在 [`reports/m9_replicate_summary.md`](../reports/m9_replicate_summary.md)。

## 成對統計檢定 (Paired Statistical Evidence)

另外使用 frozen row-level predictions 執行 5,000 次 hierarchical paired bootstrap。

| Metric | 平均提升 | Hierarchical bootstrap 95% CI |
| --- | ---: | ---: |
| Intent accuracy | +4.14 個百分點 | **[+2.60, +5.59]** |
| Intent macro-F1 | +2.01 個百分點 | **[+0.35, +3.69]** |
| Slot micro-F1 | +2.92 個百分點 | **[+0.87, +4.68]** |
| Exact match | +3.86 個百分點 | **[+2.75, +4.92]** |

Intent accuracy 與 exact match 另在每個 seed 執行 two-sided exact McNemar test；六項比較經 Holm correction 後全部 `p ≤ 0.00017`。完整方法、input SHA-256 與結果見 [`reports/m14_paired_statistics.md`](../reports/m14_paired_statistics.md)。跨 student family 的對照表在 [README](../README.md#結果)，原始報告為 [`reports/m15_cross_model_replication.md`](../reports/m15_cross_model_replication.md)。

## Equal-N per-recipe ablation (M19，negative result)

M19 將四種 synthetic recipes 進行 leave-one-out，並將每組 synthetic rows 固定為 2,246 筆；連同相同的 1,176 筆 real examples，每組訓練資料均為 3,422 筆。

這是 **seed 42（n=1）** 的 composition-level 描述性比較；預先登記的 detectability metric 是 exact match，門檻為 **2.5 percentage points**。

| Group | 排除的 recipe | intent acc | intent macro-F1 | slot F1 | exact match | exact Δ vs control (pp) | JSON-valid | 達門檻 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| `abl_all_eqn` | `— (equal-N control)` | 75.99% | 75.51% | 63.61% | 49.50% | +0.00 | 97.34% | no |
| `abl_no_paraphrase` | `paraphrase` | 74.14% | 74.72% | 64.09% | 50.00% | +0.50 | 96.54% | no |
| `abl_no_slot_substitution` | `slot_substitution` | 77.14% | 77.11% | 65.60% | 51.51% | +2.02 | 96.40% | no |
| `abl_no_noise_codeswitch` | `noise_codeswitch` | 73.47% | 73.03% | 63.84% | 48.76% | -0.74 | 96.47% | no |
| `abl_no_hard_negative` | `hard_negative` | 76.19% | 76.23% | 64.69% | 50.81% | +1.31 | 97.24% | no |

所有 exact-match 差異都低於預先登記門檻，因此結果不支持辨識單一 recipe 的獨立貢獻，並且**不做單一 recipe 的 causal claim**。

詳細說明見 [`reports/m19_ablation.json`](../reports/m19_ablation.json) 與 [`docs/M19_ABLATION_PROTOCOL.md`](M19_ABLATION_PROTOCOL.md)。

## Filter pipeline 效益評估

Seed 42 下，3,760-row filtered corpus 相較 unfiltered-full / equal-N unfiltered，intent accuracy 分別高 0.20 / 0.17 pp、slot F1 高 1.53 / 2.17 pp、exact match 高 0.91 / 1.11 pp。

![Filtered 與 unfiltered controls](../assets/m12_filter_comparison.png)

F1-F6 最終保留 3,760 / 11,264 rows (33.38%)。最大損失為 4,596 筆 near-duplicates，揭露了 pilot 未發現之 corpus-scale mode collapse。

F7 independent audit 完成 376/376；random stratum 的觀察漏檢率為 **6.0%**（50 筆樣本，區間仍寬），並只影響公開 Dataset，不回溯改寫 frozen training corpus。

![F1–F6 filter funnel](../assets/m12_filter_funnel.png)

### 各 intent 的變化

![各 intent 的 accuracy 變化](../assets/m12_intent_movement.png)

單一 seed 的極端 intent 變化容易受 20-shot 基線變異影響；完整三種子解讀見 [`reports/m9_replicate_summary.md`](../reports/m9_replicate_summary.md)。

## 魯棒性測試 (Robustness Probe)

包含 8,922 筆測試資料：2,974 筆 Test 各以規則改寫成 `colloquial`、`lexical`、`asr_noise` 三種 probe。

### 三種子 Paired Delta 評測

**Gemma 4 E4B** (seeds 42–44)

| Metric | Mean Δ (百分點) | Sample SD |
| --- | ---: | ---: |
| `intent_accuracy` | +3.63 | 1.72 |
| `intent_macro_f1` | +2.11 | 2.19 |
| `slot_micro_f1` | +2.75 | 2.76 |
| `exact_match` | +3.58 | 2.05 |
| `json_valid_rate` | +1.49 | 2.35 |

**Phi-4-mini** (seeds 42–44)

| Metric | Mean Δ (百分點) | Sample SD |
| --- | ---: | ---: |
| `intent_accuracy` | +6.22 | 3.46 |
| `intent_macro_f1` | +4.69 | 2.73 |
| `slot_micro_f1` | +3.73 | 1.23 |
| `exact_match` | +6.98 | 3.29 |
| `json_valid_rate` | +1.83 | 0.93 |

詳細數據見 [`reports/m16_robustness_summary_gemma.md`](../reports/m16_robustness_summary_gemma.md) 與 [`reports/m16_robustness_summary_phi4mini.md`](../reports/m16_robustness_summary_phi4mini.md)。

### Seed-42 的逐 probe 拆解 (Gemma)

| Group | Probe | Intent acc | Slot F1 | Exact match | JSON valid |
| --- | --- | ---: | ---: | ---: | ---: |
| `real_only` | `asr_noise` | 68.49% | 58.62% | 42.54% | 98.52% |
| `real_only` | `colloquial` | 73.50% | 61.20% | 47.98% | 98.18% |
| `real_only` | `lexical` | 72.83% | 61.97% | 48.49% | 97.98% |
| `real_syn_filtered` | `asr_noise` | 70.24% | 61.25% | 44.08% | 97.88% |
| `real_syn_filtered` | `colloquial` | 74.88% | 65.69% | 51.18% | 97.68% |
| `real_syn_filtered` | `lexical` | 74.68% | 65.48% | 51.11% | 97.98% |

這些是 seed 42 的拆解，不取代上方 seeds 42–44 的 paired summary；三種擾動是 deterministic probes，不等同真實 ASR 或自然 code-switching 分布。

## 實務推論範例

以下為同一台 RTX 4090、同一份 decoding contract 之真實輸出：

**輸入：`播放周杰倫`**

```jsonc
// base model — 意圖正確，但鍵名誤用 "slot"
{"intent": "play_music", "slots": [{"slot": "artist_name", "value": "周杰倫"}]}

// filtered adapter
{"intent":"play_music","slots":[{"type":"artist_name","value":"周杰倫"}]}
```

**輸入：`台北明天會不會下雨`**

```json
{"intent":"weather_query","slots":[{"type":"place_name","value":"台北"},{"type":"date","value":"明天"}]}
```

同一組五句中，**base model 0/5**，adapter 達成 **5/5 valid JSON**。在這一句，base 的鍵名誤用 `name`，並把「明天」標為 `time`；adapter 輸出合法 schema，並把「明天」標為 `date`。兩邊 prompt 刻意不同：base 使用含合法 labels 的 zero-shot catalog prompt，adapter 使用 frozen SFT prompt。

完整五句、latency 與 adapter tree SHA-256 見 [`reports/m11_demo_evidence.json`](../reports/m11_demo_evidence.json)。

## 算力成本

Primary GPU path 於單張 RTX 4090 上耗時 **14.440 h**；包含所有輔助實驗，本機總耗時為 **42.412 h**，API spend 為 **$0**。

| Phase | GPU wall-clock | 證據來源 |
| --- | ---: | --- |
| Synthetic generation | **4.073 h** | `reports/generation_report.json` |
| Primary training (seed 42) | **6.540 h** | `runs/m9_batch_report.json` |
| Trained evaluation (seed 42) | **2.777 h** | `results/m9_eval_batch_report.json` |
| Zero-shot evaluation | **1.050 h** | M8 report |
| **Measured primary core total** | **14.440 h** | 不含 extra seeds、F7 與 robustness |
| Auxiliary tasks total | **27.972 h** | F7 + M11 + extra seeds + robustness + M15 + M16 + M19 |
| **Local total** | **42.412 h** | 所有本機 GPU 階段 |
| **API spend** | **$0** | 所有模型均在本機執行 |

以 RTX 4090 的 450 W TDP 計算，primary core 14.440 h 對應 6.498 kWh、local total 42.412 h 對應 **19.085 kWh** 的保守 GPU-only 上限；這不是 wall-socket measurement。

資源帳本位於 [`reports/m12_resource_ledger.json`](../reports/m12_resource_ledger.json)。

## 公開產物與發布驗證

| 產物類型 | 位置 | 驗證狀態 |
| --- | --- | --- |
| Source、pipeline、reports | [GitHub](https://github.com/kuotunyu/FormosaNLU-Synth) | Public；Contributors 僅 `kuotunyu` |
| Versioned source archive | [Zenodo v1.2.2](https://zenodo.org/records/21879133) | Public；immutable version DOI；creator 僅 `kuotunyu` |
| 3,754-row F1–F7 corpus | [Hugging Face Dataset](https://huggingface.co/datasets/steven0226/formosa-nlu-synth-v1) | Public；Dataset Viewer 與匿名載入通過 |
| Filtered seed-42 LoRA | [Hugging Face Model](https://huggingface.co/steven0226/gemma-4-e4b-formosanlu-lora) | Public；PEFT config、686 tensors 與 SHA-256 通過 |
| Phi filtered seed-42 LoRA | [Hugging Face Model](https://huggingface.co/steven0226/phi-4-mini-formosanlu-lora) | Public；fixed revision、256 tensors 與 SHA-256 通過 |
| English technical report | [Zenodo Technical note](https://zenodo.org/records/21879155) · [DOI](https://doi.org/10.5281/zenodo.21879155) · [source](../paper/formosanlu_synth.tex) | CC BY 4.0；匿名下載驗證通過；尚未 peer review |

匿名發布稽核見 [`reports/m13_publication.json`](../reports/m13_publication.json)。
