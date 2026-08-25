# NEXT_SESSION.md — 接手指南

> **最後更新**：2026-08-11，v1.2.2 publication closeout 完成
> **目前狀態**：所有研究與 GPU 階段完成；Phi adapter 已公開，technical report
> PDF、v1.2.2 tag／GitHub Release／Zenodo version DOI 均已完成，不需要使用者操作。

---

## 0. 三十秒摘要

FormosaNLU 研究本機 open-weight teacher 生成的 synthetic data，能否改善小型
language model 在正體中文（台灣）NLU（intent classification + slot filling、固定
JSON 輸出）的 low-resource 表現。

公開產物：

- GitHub：<https://github.com/kuotunyu/FormosaNLU-Synth>
- GitHub latest stable Release：[v1.2.2](https://github.com/kuotunyu/FormosaNLU-Synth/releases/tag/v1.2.2)
- Zenodo all versions：[`10.5281/zenodo.21767492`](https://doi.org/10.5281/zenodo.21767492)
- Zenodo v1.2.2：[record 21879133](https://zenodo.org/records/21879133)；DOI [`10.5281/zenodo.21879133`](https://doi.org/10.5281/zenodo.21879133)
- Zenodo Technical note：[record 21879155](https://zenodo.org/records/21879155)；DOI [`10.5281/zenodo.21879155`](https://doi.org/10.5281/zenodo.21879155)；CC BY 4.0、非 peer reviewed
- HF Dataset：`steven0226/formosa-nlu-synth-v1`（3,754 rows）
- HF Gemma Model：`steven0226/gemma-4-e4b-formosanlu-lora`
- HF Phi Model：`steven0226/phi-4-mini-formosanlu-lora`（public、seed 42、SHA-256 verified）
- Technical report：`paper/formosanlu_synth.pdf`；公開 Technical note 與 3 個檔案已完成匿名下載驗證

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
| Tagged release commit | `d9ea6bb4dd6c80c5c4f5aaa65ad81c1de45725e7` |
| Annotated tag | `v1.2.2`，tagger `kuotunyu`；舊 tags 未移動 |
| GitHub Release | [v1.2.2](https://github.com/kuotunyu/FormosaNLU-Synth/releases/tag/v1.2.2)；非 draft、非 prerelease；7 個 hash-verified assets |
| Zenodo | Public；version DOI `10.5281/zenodo.21879133`；creator 僅 `kuotunyu` |
| 本機 gates | Ruff、完整 pytest、README verifier、contributors audit、reproduce verifier 全綠 |
| Release preflight | `public_verified`；blocking 為空 |
| Contributors | GitHub API 只有 `kuotunyu` |
| Hugging Face | 三張 cards 已同步；Dataset／Gemma／Phi 的資料與 weights hashes 不變 |

`v1.2.2` tag 固定指向 Zenodo 保存的 source snapshot；其後的 DOI backlink／handoff
commit 只前進 `main`，不得移動已公開 tag。`v1.2.1` 與更早 tags 同樣 immutable。

---

## 2. 現在的 publication 待辦

- 不需再跑 M19、M16、M15、M9、F7、generation、extra seeds 或 Colab。
- v1.2.2 software release 沒有剩餘必要工作；不要移動 `v1.2.2` 或更早 tags。
- 未來若新增資料、模型或實驗，另立新 milestone／protocol，不覆寫本版本 artifacts。
- README 依使用者決定維持正體中文（台灣，`zh-TW`）為主，專有名詞保留原文。

若之後要做台灣知識蒸餾、TMMLU+、真實 ASR error 或自然 code-switching corpus，
那是新里程碑／新研究，不是 v1.2.2 的欠件。開始前應另立 protocol、凍結判準與
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
5. **歷史狀態（2026-08-01）**：CI 曾依 D-020 移除；**目前狀態（2026-08-11 起）**：
   tracked `.github/workflows/ci.yml` 已恢復 clean-checkout 驗證。下列本機 gate 範圍更嚴格，
   任何 push 前仍必須執行：

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
