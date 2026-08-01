# M18 — 重現性實測

**日期**：2026-08-01
**方法**：從 GitHub 做乾淨 clone，以 `uv.lock` 建全新環境，照 README 的重現流程逐步執行。
**沒有**使用本機既有的 venv、快取或資料。

## 為什麼要做

README 一直宣稱「單張 4090 全流程可重現」，但這是整份文件裡**唯一沒有證據的宣稱**——其他每個數字都能從 `reports/` 重算，只有這條靠信任。

## 執行環境

| 項目 | 值 |
|---|---|
| 來源 | `git clone https://github.com/kuotunyu/FormosaNLU-Synth.git` |
| Clone 大小 | 5.3 MB |
| 環境建置 | `uv sync --extra demo` → rc=0，venv 4.9 GB |
| Python | 3.11.15（由 `.python-version` 決定） |
| torch | 2.11.0+cu128 |

## 結果

| README 步驟 | 結果 |
|---|---|
| 1. `uv sync --extra demo` | ✅ rc=0 |
| 1. `python -m scripts.check_env` | ✅ exit 0（兩個 WARN，見下） |
| 2. `python -m src.data.freeze_split --verify` | ✅ **重現同一個 SHA256 `c3c9b568…`** |
| 8. `python -m scripts.check_gates` | ✅ **五道全綠** |
| ├ `ruff` | ✅ |
| ├ `pytest` | ✅ 162 passed, 5 skipped |
| ├ `verify_readme` | ✅ 83 項數字檢查 |
| ├ `verify_contributors` | ✅ 82 commits，單一作者 |
| └ `verify_reproduce` | ✅ 21 個文件化指令全部解析成功 |

兩個 WARN 是乾淨 clone 的正確行為，不是問題：

- `external_env absent` —— 共用 `.env` 在 repo 外，clone 到別處自然找不到。Phase 1 不需要任何 API key。
- `git_identity <unset>` —— clone 沒有 repo-local 提交身分。與重現無關。

5 個 skip 是需要 gitignored 的可重生資料（MASSIVE 語料、filtered corpus）的測試，訊息會說明如何取得。

## 找到並修掉三個缺陷

**這次實測的價值不在「通過了」，而在它一開始沒通過。**

| # | 缺陷 | 影響 | 處置 |
|---|---|---|---|
| 1 | `check_env` 的 `git_identity` 比對硬編的維護者 email，且列為必要項 | **README 第一步對所有第三方都失敗** | 改為非必要的 WARN；單一作者由 `verify_contributors` 稽核歷史來保證 |
| 2 | `verify_contributors` 對 `git config --local`（未設定時回傳 1）使用 `check=True` | 乾淨 clone 上**噴 traceback** 而非給出判定 | 未設定時降級為只稽核歷史並印出說明；維護者機器仍執行嚴格身分檢查 |
| 3 | `test_ci_runs_quality_evidence_and_contributor_gates` 讀取已下架的 `.github/workflows/ci.yml` | 本機通過（檔案仍在工作目錄但已 gitignored）、第三方失敗 | 移除。該測試的意圖已由 `test_check_gates` 涵蓋 |

第 1、2 項是同一類：**為作者機器寫的規則，別人不可能滿足**。第 3 項是當天下架 `.github/` 時留下的破口，典型的「在我機器上可以」。

## 沒有驗證的部分

**未在乾淨環境中重跑訓練與生成。** 那需要約 33 GPU 小時、本機 Ollama teacher 與 judge 模型，以及約 45 GB 的模型下載。

本次驗證的是：**環境可從 lockfile 重建、文件記載的每個指令都存在且可解析、所有可離線驗證的檢查都通過、凍結的 split manifest 能被第三方重現出相同雜湊**。

驗證的**不是**「整條管線重跑一次得到相同數字」。這個界線寫在 README，以免被讀成後者。

## 可重複執行

```bash
git clone https://github.com/kuotunyu/FormosaNLU-Synth.git
cd FormosaNLU-Synth
uv sync --extra demo
python -m scripts.check_env
python -m src.data.freeze_split --verify
python -m scripts.check_gates
```

> ⚠️ Windows 注意：第一次驗證選在很深的暫存路徑（283 字元），`transformers` 的部分檔案觸發 MAX_PATH 260 上限而無法開啟，造成假性失敗。改用短路徑後消失。這是驗證位置的問題，不是專案的問題，但值得記著——clone 到接近磁碟根目錄的位置比較安全。
