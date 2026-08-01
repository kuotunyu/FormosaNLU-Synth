# M19 — Per-recipe ablation：預先登記協定

> **本文件在跑任何 ablation 訓練之前寫成並 commit。** 目的是先把設計、可偵測性
> 與判讀規則定死，避免看到結果之後才決定怎麼詮釋。

## 問題

四個 recipe（`paraphrase`、`slot_substitution`、`noise_codeswitch`、
`hard_negative`）各自貢獻了多少？D-004 當初為 Colab 成本砍掉這個消融，README
一直誠實記載「未執行」。現在 GPU 有餘裕，補做。

## 設計：等量 leave-one-out

**核心問題是混淆。** 直接移除一個 recipe 會同時改變「組成」與「筆數」，那麼任何
差異都無法歸因——這正是 D-004 為 filtered vs unfiltered 引入等量對照要解決的
同一個問題。

因此**五組全部使用完全相同的合成筆數**：

| 組別 | 合成資料組成 |
|---|---|
| `abl_all_eqn` | 全部四個 recipe，下採樣至 N |
| `abl_no_paraphrase` | 移除 `paraphrase`，其餘下採樣至 N |
| `abl_no_slot_substitution` | 移除 `slot_substitution`，其餘下採樣至 N |
| `abl_no_noise_codeswitch` | 移除 `noise_codeswitch`，其餘下採樣至 N |
| `abl_no_hard_negative` | 移除 `hard_negative`，其餘下採樣至 N |

**N = 2,246**，即最小的 leave-one-out 語料大小（3,760 − 1,514 個 paraphrase）。
所有組都額外包含同一份 1,176 筆真實資料。

`abl_all_eqn` 是對照組：它與各 LOO 組**筆數相同**，差別只在組成。因此組間差異
可歸因於 recipe 組成，不是資料量。

**不與既有的 `real_syn_filtered`（3,760 筆）直接比較**——那組筆數不同，比較會
重新引入混淆。

## Recipe 來源

凍結語料沒有 recipe 欄位，但 `build_generation_plans` 是確定性的，
`generation_index` 可對回計畫。對映已驗證：3,760/3,760 筆的 intent 與計畫相符。

過濾後的實際分佈（與生成目標差距很大，本身是個發現）：

| Recipe | 生成目標 | 過濾後 | 筆數 |
|---|---:|---:|---:|
| `paraphrase` | 35% | 40.3% | 1,514 |
| `noise_codeswitch` | 20% | 32.7% | 1,228 |
| `slot_substitution` | 30% | 19.8% | 743 |
| `hard_negative` | 15% | **7.3%** | **275** |

## 可偵測性：先講清楚什麼測得出來、什麼測不出來

三種子的 `real_syn_filtered` 在 exact match 上的 sample SD 是 **0.88 個百分點**。
兩組各跑一個 seed 的差值，其 run-to-run 不確定性約
`sqrt(0.88² + 0.88²) ≈ 1.24` 點（1 SD）。

**因此本次（n=1）的判讀規則，事前定死：**

| 差異幅度 | 判讀 |
|---|---|
| < 2.5 點（約 2 SD） | **不可區分**。不得宣稱該 recipe 有或沒有貢獻 |
| ≥ 2.5 點 | 值得報告，但仍需標明 n=1 |

**`hard_negative` 幾乎確定測不出來。** 它只佔 7.3%，在 N=2,246 下約 164 筆。
移除它與否的差異落在雜訊裡的機率很高。**這個 null 結果不得被讀成「hard
negative 沒有用」**——它只代表這個設計的解析度不足以偵測 7% 的組成變化。

同理，`slot_substitution`（19.8%，約 444 筆）也在邊緣。

真正有機會分辨的是 `paraphrase`（40.3%）與 `noise_codeswitch`（32.7%）。

## 不做的事

- **不補 seed。** 五組 × 三種子 = 15 runs ≈ 23 GPU 小時，成本不划算。代價是
  解析度受限，已在上面寫明。
- **不改任何凍結契約。** 相同 prompt、500 steps、相同超參、相同評測。只有合成
  資料的組成不同。
- **不重算 M9／M14／M15 的任何結果。** 這是新增的分析，不回頭動主表。

## 成功與失敗都要報告

若五組差異全部落在 2.5 點以內，結論就是「**在這個 n=1、等量的設計下，無法分辨
recipe 之間的貢獻**」。那是一個誠實的結果，不是失敗，也不得被改寫成「所有
recipe 同等重要」。
