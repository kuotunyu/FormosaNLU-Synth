# M5 Filtering Status

> 狀態：程式與測試已完成；F1–F4、F7 已在 500 筆 pilot 實跑；F5/F6
> production calibration 因大型 embedding 權重未獲夜間下載授權而暫停。

## 已完成

- F1：Pydantic schema，能把純結構錯誤與 unknown-label 錯誤分到正確關卡。
- F2：凍結 60/55 labels，並重算 sample labels 是否等於 code-authored
  generation plan，避免 teacher 悄悄換 slot。
- F3：共用 `src/data/normalize.py`，要求所有 slot 有不重疊的 normalized span。
- F4：繁簡殘留、大陸用語、非預期 script 與 Latin ratio；noise recipe 有明確但
  有限的 code-switch 放寬。
- F5：L2 normalize、seed-too-close、synthetic duplicate、seed outlier 的
  vectorized cosine 決策；只跟先前 accepted synthetic 比，決定可重現。
- F6：Val/Test nearest-neighbor exclusion 與 auditable log schema
  （sample id、similarity、matched eval id、split）；只排除，不挑選。
- F7：固定 50 筆、hard-negative 優先的跨家族 judge 抽樣，實跑 50/50
  structured verdict。
- 每筆只寫第一個 reject reason；F1–F4 真實漏斗
  `437 + 63 = 500`。

全專案測試目前 36 passed；每一關都有 pass/fail 案例。Ruff 與
`git diff --check` 通過。

## 尚未完成：BGE-M3 production calibration

D-010 選定 `BAAI/bge-m3`，但其官方 Hugging Face tree 顯示單一 PyTorch
權重約 2.27GB，整個 repo 約 4.59GB：
[BAAI/bge-m3 files](https://huggingface.co/BAAI/bge-m3/tree/main)。

`docs/AUTONOMOUS_RUN.md` 的夜間預授權模型清單只有 teacher、judge 與 student，
沒有 embedding model；硬性禁止又要求不得下載清單外模型。因此本輪：

- 沒有下載 BGE-M3；
- `configs/filtering.yaml` 的四個 threshold 保持 `null`；
- 沒有以 TF-IDF 或小模型數字冒充 BGE-M3；
- 沒有畫不存在的相似度分布圖；
- 沒有宣稱 F1–F6 gate 通過。

程式的 `BgeM3Backend` 預設 `local_files_only=True`，所以權重未就緒時會保守
失敗而不是在背景偷下載。使用者若核可約 2.27GB 的指定權重下載，下一步是：

1. 安裝並鎖定 `sentence-transformers`／PyTorch runtime；
2. 只下載 BGE-M3 dense inference 必要檔案；
3. 對 pilot、1,176 train seeds、validation/test 分批 embedding；
4. 產出三組 nearest-cosine 分布與圖；
5. 人工開圖後才把四個 threshold 從 `null` 改成數字；
6. 重跑 F5/F6，完成最終漏斗與 M4 gate。

