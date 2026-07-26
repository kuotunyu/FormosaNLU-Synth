# Teacher / Judge 選型與授權分析

> **狀態：骨架。內容在 M2 填寫，填完需使用者核可才能進 M3。**
> 方向已由 `docs/DECISIONS.md` 的 **D-002** 定案（本機開放權重），本文件的工作是**把證據補齊、把型號定死、把實測數字放上來**。
> 規則：所有價格、型號、授權條款一律**現查現引**，附網址與查閱日期，不得憑記憶。

---

## 1. 決策摘要

<!-- FILL AT M2: 三句話講完「選了誰、為什麼、什麼情況會改」 -->

| 角色 | 選定模型 | 授權 | 定案日 |
|---|---|---|---|
| Teacher | <!-- FILL --> | | |
| Judge | <!-- FILL --> | | |
| Embedding（F5/F6 用） | <!-- FILL --> | | |
| Student（已定案，D-007） | `google/gemma-4-E4B-it` | Apache-2.0 | 2026-07-27 |

### M2 選型的兩條硬約束

1. **Teacher 必須維持 Qwen 家族。** Student 已定為 Gemma 4（D-007），judge 為 gpt-oss。三個角色分屬三個家族才能形成**跨家族蒸餾**，堵掉「teacher 與 student 同家族，當然有效」的質疑。若 teacher 也選 Gemma 就白費了這個優勢。
2. **查證範圍是「當前世代」，不是鎖死 `qwen3:30b`。** Teacher 只做**推論**，不受「Qwen3.5 系列不建議 4-bit QLoRA」這類量化警告影響，可以放心採用更新世代的 Qwen 開放權重模型。下面 §6 的表格是實測的起點，不是結論。

---

## 2. 核心判準

這份語料**要公開發佈到 Hugging Face**，供任意第三方拿去訓練任意模型。因此判準的權重是：

1. **授權是否允許「輸出被公開發佈並用於訓練他人的模型」** ← 一票否決項
2. 生成品質（JSON 合格率、標籤正確率、繁中台灣在地性）
3. 成本與可重現性
4. 吞吐與工程複雜度

---

## 3. 路線比較

| 路線 | 代表模型 | 價格 | ToS 對「公開發佈蒸餾語料」的態度 | 結論 |
|---|---|---|---|---|
| (a) 封閉模型 API | Gemini Flash-Lite Batch | <!-- FILL AT M2 --> | ⚠️ 見 §4 | **否決** |
| (b) 雲端開放權重 API | Together / Fireworks 上的 Qwen3 大杯、DeepSeek 級 | <!-- FILL AT M2 --> | <!-- FILL AT M2：各家 serving ToS 逐一查證 --> | 保留為升級路徑 |
| (c) 本機開放權重 | Ollama + Qwen3 | **$0** | ✅ Apache-2.0 無限制 | **採用（D-002）** |

---

## 4. Gemini ToS 的問題（已查證）

- **來源**：<https://ai.google.dev/gemini-api/terms>
- **Effective date**：2026-03-23
- **查閱日**：2026-07-27

原文：

> "You may not use the Services to develop models that compete with the Services (e.g., Gemini API or Google AI Studio). You also may not attempt to reverse engineer, extract or replicate any component of the Services"

付費層（Paid Services）另有：

> "Google doesn't use your prompts ... or responses to improve our products"

**判讀**：付費層解決的是「Google 會不會拿我的資料去訓練」，**沒有**解除上面那條對使用者的使用限制。本專案不只是自用微調，而是把整份蒸餾語料公開，讓任意第三方訓練任意模型 —— 落在灰區。作品集專案沒有承擔這種法律不確定性的必要。

<!-- FILL AT M2: 若 M2 複查時條款有更新，在此註記版本差異 -->

---

## 5. 開放權重授權矩陣

| 模型 | 授權 | 輸出可否公開發佈並用於訓練 | 附帶義務 |
|---|---|---|---|
| Qwen3 系列 | Apache-2.0 | ✅ | 保留授權聲明 |
| gpt-oss 系列 | Apache-2.0 | ✅ | 保留授權聲明 |
| **Gemma 4 系列** | **Apache-2.0**（Gemma 4 起改用；舊版 Gemma Terms 的使用限制與向下游傳遞義務已移除，查證日 2026-07-27） | ✅ | 保留授權聲明 |
| Gemma 3 及更早 | Gemma Terms of Use | ⚠️ | 使用限制須向下游傳遞 → 不使用 |
| DeepSeek（權重） | <!-- FILL AT M2 --> | | |
| Llama 系列 | Llama Community License | ⚠️ | 帶 AUP；須標示 "Built with Llama"；衍生模型名稱須含 "Llama" → **本專案排除** |

<!-- FILL AT M2: 每列補上官方授權網址與查閱日 -->

---

## 6. 本機吞吐實測（M2 必做）

用 20 筆真實 seed 樣本實測，不是估算。

| 模型 | `NUM_PARALLEL` | `CONTEXT_LENGTH` | tokens/s（聚合） | VRAM 峰值 | JSON 合格率 | 備註 |
|---|---|---|---|---|---|---|
| `qwen3:30b` | 1 | 4096 | <!-- FILL --> | | | |
| `qwen3:30b` | 4 | 4096 | <!-- FILL --> | | | |
| `qwen3:30b` | 8 | 4096 | <!-- FILL --> | | | |
| `qwen3:14b` | 4 | 4096 | <!-- FILL --> | | | |

**全量時數推估**：<!-- FILL AT M2 -->

**OOM 觀察與退場路徑**：<!-- FILL AT M2 -->

---

## 7. Judge 選型

- **原則**：與 teacher **不同家族**，以降低自我審查偏差（原始計畫的要求）。
- **候選**：`gpt-oss:20b`（Apache-2.0，14 GB，官方稱 16 GB 記憶體可跑）。
- **抽審範圍**：約 10% —— 全部 `hard_negative` 樣本 + 邊界／衝突樣本 + 隨機抽樣（詳見 `docs/DESIGN.md` §6 F7）。
- **不能同時常駐**：19 GB + 14 GB 超過 24 GB，必須序列式執行。

<!-- FILL AT M2: judge 的實測一致性檢查（同一批樣本重跑兩次的一致率） -->

---

## 8. 升級條款

若 M4 pilot 顯示本機 teacher 的 JSON 合格率或標籤正確率低到無法接受，升級路徑是**雲端開放權重 API**（Together / Fireworks），**不是**回頭用封閉模型。

觸發門檻（M2 先訂死，避免事後找理由）：

| 指標 | 門檻 | 實測值 |
|---|---|---|
| JSON 合格率 | <!-- FILL AT M2 --> | <!-- FILL AT M4 --> |
| F1–F3 通過率 | <!-- FILL AT M2 --> | <!-- FILL AT M4 --> |
| judge 判定正確率 | <!-- FILL AT M2 --> | <!-- FILL AT M4 --> |

升級**需使用者另行核可**（要新註冊帳號並儲值）。

---

## 9. 使用者核可

- [ ] 使用者已閱讀並同意本文件的選型
- 核可日期：<!-- FILL -->
- 備註：<!-- FILL -->
