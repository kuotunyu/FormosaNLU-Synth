# HANDOFF.md — 早晨交接報告

> 使用者早上第一個看的檔案。夜間執行的 agent 依 `docs/AUTONOMOUS_RUN.md` §9 持續更新這份文件。
> **最新的寫在最上面。** 每次更新都帶時間戳，這樣即使中途掛掉也看得出進度到哪。

---

## 📌 早晨摘要

> 夜間執行結束前必須填完這一節。使用者只讀這裡也要能掌握全局。

**尚未執行。** 這是 2026-07-27 深夜建立的骨架，夜間 agent 開工後會覆寫本節。

| 項目 | 內容 |
|---|---|
| 執行區間 | — |
| 完成到 | — |
| 卡住的項目 | — |
| GPU 時數 | — |
| 磁碟增加 | — |
| API 花費 | $0（本專案不使用任何付費 API） |

### 🔴 需要你決定（最重要的放最前面）

<!-- 逐條列出。每條要有：問題、背景、我建議的選項、以及不決定會擋住什麼 -->

_（尚無）_

### 👀 需要你 review 的產出

<!-- 例如 docs/teacher_choice.md、reports/pilot_report.md、M8 零樣本結果 -->

_（尚無）_

### ➡️ 明天的建議起點

_（尚無）_

---

## 🗒️ 執行日誌

> 格式：`### [時間] 里程碑 — 狀態`，內容含產出、驗證結果、耗時。
> 卡住時另加：完整錯誤訊息、試過的兩種修法、建議下一步。

### [2026-07-27 03:45 +08:00] M2 teacher/judge 選型 — 完成

- Teacher 定案為 `qwen3.6:27b`：20/20 JSON-valid、18/20 intent／slot／grounding
  全對；4 併發為 35.86 tok/s，8 併發沒有額外收益
- Teacher 模型 VRAM 峰值 15,820 MiB，全 GPU 峰值 18,277 MiB
- Judge `gpt-oss:20b` 兩輪共 40/40 JSON-valid，四個布林判定一致率 95%
- 找到相容性要求：gpt-oss request 不可傳 `think: false`，否則回空內容
- 成功 measured batches 共 128.67 秒（0.036 GPU h）；warmup 與失敗診斷未計時
- API 花費 $0；teacher／judge 已卸載，沒有模型常駐 VRAM
- 決策與授權證據：`docs/teacher_choice.md`、D-010；原始數字在 `reports/m2_*`

### [2026-07-27 03:14 +08:00] M0 環境與骨架 — 進行中

- 已確認工作樹乾淨、沒有 GitHub remote；現有兩筆 commit 的 author 都是 `kuotunyu`
- 已確認 repo-local Git identity 為 `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`
- 開始檢查 Python／uv／Git LFS／Ollama／RTX 4090／磁碟，並建立可重現的 Python 環境與 package 骨架
- 不讀取 `../.env` 內容，只檢查檔案是否存在

### [2026-07-27 03:30 +08:00] M1 資料稽核 + split 凍結 — 完成

- 精準載入 MASSIVE `zh-TW`：train 11,514／validation 2,033／test 2,974
- 稽核確認 60 intents、55 slot types；train 每 intent 介於 4–810 筆
- 實際 `min(20, available)` 共 1,176 筆，不是 1,200；seed=42
- `splits/manifest.json` 已連續重建驗證：`c3c9b568772c69c52d2bef9a5b881fc6fd100037562bf830ff9161f6b238632f`
- 產出 `reports/m1_data_audit.{md,json}` 與兩張分布圖；兩張圖都已開啟目視，軸標與尺度正常
- `pytest`: 8 passed；Ruff: all checks passed

### [2026-07-27 03:28 +08:00] M0 環境與骨架 — 完成

- `requirements.txt`、`uv.lock`、`.venv`、Python package 骨架與 `scripts/check_env.py` 完成
- 環境健檢全綠：Python 3.10.9、uv 0.11.18、Git LFS、RTX 4090、Ollama 0.32.0
- 下載 teacher 候選 `qwen3.6:27b`（17GB）；judge `gpt-oss:20b` 已存在
- 下載後 C: 尚餘 164.4 GiB，高於 100 GiB 護欄；無模型常駐 VRAM
- 詳細結果：`reports/m0_environment.md`

### [2026-07-27 深夜] 文件層建置 — 完成

- 建立 `docs/AUTONOMOUS_RUN.md`（無人監督執行守則）、本檔、`.claude/settings.json`（權限 allowlist）
- 預先授權：Ollama 模型 pull、MASSIVE 下載、Gemma 4 student 下載、M2 自動定案、pilot 過門檻自動接全量
- 今晚範圍：**M0 → M8 零樣本 baseline**。M9 訓練批次明確排除
- 下一步：夜間 agent 從 **M0** 開始

---

## 📊 里程碑進度快照

> 每個里程碑結束時更新一列。「驗證」欄只填**真的跑過**的結果。

| 里程碑 | 狀態 | 耗時 | 驗證結果 | 產出 |
|---|---|---|---|---|
| M0 環境與骨架 | ✅ 完成且驗證通過 | 14 分 | 健檢全綠；lock/import/Ruff 通過 | uv 環境、package 骨架、模型 |
| M1 資料稽核 + split 凍結 | ✅ 完成且驗證通過 | 2 分 | 8 tests；manifest SHA256 重建一致 | loader、稽核、圖表、manifest |
| M2 teacher/judge 選型 | ✅ 完成且驗證通過 | 15 分 | teacher 20/20 JSON、18/20 任務有效；judge 一致率 95% | 選型報告、benchmark JSON、D-010 |
| M3 recipes + schema | ⬜ 未開始 | | | |
| M4 生成器 + pilot | ⬜ 未開始 | | | |
| M5 過濾管線 + 測試 | ⬜ 未開始 | | | |
| M6 全量生成 + 過濾 | ⬜ 未開始 | | | |
| M7 data_card 草稿 | ⬜ 未開始 | | | |
| M8 零樣本 baseline | ⬜ 未開始 | | | |
| M9 訓練批次 | 🚫 今晚不做 | — | — | 明晚，需先看過 M8 結果 |

狀態圖例：⬜ 未開始／🔄 進行中／✅ 完成且驗證通過／⚠️ 完成但有問題／🛑 卡住／🚫 不在範圍
