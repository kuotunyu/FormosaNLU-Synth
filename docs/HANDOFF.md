# HANDOFF.md — 早晨交接報告

> 使用者早上第一個看的檔案。夜間執行的 agent 依 `docs/AUTONOMOUS_RUN.md` §9 持續更新這份文件。
> **最新的寫在最上面。** 每次更新都帶時間戳，這樣即使中途掛掉也看得出進度到哪。

---

## 📌 早晨摘要

> 夜間執行結束前必須填完這一節。使用者只讀這裡也要能掌握全局。

| 項目 | 內容 |
|---|---|
| 執行區間 | 2026-07-27 03:14–04:44 +08:00 |
| 完成到 | M0–M3 完成；M4 pilot 完成；M5/M7/M8 可離線完成部分已完成 |
| 卡住的項目 | BGE-M3 未獲下載授權；Windows PyTorch `c10.dll` WinError 1114 |
| GPU 時數 | 0.292 h（M2–M4 measured work；M8 未使用 GPU） |
| 磁碟增加 | 約 19 GiB；含 Gemma 4 14.924 GiB snapshot |
| API 花費 | $0（本專案不使用任何付費 API） |

### 🔴 需要你決定（最重要的放最前面）

<!-- 逐條列出。每條要有：問題、背景、我建議的選項、以及不決定會擋住什麼 -->

1. **核可 BGE-M3 權重下載。** 官方單一權重約 2.27GB；核可後才能量測
   F5/F6、確認最終 yield，並決定 ≤13,980 筆的 M6 生成量。建議核可。
2. **處理 Windows PyTorch DLL。** 專案內 PyPI torch 2.13 與官方 CUDA 12.8
   torch 2.11 都在載入 `c10.dll` 時報 WinError 1114。建議你在場時先檢查
   Visual C++ runtime；或核可我用乾淨的 uv-managed Python 重建，不要再疊在
   目前 Anaconda Python 上。這會擋住 Gemma one-step smoke 與零樣本 baseline。

### 👀 需要你 review 的產出

<!-- 例如 docs/teacher_choice.md、reports/pilot_report.md、M8 零樣本結果 -->

- `docs/teacher_choice.md`：teacher/judge 定案與完整 benchmark
- `reports/pilot_report.md`：500 筆 pilot、過濾漏斗、固定 gate
- `reports/m8_training_design.md`：Gemma artifact、QLoRA 設計與 runtime blocker
- `reports/m8_zeroshot_baseline.md`：誠實的 blocked baseline（沒有假數字）
- `docs/data_card.md`：已由 pilot 證據填入的 M7 草稿

### ➡️ 明天的建議起點

先修 PyTorch DLL 並跑 one-step `real_only` smoke；同時核可 BGE-M3。完成
F5/F6 後重算 gate，只有在真實 yield 與五小時限制同時成立時才啟動 M6。

---

## 🗒️ 執行日誌

> 格式：`### [時間] 里程碑 — 狀態`，內容含產出、驗證結果、耗時。
> 卡住時另加：完整錯誤訊息、試過的兩種修法、建議下一步。

### [2026-07-27 04:44 +08:00] M7/M8 — 草稿與管線完成，model runtime 卡住

- Gemma 4 snapshot 14.924 GiB 完整下載；revision、size、SHA256、license 已記錄
- 選用官方文字-only `Gemma4ForCausalLM`，避免載入無用的 vision/audio towers
- QLoRA config、prompt contract、六組 run plan、resumable trainer、零樣本 Test
  harness、strict parser 與 metrics 完成；45 tests、Ruff、lock check 通過
- 11,514 筆 prompt+target tokenizer audit：P99 127、最大 183 tokens；
  512-token 設定有餘裕
- 阻塞錯誤：`OSError: [WinError 1114] ... torch\lib\c10.dll`
- 修法一：全新解析 PyPI torch 2.13；修法二：改用官方 cu128 torch 2.11 並
  locked sync；兩者相同錯誤，依規則停止，不動系統 DLL／PATH／driver
- 零樣本結果所有 metrics 明確為 `null`，M9 沒有啟動
- M7 data card 已填 pilot 可證明內容；full-corpus 欄位仍標示 blocked
- 新增 `scripts/verify_contributors.py` 作為 push 前 gate：只允許
  `kuotunyu` 的既有身份，並拒絕任何共同作者 trailer

### [2026-07-27 04:26 +08:00] M5 過濾管線 — 程式完成，production calibration 卡住

- F1–F7 程式契約與 pass/fail 測試完成；全專案 36 tests passed、Ruff 通過
- F1–F4 實跑：437 accepted + 63 rejected = 500；主要拒絕為 label contract
  21、grounding/overlap 25、簡體 13、language ratio 4
- Judge 修正後 50/50 JSON、49/50 accepted（98%），唯一漏檢是非請求片段
- F5/F6 vectorized cosine、去重／離群／污染決策與去汙染 log 都有測試，但
  production BGE-M3 權重未下載、threshold 仍為 null
- 卡點：官方 BGE-M3 單一權重約 2.27GB；夜間預授權模型清單不含 embedding
  model，硬性禁止下載清單外模型
- 已試的合法替代：完成 lazy local-only backend 與固定向量測試；拒絕用
  TF-IDF／小模型數字冒充 BGE-M3
- 建議：早上核可指定 BGE-M3 必要權重後，跑分布、看圖、定 threshold

### [2026-07-27 04:20 +08:00] M4 生成器 + 500 筆 pilot — 生成完成，gate 未放行

- 斷點驗證：5/12 後續跑到 12/12；index 連續、id 唯一，第三次重跑 SHA 不變
- 正式 pilot 500/500：500 unique ids、100% JSON；固定 recipe 比例正確
- Teacher：643.73 秒、126,353 prompt tokens、21,910 output tokens、$0
- F1–F3 90.8%，F1–F4 87.4%；judge 98%
- 現行 18,000 筆線性投影 6.44 h，超過 5 h；5 h 最多約 13,980 筆
- F1–F6 尚無真實接受率，無法證明 13,980 筆能留下 8,000，因此 M6 未放行
- 完整報告：`reports/pilot_report.md`

### [2026-07-27 04:05 +08:00] M3 recipes + schema — 完成

- 凍結 60 intents／55 slot types 與 SHA256，程式會對
  `splits/manifest.json` 驗證漂移
- 完成 `CandidateOutput`／`SyntheticSample`／完整 provenance schema；合成 id
  是不含時間與機器路徑的 content-address
- 四個 recipe 與 Markdown prompt 均版本化；slot substitution 的新 value 由程式
  決定，teacher 只修語氣
- 第一輪 20/20 JSON、16/20 契約合格；保留完整 v1 證據後改善 prompt
- 採用版本第二輪 20/20 JSON、19/20 intent／slot／grounding 契約合格；
  四種 recipe 各 5 筆、兩種 style 都已輸出到 review 報告
- 17 tests passed；Ruff 與 `git diff --check` 通過
- 兩輪 measured wall time 共 67.68 秒；結束後模型已卸載，GPU 回到約 960 MiB

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
| M3 recipes + schema | ✅ 完成且驗證通過 | 20 分 | 17 tests；20/20 JSON、19/20 契約；兩種 style | schema、labels、4 recipes、版本化 prompts、dry-run 報告 |
| M4 生成器 + pilot | ⚠️ Pilot 完成，gate 未放行 | 15 分開發 + 14 分 GPU | 500/500；F1 100%、F1–F3 90.8%、judge 98%；F5/F6 未量測 | resumable generator、pilot、報告 |
| M5 過濾管線 + 測試 | ⚠️ 程式完成，runtime 卡住 | 15 分 | 36 tests；F1–F4 漏斗對齊；BGE thresholds=null | F1–F7 程式、funnel、狀態報告 |
| M6 全量生成 + 過濾 | 🛑 未獲 gate 放行 | — | 18k 投影 6.44h；F1–F6/8k yield 未證明 | 未執行 |
| M7 data_card 草稿 | ⚠️ Pilot-backed 草稿完成 | 5 分 | 所有已填數字可追溯；全量欄位留待 M6 | data card |
| M8 零樣本 baseline | 🛑 管線完成，runtime 卡住 | 18 分 + 下載 | 45 tests；artifact hash/size；torch WinError 1114 | config、trainer、eval、blocked report |
| M9 訓練批次 | 🚫 今晚不做 | — | — | 明晚，需先看過 M8 結果 |

狀態圖例：⬜ 未開始／🔄 進行中／✅ 完成且驗證通過／⚠️ 完成但有問題／🛑 卡住／🚫 不在範圍
