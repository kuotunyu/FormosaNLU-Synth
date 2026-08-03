# FormosaNLU README Mermaid Distillation

## 1. 目標

在不削弱研究證據的前提下，讓第一次進入 GitHub repository 的讀者更快理解兩件事：

1. synthetic data 如何從 frozen real data 經 generation、filtering 變成訓練與公開產物；
2. 專案如何透過 paired arms、三個 seeds 與兩個 student model families 驗證結果。

README 需比目前版本再短一點，但所有 headline numbers、研究限制、公開產物、重現命令與 citation 仍必須可追溯。

## 2. 資訊架構

採用兩張 GitHub 原生 Mermaid flowchart，各自只回答一個問題。

### 2.1 資料產製與品質控管

顯示以下實際 code path：

`MASSIVE zh-TW` frozen split → 四種 generation recipes + `qwen3.6:27b` local teacher → 11,264 generated rows → F1–F4 deterministic filters → F5–F6 semantic filters。

F5–F6 之後分成兩個 artifact boundary：

- 3,760-row frozen primary corpus，供 preregistered training contract 使用；
- 經 F7 `gpt-oss:20b` independent audit 後的 3,754-row public Dataset。

這個分支必須明確呈現，避免把 F7 release-only corpus 誤解成 primary training corpus。

### 2.2 成對實驗與跨模型驗證

顯示一份 frozen data/config/prompt/evaluation contract 同時餵入：

- Gemma 4：`real_only` 與 `real_syn_filtered` × seeds 42/43/44；
- Phi-4-mini：相同兩個 arms × 相同三個 seeds。

每個 family 都在未修改的 2,974-row MASSIVE `zh-TW` Test 上做 strict evaluation，再進行 hierarchical paired bootstrap、McNemar + Holm，最後套用 preregistered cross-family criterion。

## 3. README 精簡原則

- 保留 hero、公開產物、headline evidence、三種子結果、cross-family replication、limitations、citation 與 licenses。
- 合併重複說明；同一項硬體、完成狀態或 reproducibility boundary 只說一次。
- Generation recipes 的逐列說明改由 Mermaid + `docs/DESIGN.md` 承接。
- 既有 `assets/m12_pipeline.png` 改放在 collapsed `<details>` 中，保留 publication figure 與 verifier coverage，但不再與主要流程圖競爭。
- 低頻細節繼續使用 `<details>`；不把核心三種子結果或 cross-family verdict 隱藏。
- 主要語言為正體中文（台灣），model、metric、pipeline、filter、seed 等專有名詞維持原文。

## 4. Mermaid 視覺規格

- 每張圖不超過 12 個 nodes；不用 emoji、圖示字型或外部圖片。
- 使用簡短、行動導向 labels，詳細數字只保留能界定 artifact 或 evaluation contract 的部分。
- 使用高對比、同義一致的四組色彩：source、process、gate、artifact/evidence。
- 每個 `classDef` 都必須明確包含 `color:`，兼顧 GitHub light/dark themes。
- Mermaid source 必須能由 repository verifier 檢查，並以 GitHub 公開頁面實際渲染驗收。

## 5. 不變邊界

- 不修改任何 Dataset rows、model artifacts、prompt、parser、threshold、seed、training config、evaluation contract 或 report numbers。
- 不重跑 generation、training 或 evaluation。
- 不修改 GitHub Release、Hugging Face、Zenodo、DOI 或 `v1.2.1` tag。
- `interview.md` 維持 untracked/excluded，絕不進入 Git。
- Git author/committer 只能是 `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`，不得有 `Co-Authored-By`；GitHub Contributors 只能有 `kuotunyu`。

## 6. 驗收標準

1. README 恰有兩個 Mermaid diagrams，分別覆蓋資料 pipeline 與 evidence design。
2. `scripts.verify_readme` 會拒絕缺圖、圖數錯誤或關鍵流程 marker 缺失的 README。
3. `assets/m12_pipeline.png` 仍可從 README 存取，但預設不展開。
4. README 比目前 686 行更短，且沒有移除 machine-checked evidence。
5. Ruff、完整 pytest、README、contributors、reproduce、closeout gates 全綠。
6. GitHub 公開頁面能正確渲染兩張 Mermaid、所有 badges/images/links，且 Contributors 仍只有 `kuotunyu`。
