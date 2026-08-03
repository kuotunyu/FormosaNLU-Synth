# NEXT_SESSION.md — 接手指南

> **最後更新**：2026-08-03，v1.2.0 已發布
> **目前狀態**：專案完成，沒有待跑的 GPU 階段，也沒有需要使用者操作的發布步驟。

---

## 0. 三十秒摘要

FormosaNLU 研究本機 open-weight teacher 生成的 synthetic data，能否改善小型
language model 在正體中文（台灣）NLU（intent classification + slot filling、固定
JSON 輸出）的 low-resource 表現。

公開產物：

- GitHub：<https://github.com/kuotunyu/FormosaNLU-Synth>
- GitHub Release：[v1.2.0](https://github.com/kuotunyu/FormosaNLU-Synth/releases/tag/v1.2.0)
- HF Dataset：`steven0226/formosa-nlu-synth-v1`（3,754 rows）
- HF Model：`steven0226/gemma-4-e4b-formosanlu-lora`

核心 paired 結果已在 Gemma 4 E4B 與 Phi-4-mini 兩個 student family 複製；M19
再完成五組 equal-N per-recipe ablation。四個 leave-one-recipe-out 組別相對
control 的 exact-match delta 為 +0.50、+2.02、-0.74、+1.31 percentage points，
全部低於預先登記的 2.5-point detectability threshold。因此正式結論是
`no_difference_reaches_preregistered_detectability_threshold`，且
`causal_claim_allowed=false`。

全專案可追溯 local GPU time 為 42.412 h，API 花費 $0。資源帳本沒有 pending
phase；GPU、Ollama 與 M19 processes 已回到 idle／不存在。

---

## 1. 發布狀態

| 項目 | 結果 |
|---|---|
| Core commit | `07493cacb26dea5daaa03aafdbc1497b12678405` |
| Annotated tag | `v1.2.0`，tagger `kuotunyu` |
| GitHub Release | 非 draft、非 prerelease |
| 本機 gates | Ruff、完整 pytest、README verifier、contributors audit、reproduce verifier 全綠 |
| Release preflight | `public_verified`；blocking 為空 |
| Contributors | GitHub API 只有 `kuotunyu` |
| Hugging Face | Dataset／adapter 刻意不變；v1.2.0 是 evidence release |

`v1.2.0` tag 指向 M19 core commit；其後若有文件-only handoff commit，不得移動
已公開 tag。

---

## 2. 現在沒有待辦

- 不需再跑 M19、M16、M15、M9、F7、generation、extra seeds 或 Colab。
- 不需重傳 Hugging Face Dataset／Model；其資料與權重 hash 刻意維持不變。
- 不需建立新 tag 或修改既有 tag。
- README 依使用者決定維持正體中文（台灣，`zh-TW`）為主，專有名詞保留原文。

若之後要做台灣知識蒸餾、TMMLU+、真實 ASR error 或自然 code-switching corpus，
那是新里程碑／新研究，不是 v1.2.0 的欠件。開始前應另立 protocol、凍結判準與
資源預算，不能把 M19 的 single-seed 結果事後升級成 recipe-level causal claim。

---

## 3. 接手時的安全鐵律

1. 先讀 `CLAUDE.md`、`docs/DECISIONS.md`、`docs/HANDOFF.md`。
2. 不改 frozen corpus、thresholds、prompt、training config、strict parser、seeds
   或 evaluation contract。
3. 不重跑已完成階段；需要新實驗時建立新 milestone 與預先登記 protocol。
4. Git author／committer 只能是
   `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`，commit 不得有
   `Co-Authored-By`；GitHub Contributors 只能有 `kuotunyu`。
5. CI 已依 D-020 移除。任何 push 前都必須執行：

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.check_gates --quiet
   ```

6. 已發布的 tag 不移動。發布前另跑：

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.release_preflight
   ```

7. 不修改、停止或干預其他 sibling 專案與未知程序；GPU 工作必須通過專案安全閘門。

---

## 4. 主要證據入口

- `README.md`：研究問題、方法、主結果、限制與重現入口
- `reports/m10_main_results.md`：Gemma primary 七行主表
- `reports/m14_paired_statistics.md`：paired statistics
- `reports/m15_cross_model_replication.json`：Phi cross-family replication
- `reports/m16_robustness_summary_gemma.json`：Gemma seeds 42–44 robustness
- `reports/m16_robustness_summary_phi4mini.json`：Phi-4-mini seeds 42–44 robustness
- `reports/m19_ablation.json`：M19 machine-readable aggregate
- `reports/m19_runtime_audit.json`：M19 中斷 attempt 的 hash-anchored resource audit
- `reports/m12_resource_ledger.json`：完整本機 GPU 資源帳本
- `docs/DECISIONS.md`：不可事後改寫的設計與判讀紀錄
- `docs/HANDOFF.md`：最新發布與完整工作日誌

---

## 5. 常用唯讀驗證

```powershell
# 所有本機 gates
.\.venv\Scripts\python.exe -m scripts.check_gates --quiet

# README 數字從 reports 重算
.\.venv\Scripts\python.exe -m scripts.verify_readme

# sole-contributor audit
.\.venv\Scripts\python.exe scripts/verify_contributors.py

# 公開 GitHub／HF artifacts 驗證
.\.venv\Scripts\python.exe -m scripts.verify_publication
```

這些命令不會啟動 GPU 訓練。
