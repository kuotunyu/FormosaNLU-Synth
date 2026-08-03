# FormosaNLU README Redesign

## 1. 目的

重整公開 `README.md`，讓第一次進入 GitHub 的訪客能在十秒內理解：

1. FormosaNLU 解決什麼問題；
2. synthetic data 帶來多少可量化改善；
3. 結果已在第二個 student model family 複製；
4. Dataset、Model、報告與 DOI 都可直接取得。

README 以正體中文（台灣）為主，技術專有名詞保留原文。這次只改善敘事、
資訊層級與 GitHub 顯示，不修改任何研究結果或公開 artifact。

## 2. 現況問題

- 標題過長，且把語言地區資訊放在最醒目的位置，反而弱化專案主題。
- DOI badge 在 GitHub 顯示為破圖，造成第一印象不穩定。
- 首屏以內部 milestone 名稱組成的長篇「目前狀態」開場，閱讀成本高。
- 最有說服力的 Gemma、Phi 跨 family 結果和公開 artifacts 出現得太晚。
- 多處重複交代完成狀態、實驗設定與結論，讓 686 行 README 顯得比必要更長。
- 完整 evidence 很有價值，不適合為追求短小而大量刪除。

## 3. 採用方案

採「首屏大幅重整、全文小幅精簡」：

- 前兩個畫面重寫為清楚的 project pitch、核心數字、主結果圖與公開 artifacts。
- 刪除重複的完成狀態與內部 milestone 清單。
- 保留完整研究 evidence、negative result、limitations、licenses 與 reproducibility。
- 將低頻但必要的細節放入 `<details>`，提供 progressive disclosure。
- 不把 README 縮成只有 marketing 摘要，也不把關鍵 evidence 全數搬走。

## 4. 首屏資訊架構

### 4.1 標題與一句話定位

標題改為：

`FormosaNLU — Synthetic Data Distillation for Low-resource NLU`

副標以一到兩句正體中文說明：使用本機 open-weight teacher 生成與過濾
synthetic data，並在 20-shot MASSIVE NLU 上，以兩個 student model families
驗證是否改善 intent classification、slot filling 與 strict JSON output。

「正體中文（台灣）」不再出現在標題或被粗體強調，只在 Dataset／任務脈絡中
自然說明 MASSIVE `zh-TW`。

### 4.2 穩定 badge 列

以 Shields.io 或純文字連結取代目前的 Zenodo 動態 SVG badge，避免 GitHub
proxy/cache 造成破圖。Badge 列只保留有決策價值的入口：

- GitHub Release `v1.2.1`
- Hugging Face Dataset
- Hugging Face Model
- DOI `10.5281/zenodo.21767493`
- MIT License

DOI badge 必須仍連到 `https://doi.org/10.5281/zenodo.21767493`，並同步更新
closeout verifier 對 badge markup 的期待；不更動 DOI 本身。

### 4.3 核心證據

在首屏直接呈現三項可掃讀證據：

- Gemma 三 seeds：intent exact match `+4.14 pp`、joint exact match `+3.86 pp`；
- Phi-4-mini replication：intent exact match `+5.09 pp`、joint exact match
  `+4.71 pp`；
- `11,264` generated → `3,760` frozen primary，單張 RTX 4090、`$0` API cost。

數字後立即顯示現有 `assets/m12_main_results.png`，讓訪客先看到結論，再自行
深入方法與完整表格。

### 4.4 公開產物

將 Dataset、Gemma LoRA adapter、GitHub Release、Zenodo DOI／record 整理為
四個明確入口。狀態只保留一行：專案已完成、公開 artifacts 已通過匿名下載與
hash 驗證。

## 5. 全文重整

README 依下列順序重排：

1. Hero：定位、badges、核心證據、主結果圖；
2. 公開產物；
3. 任務與實際 model output；
4. 實驗結果與 cross-family replication；
5. filtering、robustness 與 M19 negative result；
6. 方法與資料流程；
7. reproduction；
8. leakage、limitations、licenses、citation 與延伸文件。

精簡規則：

- 相同事實只在最合適的位置說一次；
- milestone code（M9、M15、M19）可作 evidence locator，但不作首屏主敘事；
- 每段先寫結論，再放方法或限制；
- 保留所有會影響研究判讀的數字與 caveat；
- 長篇 per-intent、環境與指令細節可摺疊，但不可讓 verifier 失去 evidence；
- 不新增未由 tracked report 支持的 performance、causal 或泛化主張。

## 6. 不變範圍

- 不修改 Dataset rows、model tensors、frozen corpus、prompt、parser、threshold、
  seeds、train config、evaluation contract 或任何 report 數字。
- 不重新執行 generation、training 或 evaluation。
- 不移動或重建 `v1.2.1` tag。
- 不修改 Hugging Face artifacts 或 Zenodo record。
- 私有 `interview.md` 保持 untracked／excluded，絕不加入 Git。
- Git author/committer 僅能是
  `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`，不得加入
  `Co-Authored-By`；GitHub Contributors 必須仍只有 `kuotunyu`。

## 7. 驗證方式

1. 檢查 Markdown hierarchy、連結與圖片路徑；
2. 執行 README verifier 與 closeout verifier，必要時只調整 verifier 的呈現層
   expectation；
3. 執行完整 gate suite：Ruff、pytest、README、contributors、reproduce、
   closeout；
4. 以 GitHub-compatible render 檢查首屏、badge、表格、`<details>` 與圖片；
5. 檢查 diff 僅包含 README redesign、對應 verifier/test 與設計／計畫文件；
6. commit/push 後確認 commit author、committer 與 Contributors 都只有
   `kuotunyu`，再確認 GitHub README 的 DOI badge 不再破圖。

## 8. 驗收標準

- 第一次訪客在首屏即可理解問題、方法、兩個 model families 的結果與公開入口；
- 標題不再特別強調「正體中文（台灣）」；
- DOI 入口在 GitHub 正常顯示且可點擊；
- README 比目前更短、重複更少，但研究 caveat 與完整 evidence 仍可取得；
- 所有既有數值 verifier 與完整 gates 通過；
- 公開 artifact hashes、release tag 與遠端內容不變；
- GitHub Contributors 仍只有 `kuotunyu`。
