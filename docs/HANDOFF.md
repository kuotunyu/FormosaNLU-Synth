# HANDOFF.md — 早晨交接報告

> 使用者早上第一個看的檔案。夜間執行的 agent 依 `docs/AUTONOMOUS_RUN.md` §9 持續更新這份文件。
> **最新的寫在最上面。** 每次更新都帶時間戳，這樣即使中途掛掉也看得出進度到哪。

---

## 📌 早晨摘要

> 夜間執行結束前必須填完這一節。使用者只讀這裡也要能掌握全局。

| 項目 | 內容 |
|---|---|
| 執行區間 | 2026-07-27 03:14–2026-07-29 22:24 +08:00（跨多次使用者回來後續作） |
| 完成到 | M14 GitHub/HF v1.0.0 release 完成；M15 CPU pipeline 與判準完成 |
| 卡住的項目 | M15 下載 7.7 GB Phi-4-mini 前需依專案 >2 GB 規則取得使用者明示同意 |
| GPU 時數 | primary core 14.440 h；auxiliary 8.685 h；可追溯 local total 23.124 h |
| 磁碟增加 | Gemma 4 14.924 GiB；BGE-M3 2.293GB；Marian 必要檔 630.6MB；另有可刪舊 venv |
| API 花費 | $0（本專案不使用任何付費 API） |

### 🟡 目前只需一項確認

<!-- 逐條列出。每條要有：問題、背景、我建議的選項、以及不決定會擋住什麼 -->

Primary 六組已用固定 3,760-row filtered corpus 完成，沒有放寬 thresholds。
M14 不需要 GPU，Codex 正在收尾。M15 擬使用
`microsoft/Phi-4-mini-instruct` 做第二 student family；模型約 7.7 GB，
需使用者明示同意下載。下載後會先做 token／VRAM／resume smoke，通過才排
`real_only`／`real_syn_filtered` × seeds 42–44 的過夜批次。

### 👀 需要你 review 的產出

<!-- 例如 docs/teacher_choice.md、reports/pilot_report.md、M8 零樣本結果 -->

- `docs/teacher_choice.md`：teacher/judge 定案與完整 benchmark
- `reports/pilot_report.md`：500 筆 pilot、過濾漏斗、固定 gate
- `reports/m8_training_design.md`：Gemma artifact、文字塔 key mapping 與 QLoRA smoke
- `reports/m8_zeroshot_baseline.md`：完整 2,974-row 嚴格零樣本 baseline
- `reports/generation_report.md`：M6 正式漏斗、mode collapse 與負面結果
- `reports/m9_preflight.md`：六組筆數、Standard Aug 與 checkpoint resume 實證
- `docs/M9_OVERNIGHT_RUNBOOK.md`：睡前一鍵 preflight、3,760 明示 guard、續跑與停損
- `reports/m6_f7_judge.json`：376-row independent judge 完整結果
- `reports/m6_f7_release.json`：6 筆排除與 3,754-row release-only corpus hash
- `reports/m10_main_results.md`：zero-shot + 六組 trained 的完整七行 primary 主表
- `reports/m11_demo_evidence.json`：五句真模型 base-versus-adapter 原始輸出、
  strict validity、latency 與 adapter hash
- `reports/m12_resource_ledger.json`：14.440 h 可追溯 primary GPU 資源帳本
- `assets/m12_*.png`：主表、filter 比較、漏斗、per-intent 與方法圖
- `src/inference/demo.py`：base vs filtered adapter 的 M11 Gradio 比較介面
- `reports/m10_probe_manifest.json`：8,922-row evaluation-only robustness probe
- `docs/data_card.md`：已填入 full-corpus 結果的 pre-release 草稿

### ➡️ 接下來的建議起點

先讓 M14 GitHub CI／Release 全綠，再執行 M15 第二 student paired replication。
不要覆寫 v1 release corpus、frozen thresholds 或 Gemma primary runs。

---

## 🗒️ 執行日誌

> 格式：`### [時間] 里程碑 — 狀態`，內容含產出、驗證結果、耗時。
> 卡住時另加：完整錯誤訊息、試過的兩種修法、建議下一步。

### [2026-07-29 22:24 +08:00] M14 v1.0.0 — 完成

- GitHub Actions run
  [30460498184](https://github.com/kuotunyu/FormosaNLU-Synth/actions/runs/30460498184)
  在 clean Linux checkout 全綠：Node 24 actions、Ruff、127 tests、README
  evidence、sole-contributor history
- GitHub annotated tag `v1.0.0` 指向
  `fceaef1c2b9b742b115fd45ca82ceec2f1ac0fc6`，tagger 為 `kuotunyu`
- GitHub Release：
  <https://github.com/kuotunyu/FormosaNLU-Synth/releases/tag/v1.0.0>
- GitHub Contributors API 複驗仍只有 `kuotunyu`

### [2026-07-29 22:14 +08:00] M14/M15 — release hardening 與 CPU preflight

- HF Dataset／Model cards 已同步 M14 paired statistics，兩者各建立
  `v1.0.0` tag；dataset 3,754 rows 與 adapter SHA-256 均未改
- GitHub CI 已證明 clean Linux checkout 的 Ruff、117 項可重現 tests 與
  README verifier 全綠；sole-contributor step 失敗只因 runner 沒有 local
  Git identity，已改為 CI 僅 audit history，本機仍強制 audit identity + history
- Phi remote metadata 已固定 revision
  `cfbefacb99257ffa30c83adab238a50856ac3083`、MIT、
  7,691,526,227 download bytes；下載後 C: 預估仍有 130.7 GiB
- 新增隔離的 M15 config、generic causal-model loader、兩組 × 三 seeds
  resumable training/evaluation pipeline、artifact／VRAM／resume／strict-output gates
- 跨模型 claim 已在看結果前凍結：`intent_accuracy` 與 `exact_match` 在 Gemma
  與 Phi 都須 mean Δ > 0 且 hierarchical 95% CI lower bound > 0；不 pooling families

### [2026-07-29 21:55 +08:00] M14 paired statistics — 核心計算完成

- 讀取六份 ignored prediction JSONL：2 groups × seeds 42–44，每份 2,974 rows；
  paired expected rows 與連續 indices 全部一致，SHA-256 寫入 machine report
- 5,000 次 hierarchical paired bootstrap：intent accuracy Δ +4.14 points，
  95% CI [+2.60, +5.59]；exact Δ +3.86，CI [+2.75, +4.92]
- 每 seed 的 intent accuracy／exact match exact McNemar tests 經六項 Holm
  correction 後全部顯著，最大 adjusted p 約 0.00017
- 統計適用 frozen MASSIVE `zh-TW` Test 與 Gemma contract，不宣稱跨模型泛化
- 已新增 `CITATION.cff`、CI workflow、v1.0.0 metadata，總驗收尚未完成

### [2026-07-29 19:45 +08:00] M13 public release — 完成

- GitHub `kuotunyu/FormosaNLU-Synth` 已轉 Public；公開前後 Contributors
  API 均只有 `kuotunyu`
- HF Dataset `steven0226/formosa-nlu-synth-v1`：3,754 rows、60 intents、
  3,754 unique IDs，Dataset Viewer HTTP 200，CC BY 4.0
- HF Model `steven0226/gemma-4-e4b-formosanlu-lora`：Apache-2.0、
  `google/gemma-4-E4B-it` base、686 tensors、adapter SHA-256
  `f70f423814dcd47943c92c0beb8b08a4e7f65e60a44355d3dcd95bed9f0bd60a`
- 發布採 Private-first：逐檔回下載 SHA 比對全綠後，才依使用者明確授權
  依序公開 GitHub → Dataset → Model
- 匿名 `load_dataset`、PEFT config、safetensors、GitHub API 與 Dataset
  Viewer 全部通過

### [2026-07-29 12:52 +08:00] M10 robustness — 完成

- `real_only` 與 `real_syn_filtered` seed-42 adapters 各完成 8,922-row
  deterministic robustness probes；兩份 JSONL 都是 index 0–8,921、
  8,922 unique indices 與 8,922 unique source/probe keys
- `real_only` 整體 intent 71.61%、slot F1 60.59%、exact 46.33%；
  filtered 為 73.27%、64.13%、48.79%
- filtered 在 ASR-noise、colloquial、lexical 三種 probes 的 intent／slot／exact
  全部高於 `real_only`；ASR-noise 是兩組最困難的 probe
- Combined report、batch report、evaluation-only contract 與兩個 return code
  全部驗證；GPU 正常釋放
- robustness 耗時 2.102 GPU h；重建後可追溯 local total 23.124 h，
  resource ledger `status=complete_all_local_gpu` 且 pending 為空

### [2026-07-29 10:46 +08:00] M9 三種子 uncertainty — 完成

- `real_only` 與 `real_syn_filtered` 的 seeds 43/44 四組訓練、各 2,974-row
  Test evaluation 全部完成；資料/config SHA-256 與 primary contract 一致
- 三種子 paired Δ：intent accuracy +4.14 ± 1.39 points（95% CI
  [+0.68, +7.59]）；exact match +3.86 ± 0.73（[+2.03, +5.68]）
- `n=3`、Student's t（df=2）interval 只作 descriptive uncertainty，
  不宣稱廣泛統計顯著性
- Ruff、pytest、README verifier、contributors audit 全綠後，以
  `kuotunyu` 單一作者推送 commit `22a32b7`
- 第二次 25 分鐘 GPU safety gate 通過後，robustness 已由 frozen 命令啟動

### [2026-07-29 04:02 +08:00] M11 real demo evidence — 完成

- 兩次 GPU safety gate 全綠後，以 `google/gemma-4-E4B-it`、
  filtered seed-42 adapter 與 unconstrained decoding 跑固定五句
- base model 0/5 通過嚴格 schema；filtered adapter 5/5 通過。這是 curated
  qualitative evidence，不是 Test-set accuracy estimate
- evidence 綁定 adapter tree SHA-256
  `fec6f9214022eae0fb7ece8a29a7cfdb90188fd770829045dc6b1ee0e5faccac`
  與 source commit `3a39eae4cf04ad6984f984134da03c6b635613bb`
- 完整原始輸出與 latency 在 `reports/m11_demo_evidence.json`；commit
  `53182a5` 已推送，GitHub author/committer/Contributors 均只有 `kuotunyu`

### [2026-07-29 03:37 +08:00] F7 independent judge — 完成

- 從 checkpoint 64/376 依原命令安全續跑，完成 376/376；JSON、index、
  sample ID 與 manifest 全部一一對齊
- `gpt-oss:20b` 接受 370、拒絕 6；random stratum 拒絕 3/50，觀察漏檢率
  6.0%，Wilson 95% interval 2.06%–16.22%
- hard-negative 272/275、boundary-conflict 51/51 通過；這兩個 targeted
  strata 不是全 corpus 的無偏估計
- 6 筆已知不合格列已從 release-only corpus 排除，留下 3,754 筆；
  frozen 3,760-row M9 training input 不回溯修改
- 完整 judge result SHA-256
  `c3dfb06b8cae439a876ef28dcfe0fe28488fc22a6c14ebf0abbe37036b142d55`
- Ruff、98 tests、README 22 項 artifact 對照與 contributor audit 全綠

### [2026-07-29 00:25 +08:00] Colab portability — 完成並匯入

- 使用者在 G4（NVIDIA RTX PRO 6000 Blackwell 96 GB）完成 `real_only`
  seed 42、500 steps；training runtime 1,914.7 秒，peak allocated
  20,646 MiB
- Google Drive 下載為兩個 ZIP；兩包均通過 archive integrity、安全路徑與
  secret pattern 檢查，合併匯入 `results/colab/real_only/seed_42/`
- `status/group/seed`、資料筆數、batch、max steps、參數量與 global step
  均和本機 primary 相同；frozen config 完全一致
- final adapter safetensors 可讀取（686 tensor keys）；不同硬體與套件環境下
  不要求 adapter weights 逐位元相同
- 完整可追溯證據寫入 `reports/m9_colab_portability.json`

### [2026-07-28 22:06 +08:00] GitHub repository — 改名為 FormosaNLU-Synth

- 使用者確認正式名稱為 `kuotunyu/FormosaNLU-Synth`，讓名稱直接表達
  synthetic data 主題
- GitHub rename 保留完整 commit history、Private visibility 與 `main`
- local origin、release gate、文件、Colab Drive path 與 GPU automation
  同步使用新名稱
- 改名後仍須驗證 remote Authors／Contributors 只有 `kuotunyu`

### [2026-07-28 18:43 +08:00] CPU preflight — Colab bundle 與 GPU queue 已重驗

- 重新建立 `outputs/formosanlu_colab_bundle.zip`：3,597,778 bytes，
  SHA-256 `25f73183bf2af9285929b97433d2c278f01ee83118feb2b3a1d6d8785c36fefc`
- bundle 綁定 source commit `16ee1ac5d7aed101bc413aaf03afaf1d2ab76d40`，
  不含 Gemma weights，避免把 15.9 GB model 包進 Git／Drive bundle
- extra-seed dry plan 再確認四組 pending，seeds 43/44 的資料 SHA-256
  與各自 primary seed-42 完全一致
- robustness 與真模型 demo dry-run 正確偵測 SafeSynth，沒有啟動 GPU
- 30 分鐘 automation 已同步為既有 Private origin；里程碑全綠後才可
  commit/push，且每次 push 後都要重驗 GitHub Contributors 只有 `kuotunyu`

### [2026-07-28 18:38 +08:00] GitHub repository — Private 首次 push 完成

- 建立 GitHub Private repository（現名 `kuotunyu/FormosaNLU-Synth`），
  default branch `main`
- Description 與 README 已改為正體中文（台灣，`zh-TW`）為主，專有名詞保留原文
- README 20 項 artifact 重算、95 tests、Ruff 與 contributor audit 全綠後 push
- GitHub remote commit authors 與 Contributors API 都只回傳 `kuotunyu`
- 尚未轉 Public；必須等剩餘 GPU 工作、Colab 與 M13 review 完成並取得使用者核可

### [2026-07-28 18:29 +08:00] 剩餘 GPU queue — F7 安全暫停

- F7 在兩次 gate 全綠後啟動，完成並 fsync checkpoint **64/376**
- 執行中偵測到 DefectForge／SafeSynth 新程序，故只停止 FormosaNLU
  `scripts.judge_full`，沒有修改或停止任何 sibling；`gpt-oss:20b` 已卸載
- 同一 F7 命令可由 index 64 後安全續跑；結果 JSONL 與 logs 均為 ignored
- 新增 30 分鐘 heartbeat：連續兩次 free 才續跑，順序為 F7 → M11 real
  evidence → extra seeds 43/44 → robustness；不發佈，里程碑全綠後可推送
  既有 Private origin
- 額外完成 guarded runners、三種子統計器、robustness runner 與 M13
  release preflight；目前全 repo **95 tests passed**

### [2026-07-28 18:10 +08:00] M11/M12 — primary 報告與 demo 完成

- M9 六組 seed-42 訓練與六組全 Test 評估完成；M10 七行主表完整
- filtered synthetic：exact +3.06 points（gap closed 26.4%），slot F1
  +4.40 points（gap closed 46.6%）；仍明確標為單一 seed primary 結果
- 新增 M11 Gradio side-by-side 比較介面；mock 瀏覽器測試、console 與輸出通過
- M12 README、五張可重建圖、資源帳本與 verifier 完成；20 項數字對照通過
- primary core GPU wall-clock 14.440 h；API spend $0
- pending：seeds 43/44 四組、F7 376-row audit、8,922-row robustness、
  真模型 demo/GIF、Colab 一組、M13 發佈

### [2026-07-27 21:30 +08:00] 夜間 GPU 時間放寬 — pipeline 已擴充

- 使用者明示睡眠約八小時，起床後不一定立即用電腦，不必為八小時硬停
- 同一 guard 現在只在六組訓練全完成後，自動接六組 resumable evaluation
- evaluation 全完成後才產生 M10 主表；training / evaluation 任一失敗都會
  停在可續跑狀態，不會把 pending 結果標成完成
- F7 judge、額外 seeds、發佈與 sibling projects 仍不由此入口暗中啟動

### [2026-07-27 21:15 +08:00] M9 過夜總控 — 完成，不占 GPU

- 新增單一 CPU readiness/status 入口，檢查 contributors、工作樹、六組資料、
  Gemma 檔案大小、resume smoke、GPU baseline 與至少 20 GiB 磁碟
- 啟動 guard 固定為 `M9-OVERNIGHT-3760-4090`，避免把 3,760 誤寫成達成
  8,000 gate；六組仍依序執行、完整組跳過、未完整組由 checkpoint 續跑
- 動態狀態寫入 ignored `runs/m9_overnight_status.json`，不污染 Git provenance
- 當時 adapter evaluation 保留獨立 guard；後續已由 D-015 依使用者新授權
  改為訓練成功後自動接續
- 修正 `reports/m9_preflight.md` 既有的 UTF-8 破損文字

### [2026-07-27 18:12 +08:00] M9/M10 CPU 交付物 — 完成，不占 GPU

- 建立 `notebooks/01_sft_student.ipynb`：同一份 `train.py`、22.5 GiB
  preflight、HF Secret、每 120 秒 Drive checkpoint sync、斷線續跑與成功驗證
- deterministic Colab bundle 約 3.5 MB，不含 15.9 GB Gemma 權重；hash/report
  由 clean source commit 產生
- F7 manifest 376/3,760：hard-negative 275 全納入、boundary 51、random 50；
  `judge_full.py` dry plan 顯示 checkpoint 0/376，未載入 gpt-oss
- M10 七行主表產生器完成；目前 zero-shot 列已填，六組 trained rows 正確標 pending
- robustness probe 8,922 筆：2,974 Test × colloquial / lexical / ASR-noise，
  2,974 個 source 皆有三個不同且 slot-grounded 的版本
- README 已先填 M6 漏斗、mode-collapse 負面結果、已知 GPU 時數與正確 CLI

### [2026-07-27 17:30 +08:00] M6 → M9 preflight — 完成，等待資料決策

- M6 raw 11,264/11,264；index 0–11,263、ID 唯一、SHA-256 與 cost session 完整
- frozen F1–F6 最終 3,760（33.38%）；F5 synthetic duplicate 單項移除 4,596
- 9,114 個 F1–F4 survivors 僅 4,044 個 distinct utterances，確認為 mode collapse
- Standard Aug 3,760 筆完成：EDA 2,200、char noise 514、backtranslation 1,046
- 六組 train counts / unique IDs / 60 intents 全通過，三個 equal-N addition 皆為 3,760
- QLoRA 跨程序 resume smoke 從 `checkpoint-1` 接到 step 2；peak 20,646 MiB
- 六組 batch 與 trained-adapter evaluation 都有 dry-plan、resume 與 explicit guard
- 沒有啟動長時間 M9；短 GPU 工作完成後已通知 SafeSynth / DefectForge 解除保留

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
| M4 生成器 + pilot | ✅ 完成且 fixed gate 通過 | 15 分開發 + 14 分 GPU | 500/500；F1–F6 375/500；judge 49/50 | resumable generator、pilot、報告 |
| M5 過濾管線 + 測試 | ✅ 完成且驗證通過 | 約 20 分 + BGE 短測 | thresholds 0.999/0.995/0.650/0.990；漏斗對齊 | F1–F7 程式、BGE archive、funnel |
| M6 全量生成 + 過濾 | ⚠️ 完成但未達產量 gate | 4.073 h generation | 11,264/11,264；F1–F6 3,760（33.38%） | corpus、generation report、mode-collapse 分析 |
| M7 data_card 草稿 | ✅ Full-corpus pre-release 草稿 | — | M6 數字與限制均可追溯 | data card |
| M8 零樣本 baseline | ✅ 完成且驗證通過 | 1.050 h inference + smoke | 2,974/2,974；intent 10.66%；QLoRA peak 20,646 MiB | config、trainer、baseline、adapter smoke |
| M9 訓練批次 | 🟡 啟動準備完成 | 尚未長跑 | 六組 preflight；1→2 step resume；Standard Aug 3,760 | batch/eval CLI、資料、preflight report |

狀態圖例：⬜ 未開始／🔄 進行中／✅ 完成且驗證通過／⚠️ 完成但有問題／🛑 卡住／🚫 不在範圍
