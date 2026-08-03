# M19 Equal-N Per-recipe Ablation

Status: **complete**.

所有組別固定 2,246 筆 synthetic rows、相同 prompt／train config／500 steps，並在同一份 2,974-row Test 上評估。結果僅為 seed 42（n=1）的描述性比較。

預先登記的可偵測門檻為 exact match 絕對差異 2.5 percentage points；低於門檻代表本設計無法分辨，不等於效果為零。單一 seed 結果不支持 recipe-level causal claim。

| Group | Excluded recipe | Intent acc | Macro-F1 | Slot F1 | Exact | Δ Exact vs control (pp) | JSON-valid | Detectable |
|---|---|---:|---:|---:|---:|---:|---:|:---:|
| `abl_all_eqn` | `— (equal-N control)` | 75.99% | 75.51% | 63.61% | 49.50% | +0.00 | 97.34% | no |
| `abl_no_paraphrase` | `paraphrase` | 74.14% | 74.72% | 64.09% | 50.00% | +0.50 | 96.54% | no |
| `abl_no_slot_substitution` | `slot_substitution` | 77.14% | 77.11% | 65.60% | 51.51% | +2.02 | 96.40% | no |
| `abl_no_noise_codeswitch` | `noise_codeswitch` | 73.47% | 73.03% | 63.84% | 48.76% | -0.74 | 96.47% | no |
| `abl_no_hard_negative` | `hard_negative` | 76.19% | 76.23% | 64.69% | 50.81% | +1.31 | 97.24% | no |

Machine-readable source: `reports/m19_ablation.json`.
