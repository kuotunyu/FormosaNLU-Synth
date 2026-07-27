# HANDOFF.md — 早晨交接報告

> 使用者早上第一個看的檔案。夜間執行的 agent 依 `docs/AUTONOMOUS_RUN.md` §9 持續更新這份文件。
> **最新的寫在最上面。** 每次更新都帶時間戳，這樣即使中途掛掉也看得出進度到哪。

---

## 📌 早晨摘要

> 夜間執行結束前必須填完這一節。使用者只讀這裡也要能掌握全局。

| 項目 | 內容 |
|---|---|
| 執行區間 | 2026-07-27 03:14–12:05 +08:00（含使用者返回後續作） |
| 完成到 | M0–M5、M7、M8 完成；M6 正式生成 11,264 筆進行中 |
| 卡住的項目 | 無；M6 投影 4.028 h，期間不可重疊其他 GPU 模型 |
| GPU 時數 | M8 零樣本 summed generation 1.050 h；另有 M2–M4 0.292 h 與短 smoke |
| 磁碟增加 | Gemma 4 14.924 GiB；BGE-M3 dense 必要檔 2.293GB；另有可刪的舊 venv 複本 |
| API 花費 | $0（本專案不使用任何付費 API） |

### 🔴 需要你決定（最重要的放最前面）

<!-- 逐條列出。每條要有：問題、背景、我建議的選項、以及不決定會擋住什麼 -->

目前沒有需要使用者立即操作的 blocker。請在 M6 約四小時執行期間不要從其他
專案啟動 GPU 模型。Python runtime 已修復，沒有修改系統 PATH、driver 或 DLL。

### 👀 需要你 review 的產出

<!-- 例如 docs/teacher_choice.md、reports/pilot_report.md、M8 零樣本結果 -->

- `docs/teacher_choice.md`：teacher/judge 定案與完整 benchmark
- `reports/pilot_report.md`：500 筆 pilot、過濾漏斗、固定 gate
- `reports/m8_training_design.md`：Gemma artifact、文字塔 key mapping 與 QLoRA smoke
- `reports/m8_zeroshot_baseline.md`：完整 2,974-row 嚴格零樣本 baseline
- `docs/data_card.md`：已由 pilot 證據填入的 M7 草稿

### ➡️ 明天的建議起點

監控 M6 可續跑 checkpoint。11,264 筆完成後跑相同 F1–F6、產生正式 filtered /
unfiltered corpus 與漏斗報告；不足 8,000 就如實停下分析，不調門檻。

---

## 🗒️ 執行日誌

> 格式：`### [時間] 里程碑 — 狀態`，內容含產出、驗證結果、耗時。
> 卡住時另加：完整錯誤訊息、試過的兩種修法、建議下一步。

### [2026-07-27 12:24 +08:00] M5 → M6 — fixed gate 通過，正式生成啟動

- BGE-M3 dense 必要檔 2,293,322,213 bytes，主權重 SHA-256 已記錄；
  local-only CUDA calibration 約 18 秒，peak allocated 2.31 GiB
- 人工看過分布圖與 top/bottom 25 pairs 後凍結 thresholds：
  synthetic 0.999、seed copy 0.995、outlier 0.650、Val/Test 0.990
- F1–F6 pilot：375/500（75.0%）；semantic rejects 62，含 F6 exclusions 12
- Wilson 95% yield 下界 71.02%；保守生成 11,264 筆可望留下至少 8,000；
  投影 4.028 h，小於 5 h / 13,980 筆固定上限
- `qwen3.6:27b` 正式生成已啟動；checkpoint 每筆 fsync、每 25 筆回報，
  可中斷續跑

### [2026-07-27 12:05 +08:00] M8 — runtime 修復、QLoRA smoke 與完整 baseline 完成

- uv-managed CPython 3.11.15 排除 Anaconda 舊 Visual C++ runtime 衝突；
  PyTorch 2.11.0+cu128、CUDA、RTX 4090 全部通過
- E4B multimodal 權重的 `model.language_model.*` 明確 remap 至文字模型
  `model.*`；665 個語言權重載入，vision/audio 權重刻意忽略
- one-step `real_only` QLoRA smoke：train loss 1.9862、eval loss 2.9560、
  peak allocated VRAM 20,646 MiB；adapter 與 checkpoint 均寫出且已 hash
- 零樣本 Test 2,974/2,974：JSON-valid 17.38%、intent accuracy 10.66%、
  macro-F1 23.12%、slot F1 0%、exact 8.10%；所有 invalid row 都留在分母
- 517 筆 strict-valid output 中 317 筆 intent 正確（61.32%），僅列為診斷；
  未修補輸出、未 constrained decode、未依 Test 調 prompt
- batch 4→8 只做吞吐工程；checkpoint 0–2,973 連續、可中斷續跑
- BGE-M3 dense 必要檔 2,293,322,213 bytes 已下載；因 SafeSynth 正佔滿 GPU，
  暫不與它同時載入

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
