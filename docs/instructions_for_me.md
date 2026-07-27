# instructions_for_me.md — 換你做的事

> **狀態：骨架。** 每次需要你動手時，我會把對應章節填實並在對話裡指給你看。
> 這份檔的存在理由：需要離開這台電腦才能做的事（Colab、HF、GitHub），我做不了，只能寫清楚讓你照做。
> 所有「請你做」的步驟都會標上**預期耗時**與**做完怎麼確認成功**。

---

## 目前待辦

<!-- 每次更新時把這一節換成當下真正要你做的事；沒有就寫「無」 -->

**無。** 目前所有工作都在本機，不需要你動手。

---

## A. Colab 可攜性驗證（M9，只跑一組）

> 因為 D-006 改成「本機 4090 跑全部訓練」，Colab 在這個專案的角色是**驗證 notebook 真的能在別人的機器上跑起來**，不是主力算力。所以只需要跑一組，約 1.5 小時 units。

### A-1. 上傳

1. 把 `notebooks/` 整個資料夾複製到 Google Drive 的 `MyDrive/sdg-portfolio/03-formosanlu-sdg/`
2. 一併複製 `<FILL AT M9: 需要的資料檔清單與大小>`

### A-2. 開啟與設定

1. 在 Drive 裡對 `01_sft_student.ipynb` 按右鍵 →「開啟工具」→ Google Colaboratory（**從 Drive 開啟**，不要另外上傳一份，否則存檔會存錯地方）
2. Runtime → Change runtime type → **`<FILL AT M9: 建議 runtime 與 fallback 規則>`**
3. 左側鑰匙圖示 → Secrets → 確認有 `HF_TOKEN`（並打開該 notebook 的存取開關）
4. **不要**把任何 token 貼進 notebook 儲存格

### A-3. 執行

- 預估時數：`<FILL AT M9>`
- 預估 compute units：`<FILL AT M9>`
- 中途斷線怎麼辦：`<FILL AT M9: resume 步驟>`

### A-4. 跑完要下載回來的東西

| 檔案 | 放到本機哪裡 |
|---|---|
| `<FILL AT M9>` | `results/colab/<group>/` |

下載的檔案會落在 Windows 的 `Downloads`。直接跟我說「檔案在 `C:\Users\3Hml\Downloads\xxx.zip`，幫我歸位」，我會自己搬。

### A-5. 怎麼確認成功

`<FILL AT M9: 例如「metrics.jsonl 的最後一行 Val exact match 與本機同組相差在 X 以內」>`

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
