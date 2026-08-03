# README 直式流程與術語降噪設計

**日期：** 2026-08-03  
**狀態：** 已確認  
**範圍：** `README.md` 的敘事精簡、第一張 Mermaid 流程圖與對應驗證；不修改研究資料、模型、設定、結果或 release artifacts。

## 目標

1. 再精簡 README 約 25–40 行，降低重複敘事，但保留核心結果、限制、引用、授權與重現資訊。
2. 將資料產製圖由橫式改為直式，使 GitHub 頁面中的節點與文字不必縮得過小。
3. 讓第一次閱讀的人不需要先理解 F1–F7，仍能知道每一階段在檢查什麼。
4. 保留 F1–F7 作為內部稽核與文件交叉引用代號，維持研究可追溯性。

## 方案選擇

採用「直式主流程＋摺疊代號表」。主圖使用 plain-language labels；F1–F7 不出現在主視覺路徑，只放在圖下的 `<details>` 對照表。

未採用方案：

- **直式圖保留全部 F1–F7：** 可追溯性高，但仍要求讀者先解碼術語。
- **拆成生成圖與過濾圖：** 單圖較簡單，但會增加 README 長度與視覺切換成本。

## 直式資料流程

主圖使用 `flowchart TB`，內容依序為：

1. `MASSIVE zh-TW` frozen 20-shot data 與 `qwen3.6:27b` local teacher。
2. 四種 synthetic data recipes：paraphrase、slot substitution、noise / code-switch、hard negatives。
3. 11,264 筆 generated rows。
4. 格式與語意一致性：JSON schema、合法 labels、slot groundedness、台灣用語。
5. 資料品質與防洩漏：去重／多樣性、排除接近 validation / Test 的內容。
6. 凍結 3,760 筆 preregistered training corpus。
7. 由不同 model family `gpt-oss:20b` 進行獨立抽樣稽核。
8. 公開 3,754 筆 Hugging Face Dataset。

主圖必須直接顯示兩個 corpus 的用途差異：3,760 筆用於正式訓練；3,754 筆是稽核後的公開版本。兩者不得被畫成同一 artifact。

## F1–F7 對照

在主圖後加入預設收合的 `<details>`：

| Audit ID | 對讀者顯示的意義 |
| --- | --- |
| F1 | JSON 與欄位格式正確 |
| F2 | intent 與 slot labels 合法 |
| F3 | slot values 確實出現在句子中 |
| F4 | 語言與台灣用語符合規則 |
| F5 | 去除重複、過近與極端離群樣本 |
| F6 | 排除接近 validation / Test 的內容 |
| F7 | 不同 model family 的獨立品質稽核 |

對照表只服務 traceability，不在主圖重複長篇技術細節；完整 thresholds 仍連到 `docs/DESIGN.md`。

## README 精簡範圍

- 合併「實驗契約」與「方法總覽」附近重複出現的 dataset、model family、Test 與 hardware 敘事。
- 移除主圖後重複解釋每個流程節點的句子，僅保留 3,760／3,754 artifact 邊界。
- 壓縮公開產物後的重複驗證 prose；保留實際連結、匿名驗證結果與最小載入範例。
- 不刪除 headline evidence、完整統計表、limitations、leakage、citation、license、reproduction commands 或 public artifact URLs。
- 第二張 cross-family paired experiment 圖維持不變，因其目前的直式層級與可讀性已足夠。

## 視覺與相容性

- Mermaid 採高對比淺色底、深色文字；每個 `classDef` 明確設定 `color:`。
- 節點標籤優先使用讀者語言，model names、metrics 與 protocol names 保留原文。
- GitHub public README 是權威渲染面；本機 Mermaid CLI 先驗證 syntax，再實際檢查 GitHub render。
- 主圖控制在單一路徑與一個發布分支，不增加互動或額外圖片資產。

## 驗證與回歸保護

- 更新 `scripts.verify_readme.readme_diagram_checks`，要求第一張圖為 `flowchart TB`，並檢查 plain-language stage markers 與 F1–F7 摺疊對照。
- 先新增／更新 focused tests 並確認 RED，再修改 README／verifier使其 GREEN。
- 驗證兩張 Mermaid 均可由 Mermaid CLI 渲染，且 GitHub 公開頁面無 syntax error、broken images 或缺失章節。
- 執行完整 gate suite：Ruff、pytest、README traceability、sole contributor、reproduction commands、closeout metadata。
- `interview.md` 必須持續未追蹤；GitHub Contributors 必須只有 `kuotunyu`；`v1.2.1` tag 不得變動。

## 非目標

- 不重算、改寫或挑選研究結果。
- 不修改 frozen data、filter thresholds、prompts、models、seeds、training config 或 evaluation contract。
- 不建立新 release、不改 DOI、不重新發布 Hugging Face artifacts。
- 不修改第二張 Mermaid 的研究邏輯。

## 成功條件

1. README 比目前 660 行再減少約 25–40 行。
2. 第一張 Mermaid 在 GitHub 上為清楚的直式流程，主圖不顯示 F1–F7。
3. 新讀者可由節點直接理解檢查內容；研究讀者可從摺疊表查回 F1–F7。
4. 3,760 training corpus 與 3,754 public Dataset 的差異不再依賴圖外推理。
5. 完整 gates、公開 render、作者與 Contributors 稽核全部通過。
