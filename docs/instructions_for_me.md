# instructions_for_me.md — 換你做的事

> **狀態：所有本機 GPU 階段、Colab portability 與 M12 證據均已完成；M13 最終 review 待辦。**
> 這份檔的存在理由：需要離開這台電腦才能做的事（Colab、HF、GitHub），我做不了，只能寫清楚讓你照做。
> 所有「請你做」的步驟都會標上**預期耗時**與**做完怎麼確認成功**。

---

## 目前待辦

<!-- 每次更新時把這一節換成當下真正要你做的事；沒有就寫「無」 -->

**目前不需要你操作。** 本機 primary 六組訓練、六組評估、seeds 43/44
四組 uncertainty runs、M10、M11
介面與五句 real evidence、M12 報告、F7 與 Colab `real_only` portability
run，以及兩組 robustness inference 都已完成。Codex 正在執行最終
release audit；你醒來後只需 review 是否轉 Public／發布 Hugging Face。

---

## 0. 本機 M9 過夜批次

狀態：**primary seed-42 與 seeds 43/44 uncertainty 已完成。** 六組
primary 訓練 6.540 h、六組全 Test 評估 2.777 h；另有四組 extra-seed
訓練／評估。M10 七行主表與三種子摘要已產生。技術報告在
`reports/m9_preflight.md`、`reports/m9_replicate_summary.md` 與
`reports/m10_main_results.md`。

原 primary 入口保留作重現與續跑；正常情況不需再啟動。額外 seeds 使用
新的獨立入口，會先驗證訓練資料 SHA-256 與 sibling/GPU safety gate：

若真的需要手動啟動，請在專案根目錄使用：

```powershell
.\.venv\Scripts\python.exe -m scripts.m9_replicates
```

這是 CPU-only 狀態檢查，不會啟動 GPU。實際 `--execute` 由 Codex 在安全
gate 全綠時處理；中斷後會跳過完整 run，未完成 run 從最新 checkpoint 續跑。

---

## A. Colab 可攜性驗證（M9，只跑一組）

> 因為 D-006 改成「本機 4090 跑全部訓練」，Colab 在這個專案的角色是**驗證 notebook 真的能在別人的機器上跑起來**，不是主力算力。所以只需要跑一組，約 1.5 小時 units。

**狀態：✅ 已完成。** 2026-07-28 使用 G4（NVIDIA RTX PRO 6000
Blackwell）完成 `real_only` seed 42、500 steps；成果已匯入
`results/colab/real_only/seed_42/`，正式比對報告為
`reports/m9_colab_portability.json`。下列步驟保留作重現 SOP。

### A-1. 上傳

1. 在 Google Drive 建立 `MyDrive/sdg-portfolio/FormosaNLU-Synth/`
2. 上傳 `notebooks/01_sft_student.ipynb`
3. 上傳 `outputs/formosanlu_colab_bundle.zip`，改名或解壓都不需要

bundle 約 3.5 MB，已包含程式碼、lockfile、三個 MASSIVE `zh-TW` Parquet
shards，以及六組訓練所需的 synthetic / Standard Aug 資料；**不含**
15.9 GB Gemma 權重。notebook 會用 `HF_TOKEN` 直接下載固定 base model。
實際 byte size、SHA-256 與 source commit 記在 `reports/m9_colab_bundle.json`。

### A-2. 開啟與設定

1. 在 Drive 裡對 `01_sft_student.ipynb` 按右鍵 →「開啟工具」→ Google Colaboratory（**從 Drive 開啟**，不要另外上傳一份，否則存檔會存錯地方）
2. Runtime → Change runtime type → 選 **至少 22.5 GiB 可用顯存**的 GPU。
   L4-class 24 GB 或 A100 可通過；T4 16 GB 會被 notebook preflight 主動拒絕。
3. 左側鑰匙圖示 → Secrets → 確認有 `HF_TOKEN`（並打開該 notebook 的存取開關）
4. **不要**把任何 token 貼進 notebook 儲存格

### A-3. 執行

- 環境與 15.9 GB 模型下載：視 Colab 網路約 15–40 分鐘
- `real_only` seed-42 portability run：預留約 1–1.5 GPU 小時
- compute units：依 Colab 當下方案與硬體費率變動；以介面顯示值為準並截圖留存
- 每 120 秒把 checkpoint 同步到 Drive
- 中途斷線：重新從第一格執行；notebook 會從 Drive 還原
  `runs/real_only/seed_42/checkpoint-*`，同一條 `train.py --resume` 自動續跑

### A-4. 跑完要下載回來的東西

| 檔案 | 放到本機哪裡 |
|---|---|
| Drive 的 `runs/real_only/seed_42/` 整個資料夾 | `results/colab/real_only/seed_42/` |

下載的檔案會落在 Windows 的 `Downloads`。直接跟我說「檔案在 `C:\Users\3Hml\Downloads\xxx.zip`，幫我歸位」，我會自己搬。

### A-5. 怎麼確認成功

最後一格必須顯示 `PORTABILITY RUN PASSED`，且 Drive 目錄同時包含：

- `run_report.json`：`status=completed`、`group=real_only`、`seed=42`
- `adapter/`
- `metrics.jsonl`
- `env.json`
- `config.snapshot.yaml`

下載回本機後會比對 shared config、資料筆數、完成 step 與 validation loss
trajectory；可攜性驗證不要求不同 GPU 的浮點結果逐位元一致。

本次驗證結果：frozen config 與十個 identity fields 均相同，final adapter
可正常讀取；Colab training runtime 1,914.7 秒，peak allocated VRAM
20,646 MiB。兩個 Drive 下載 ZIP 均通過完整性、安全路徑與 secret pattern
檢查。

---

## B. Hugging Face 發佈（M13）

<!-- FILL AT M13 -->

- [ ] 確認 `huggingface-cli` / `hf` 已登入（帳號 `steven0226`）
- [ ] dataset repo：`steven0226/formosa-nlu-synth-v1`
- [ ] model repo：`steven0226/gemma-4-e4b-formosanlu-lora`
- [ ] **轉 public 前我會先給你完整的 card 內容過目**

---

## C. GitHub 發佈（M13）

Repository 已於使用者明確同意後建立：

- [x] repo：`kuotunyu/FormosaNLU-Synth`
- [x] 先建為 **Private**
- [x] Description 與 README 以正體中文（台灣，`zh-TW`）為主
- [x] 首次 push；remote commits 與 GitHub Contributors 都只有 `kuotunyu`
- [x] 完成 extra seeds 與三種子 uncertainty（真模型證據亦已完成）
- [x] 完成 robustness
- [ ] 完成發佈前總驗收並由使用者 review
- [ ] **使用者過目後才轉 Public**

> 提醒：commit 一律不帶 `Co-Authored-By` trailer，GitHub Contributors 只會有 `kuotunyu`。
> push 前先跑 `python scripts/verify_contributors.py`；任何非 `kuotunyu`
> author/committer 或共同作者 trailer 都會直接失敗。

---

## D. 需要你決定 / 花錢的關卡（隨時可能出現）

| 時機 | 我會問你什麼 |
|---|---|
| M0 | 是否 pull Ollama teacher/judge 模型（19GB / 14GB）；`OLLAMA_MODELS` 是否改指 D: 槽 |
| M2 | teacher / judge 選型定案，要你點頭 |
| M4 | pilot 報告，要你點頭才跑全量 |
| M8 | 已完成 Gemma 4 one-step QLoRA smoke 與完整 2,974-row 零樣本 baseline；runtime 已修復 |
| 任何時候 | 需要花錢（例如升級到雲端 API）一律先問 |
