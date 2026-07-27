# instructions_for_me.md — 換你做的事

> **狀態：M9 本機與 Colab 操作已填實；M13 發佈章節仍待最終結果。**
> 這份檔的存在理由：需要離開這台電腦才能做的事（Colab、HF、GitHub），我做不了，只能寫清楚讓你照做。
> 所有「請你做」的步驟都會標上**預期耗時**與**做完怎麼確認成功**。

---

## 目前待辦

<!-- 每次更新時把這一節換成當下真正要你做的事；沒有就寫「無」 -->

**不用操作電腦，但需要做一個決定：**

1. 建議：用固定門檻實得的 3,760 筆 filtered corpus 照實跑 M9；
2. 或先修訂 generation design，再另開一次正式生成（會延後 M9，且本次結果仍保留）。

選好後，睡前只要在對話裡說「開始跑 M9」；我會先檢查另外兩個專案與 GPU，
再啟動可續跑的六組批次。你不需要自己輸入 PowerShell 指令。

---

## 0. 本機 M9 過夜批次

準備狀態：六組資料、Standard Aug、dry plan、checkpoint 續跑與 evaluation
入口均已驗證。技術報告在 `reports/m9_preflight.md`。

若真的需要手動啟動，請在專案根目錄使用：

```powershell
.\.venv\Scripts\python.exe -m scripts.train_all --execute --confirm M9-LOCAL-4090
```

正常情況不需要你做這一步；由我協調其他專案並啟動較安全。中斷後重跑同一命令
會跳過完整 run，未完成 run 會從最新 checkpoint 接續。

---

## A. Colab 可攜性驗證（M9，只跑一組）

> 因為 D-006 改成「本機 4090 跑全部訓練」，Colab 在這個專案的角色是**驗證 notebook 真的能在別人的機器上跑起來**，不是主力算力。所以只需要跑一組，約 1.5 小時 units。

### A-1. 上傳

1. 在 Google Drive 建立 `MyDrive/sdg-portfolio/03-formosanlu-sdg/`
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

---

## B. Hugging Face 發佈（M13）

<!-- FILL AT M13 -->

- [ ] 確認 `huggingface-cli` / `hf` 已登入（帳號 `steven0226`）
- [ ] dataset repo：`steven0226/formosa-nlu-synth-v1`
- [ ] model repo：`steven0226/gemma-4-e4b-formosanlu-lora`
- [ ] **轉 public 前我會先給你完整的 card 內容過目**

---

## C. GitHub 發佈（M13）

<!-- FILL AT M13 -->

依 D-005，整個 Phase 1 + Phase 2 都不建 remote，到這一步才建：

- [ ] repo 名稱：`kuotunyu/03-formosanlu-sdg`（先建 **private**）
- [ ] 通過發佈前總驗收
- [ ] **你過目後才轉 public**

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
