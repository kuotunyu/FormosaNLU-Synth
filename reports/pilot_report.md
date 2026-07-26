# M4 500-sample Pilot Report

> 執行日：2026-07-27。這份報告只記錄可由 committed JSON 或本機 JSONL
> 重算的數字。M6 **未放行**。

## 1. Generation

| 指標 | 實測 |
|---|---:|
| 完成筆數 | 500 / 500 |
| 連續 generation index | 0–499，無缺漏、無重複 |
| unique synthetic id | 500 |
| JSON-valid | 500 / 500（100%） |
| Prompt tokens | 126,353 |
| Output tokens | 21,910 |
| Wall-clock | 643.73 s（10.73 min） |
| Requests/s | 0.777 |
| Output tokens/s | 34.04 |
| API cost | $0 |

Recipe 配比精確等於設計值：paraphrase 175、slot substitution 150、
noise/code-switch 100、hard negative 75。Style 為 `massive_like` 201、
`tw_colloquial` 299。

斷點續跑在正式 pilot 前另以 12 筆實測：先寫 5 筆，再補 7 筆後 index
0–11 各一次、12 個 id 全唯一；第三次執行顯示 already complete，JSONL 的
SHA256 前後不變。每筆同時保存 deterministic plan fingerprint，prompt／排程
漂移時拒絕接到舊 checkpoint。

原始重算結果：`reports/m4_pilot_generation.json`。

## 2. F1–F4 funnel

補上「輸出 labels 必須等於 code-authored generation plan」的重算後：

| 累積階段 | 通過 | 比率 |
|---|---:|---:|
| F1 schema | 500 | 100.0% |
| F1–F3（含 label contract + groundedness） | 454 | 90.8% |
| F1–F4（含 locale） | 437 | 87.4% |

| 第一個拒絕原因 | 筆數 |
|---|---:|
| `F2_LABEL_CONTRACT_SLOTS` | 21 |
| `F3_UNGROUNDED_OR_OVERLAPPING_SLOT` | 25 |
| `F4_LOCALE_SIMPLIFIED` | 13 |
| `F4_LOCALE_LANGUAGE_RATIO` | 4 |
| **合計** | **63** |

`437 accepted + 63 rejected = 500`，漏斗對得起來。每筆 accepted/rejected
仍保留完整 provenance、filter scores 與第一個 reject reason；本機重生檔在
`data/filtered/`，統計原始檔在 `reports/m5_cheap_filter_funnel.json`。

## 3. F7 independent judge

固定 selection seed 42，共 50 筆：hard negative 32、其他三種 recipe 各 6。
抽樣先取 25 筆 hard negative，再分層補齊，不是只挑容易案例。

第一輪得到 42/50 accepted，但只有 45/50 JSON；5 筆 hard negative 的 reasoning
用完 512-token 上限而沒有 verdict，prompt 也讓 judge 誤以為
「hard-negative recipe 天生該拒絕」。完整錯誤結果保留在
`reports/m4_pilot_judge_v1.json`，沒有覆蓋。

修正 recipe 定義並把 judge 上限改為 768 後，使用同一抽樣策略重跑：

| 指標 | 第二輪 |
|---|---:|
| JSON-valid | 50 / 50 |
| Accepted | 49 / 50 |
| Accepted rate | **98.0%** |
| Wall-clock | 88.37 s |
| Output tokens | 2,028 |

唯一拒絕句是「這個問題真的沒有意義啦」：label contract 合法，但不是完整自然的
助理請求。這是 F1–F4 的真實漏檢，證明 judge 抽審有額外價值。

## 4. Time and yield projection

Pilot generation 為 1.2875 GPU seconds/record。線性外推：

- 現行 `--full` 規劃 18,000 筆約 **6.44 h**，超過 5 h 門檻。
- 在相同速度下，5 h 最多約 **13,980 筆**。
- 要在 13,980 筆內留下 8,000 筆，F1–F6 接受率至少要 **57.22%**。
- 目前只有 F1–F4 的 87.4%；F5/F6 未校準，不能拿 87.4% 假裝最終接受率。

Teacher pilot 成功 batch 為 643.73 GPU s；兩輪 judge 診斷共 207.92 GPU s。
本里程碑實際 GPU wall 共 851.65 s（0.237 h）。若只算最後採用的 judge 輪次，
正式 pilot 路徑是 732.10 s（0.203 h）。

## 5. Fixed autonomous gate

門檻保持 `docs/AUTONOMOUS_RUN.md` 原值，沒有調低：

| # | 固定門檻 | 結果 | 判定 |
|---:|---|---:|---|
| 1 | F1 JSON ≥95% | 100.0% | PASS |
| 2 | F1–F3 ≥70% | 90.8% | PASS |
| 3 | F1–F6 ≥45% | 尚未量測 F5/F6 | **BLOCKED** |
| 4 | Judge 50 筆 ≥80% | 98.0% | PASS |
| 5 | 全量 ≤5 h | 18k 投影 6.44 h | **FAIL（現行數量）** |
| 6 | 最終 filtered ≥8,000 | 需要 F1–F6 接受率 | **BLOCKED** |

因此 M6 全量生成未獲放行。這不是調門檻的理由；需要先完成 BGE-M3
相似度分布、人工看圖定 threshold，再以真實 F1–F6 接受率選擇
≤13,980 的生成量。若該範圍無法同時留下 8,000 筆，固定門檻代表本機路線失敗，
應交由使用者決定下一步。

