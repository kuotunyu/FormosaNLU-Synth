# M5 Filtering Status

> 狀態：F1–F7 程式、BGE-M3 production calibration、人工 pair review、
> 四個 frozen thresholds 與 500 筆 pilot 完整漏斗均已完成。

## 已完成

- F1：Pydantic schema，能把純結構錯誤與 unknown-label 錯誤分到正確關卡。
- F2：凍結 60/55 labels，並重算 sample labels 是否等於 code-authored
  generation plan，避免 teacher 悄悄換 slot。
- F3：共用 `src/data/normalize.py`，要求所有 slot 有不重疊的 normalized span。
- F4：繁簡殘留、大陸用語、非預期 script 與 Latin ratio；noise recipe 有明確但
  有限的 code-switch 放寬。
- F5：L2 normalize、seed-too-close、synthetic duplicate、seed outlier 的
  vectorized cosine 決策；只跟先前 accepted synthetic 比，決定可重現。
- F6：Val/Test nearest-neighbor exclusion 與 auditable log schema
  （sample id、similarity、matched eval id、split）；只排除，不挑選。
- F7：固定 50 筆、hard-negative 優先的跨家族 judge 抽樣，實跑 50/50
  structured verdict。
- 每筆只寫第一個 reject reason；F1–F4 真實漏斗
  `437 + 63 = 500`。

全專案測試目前 53 passed；每一關都有 pass/fail 案例。Ruff 與
`git diff --check` 通過。

## BGE-M3 production calibration

D-010 選定 `BAAI/bge-m3`。使用者返回後核可下載，本機只取 dense inference
必要檔案，共 2,293,322,213 bytes；主權重 2,271,145,830 bytes，SHA-256：
`b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38`。
backend 全程 `local_files_only=True`。

437 筆 F1–F4 pilot、1,176 train seeds 與 5,007 Validation/Test rows 在 RTX
4090 上完成 embedding。第二次可重現量測總耗時約 18 秒，peak allocated
VRAM 約 2.31 GiB。三組分布、完整 quantiles 與權重 hash 在
`reports/m5_similarity_calibration.json`；圖在
`assets/m5_similarity_distributions.png`。

在看到 F1–F6 yield **之前**，先人工檢查圖與最高／最低 25 組 pair，凍結：

| Threshold | Frozen value | Pair-review rationale |
| --- | ---: | --- |
| synthetic duplicate | 0.999 | 最高 25/25 都是逐字重複 |
| seed too close | 0.995 | 涵蓋逐字與只差標點／語尾的 seed 複製 |
| seed outlier minimum | 0.650 | 只排除明顯過短的「定期」；0.659 起已有合理 domain 句 |
| Val/Test contamination | 0.990 | 排除逐字與近乎只差功能詞的 eval wording |

門檻凍結後才重跑 F5/F6。最終接受 375/500（75.0%）；semantic rejects 62：
synthetic duplicate 16、seed duplicate 33、seed outlier 1、Val/Test
contamination 12。F6 exclusion log 記錄 sample id、matched eval id、split 與
similarity。

## M6 fixed gate

75.0% pilot yield 的 Wilson 95% 下界是 71.02%。依實測每筆 1.287466431 秒，
保守產生 11,264 筆可望留下至少 8,000 筆，投影 4.028 小時；低於固定五小時
上限 13,980 筆。因此 gate 通過，且沒有為放行而調整 thresholds。
