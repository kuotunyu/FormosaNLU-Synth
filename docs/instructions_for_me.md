# instructions_for_me.md — 換你做的事

> **狀態：v1.2.0 已發布，專案完成。**
> 這份檔保留已完成的 Colab、Hugging Face 與 GitHub 操作紀錄，供未來重現；
> 目前沒有需要使用者執行的步驟。
> 所有「請你做」的步驟都會標上**預期耗時**與**做完怎麼確認成功**。

---

## 目前待辦

<!-- 每次更新時把這一節換成當下真正要你做的事；沒有就寫「無」 -->

**無。v1.2.0 已於 2026-08-03 完成發布。**

| 動作 | 結果 |
|---|---|
| M19 五組 equal-N ablation | ✅ 五組各 500 steps + 2,974-row strict evaluation |
| Annotated tag `v1.2.0` | ✅ 指向 `07493cacb26dea5daaa03aafdbc1497b12678405`，tagger `kuotunyu` |
| GitHub Release | ✅ [v1.2.0](https://github.com/kuotunyu/FormosaNLU-Synth/releases/tag/v1.2.0)，非 draft、非 prerelease |
| Release preflight | ✅ `public_verified`，blocking 為空 |
| Hugging Face artifacts | ✅ 刻意不變；Dataset 仍 3,754 rows、Gemma adapter SHA 未變 |
| Contributors | ✅ GitHub API 複驗只有 `kuotunyu` |

v1.2.0 是研究證據版本，不是 Dataset／Model artifact 版本，因此不需要重新上傳
Hugging Face。M19 的 single-seed negative result、2.5-point detectability threshold
與 no-causal-claim 限制均已公開。

以下 v1.1.0 表格保留作歷史紀錄：

三件動作在使用者明確授權後由 agent 代為執行，執行前後皆有驗證：

| 動作 | 結果 |
|---|---|
| Annotated tag `v1.1.0` | ✅ 指向 `2f2d69b`，tagger `kuotunyu` |
| GitHub Release | ✅ [v1.1.0](https://github.com/kuotunyu/FormosaNLU-Synth/releases/tag/v1.1.0)，非 draft |
| HF dataset card | ✅ commit `dd6f3994` |
| HF model card | ✅ commit `d9b6d010` |
| 發佈後匿名驗證 | ✅ `public_verified`；dataset 仍 3,754 rows、adapter SHA `f70f4238…` 未變 |
| Contributors 複驗 | ✅ 仍只有 `kuotunyu` |

未來若要建立新版本，仍需先取得使用者明確授權，並在發布前通過完整本機 gates。

> ⚠️ 一個已知的小瑕疵：清理 release notes 的 commit（`a5926ad`）在建 tag 之後，
> 所以 `v1.1.0` 標記的 tree 裡，那份文件的開頭仍有「草稿」字樣。程式碼、結果與
> 報告完全相同，Release 頁面用的是清理後的內容。**已發佈的 tag 不移動**——移動
> 公開 tag 比這個瑕疵更糟。

---

## 已完成的發佈步驟（保留作重現 SOP）

前置條件：`python -m scripts.check_gates` 全綠。

### 1. 建 v1.1.0 annotated tag（約 1 分鐘）

```powershell
git tag -a v1.1.0 -m "v1.1.0: cross-family replication and robustness backfill"
git push origin v1.1.0
```

確認成功：`git show v1.1.0 | head -5` 的 Tagger 是 `kuotunyu`。

### 2. 發 GitHub Release（約 3 分鐘）

內容直接用 [`docs/RELEASE_NOTES_v1.1.0.md`](RELEASE_NOTES_v1.1.0.md)。

確認成功：Release 頁面指向 `v1.1.0` tag；Contributors API 仍只有 `kuotunyu`。

### 3. 上傳兩張 Hugging Face card（約 5 分鐘）

- `hf_cards/dataset_README.md` → `steven0226/formosa-nlu-synth-v1`
- `hf_cards/model_README.md` → `steven0226/gemma-4-e4b-formosanlu-lora`

**只更新 card，不動資料與權重**——dataset 仍是 3,754 rows、adapter 的
SHA-256 未變，v1.1.0 是證據版本而非資料版本。

確認成功：兩個 HF 頁面顯示新的跨 family 段落；Dataset Viewer 仍正常。

README 維持使用者指定的正體中文（台灣，`zh-TW`）為主，專有名詞直接使用原文。

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

- [x] `hf auth whoami`：帳號 `steven0226`
- [x] Public dataset：[`steven0226/formosa-nlu-synth-v1`](https://huggingface.co/datasets/steven0226/formosa-nlu-synth-v1)
- [x] Public model：[`steven0226/gemma-4-e4b-formosanlu-lora`](https://huggingface.co/steven0226/gemma-4-e4b-formosanlu-lora)
- [x] 先建立 Private、逐檔回下載比對，再依使用者明確授權轉 Public
- [x] 匿名 Dataset 載入、Dataset Viewer、PEFT config、adapter SHA-256 通過

---

## C. GitHub 發佈（M13）

Repository 已於使用者明確同意後建立：

- [x] repo：`kuotunyu/FormosaNLU-Synth`
- [x] 先建為 **Private**
- [x] Description 與 README 以正體中文（台灣，`zh-TW`）為主
- [x] 首次 push；remote commits 與 GitHub Contributors 都只有 `kuotunyu`
- [x] 完成 extra seeds 與三種子 uncertainty（真模型證據亦已完成）
- [x] 完成 robustness
- [x] 完成發佈前總驗收並取得使用者明確公開授權
- [x] GitHub 轉 Public

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
