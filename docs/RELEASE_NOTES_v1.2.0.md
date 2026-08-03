# v1.2.0 — Equal-N per-recipe ablation

## 這是研究證據版本，不是 Dataset／Model artifact 版本

**Hugging Face Dataset 與 LoRA adapter 完全沒有改變。**

- Dataset 仍是 3,754-row F1–F7 release-only corpus
- Model 仍是同一份 Gemma filtered seed-42 LoRA
- Frozen corpus、thresholds、prompt、500-step training contract、strict parser
  與 MASSIVE `zh-TW` Test set 全部未動

v1.2.0 新增的是 M19：在相同資料量下，檢查四種 synthetic recipes 的組成差異。

---

## M19 實驗設計

每個組別都使用：

- 1,176 筆 frozen 20-shot real examples
- 2,246 筆 synthetic examples（equal-N）
- Gemma 4 E4B、seed 42、500 training steps
- 同一份不含 label catalog 的 SFT prompt
- 同一個 strict evaluator 與 2,974-row untouched Test set

`abl_all_eqn` 保留四種 recipes 作為 equal-N control；另外四組各排除一種 recipe。
Exact match 相對 control 的 absolute delta 是否達到 **2.5 percentage points**，
是在執行前凍結的 detectability threshold。

## 結果

| Group | 排除 recipe | intent acc | slot F1 | exact match | exact Δ vs control（pp） | 達門檻 |
| --- | --- | ---: | ---: | ---: | ---: | :---: |
| `abl_all_eqn` | — | 75.99% | 63.61% | 49.50% | +0.00 | no |
| `abl_no_paraphrase` | `paraphrase` | 74.14% | 64.09% | 50.00% | +0.50 | no |
| `abl_no_slot_substitution` | `slot_substitution` | 77.14% | 65.60% | 51.51% | +2.02 | no |
| `abl_no_noise_codeswitch` | `noise_codeswitch` | 73.47% | 63.84% | 48.76% | -0.74 | no |
| `abl_no_hard_negative` | `hard_negative` | 76.19% | 64.69% | 50.81% | +1.31 | no |

五組皆完成 500 steps 與 2,974/2,974 strict evaluation；沒有任何組別達到門檻。
Machine-readable 判讀是：

`no_difference_reaches_preregistered_detectability_threshold`

這是重要的 negative result，但不是「四種 recipe 都沒用」：M19 只有
**seed 42（n=1）**，而且比較的是 equal-N composition。因此 v1.2.0 明確保留
`causal_claim_allowed=false`，不做 recipe-level causal claim，也不在看到結果後
追加 seeds、換 detectability metric 或降低門檻。

---

## Artifact 與資料稽核

- 五組 training data 都是 3,422 rows／3,422 unique ids
- deterministic rebuild 的五組 SHA-256 都穩定重現
- 五份 prediction JSONL 都是 2,974 rows／2,974 unique expected ids，
  `generation_index` 完整覆蓋 0–2,973
- 五份 `run_report.json` 均為 `completed`、`global_step=500`
- 五個 `checkpoint-500` 與 final adapter directory 都存在
- Aggregate report：`reports/m19_ablation.json`
- 預先登記契約：`docs/M19_ABLATION_PROTOCOL.md`

## 資源帳本

| 項目 | v1.1.0 | v1.2.0 |
| --- | ---: | ---: |
| Primary core | 14.440 h | **14.440 h（刻意未變）** |
| Auxiliary | 19.035 h | **27.972 h** |
| 可追溯 local total | 33.475 h | **42.412 h** |
| 450 W TDP 上限包絡 | 15.064 kWh | **19.085 kWh** |
| API 花費 | $0 | **$0** |

M19 共計 8.937 h。`abl_no_paraphrase` 曾在 final validation 中斷，成功續跑的
final run report 只記錄後段 session；v1.2.0 以原始 log timestamps 與 SHA-256
建立 `reports/m19_runtime_audit.json`，把被捨棄 attempt 的 2.084 h **只補一次**，
避免把中斷成本悄悄漏掉。這項稽核只修正資源統計，不影響任何模型或結果。

---

## Repository 變更

- 新增五組 machine-readable／Markdown evaluation reports
- 新增 `scripts.build_m19_report` aggregate 與 README reproducibility checks
- `verify_readme` 現在會逐列從 M19 JSON 重建表格，並強制揭露 single-seed、
  2.5-point threshold 與 no-causal-claim 三項限制
- Resource ledger 支援 hash-anchored interrupted-attempt audit，並有 regression test
- 新增 D-021，記錄預先登記判讀、拒絕事後追加分析，以及 negative result

## 完整資料

- M19 aggregate：[`reports/m19_ablation.md`](https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.0/reports/m19_ablation.md)
- M19 runtime audit：[`reports/m19_runtime_audit.json`](https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.0/reports/m19_runtime_audit.json)
- M19 protocol：[`docs/M19_ABLATION_PROTOCOL.md`](https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.0/docs/M19_ABLATION_PROTOCOL.md)
- Resource ledger：[`reports/m12_resource_ledger.json`](https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.0/reports/m12_resource_ledger.json)
- Decision record：[`docs/DECISIONS.md`](https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.0/docs/DECISIONS.md)
