# DESIGN_PHASE2.md — 微調 / 評測 / Demo / 發佈 技術設計

> 適用範圍：**M8–M13**。Phase 1（資料管線）的設計在 `docs/DESIGN.md`。
> 指標定義已在 `docs/DESIGN.md` §11 凍結，本文件**不重新定義**，只描述實作。
> 這份文件是實作依據。發現行不通就改這份文件並在 `docs/DECISIONS.md` 記一筆，不要默默偏離。

---

## 0. 與原始 Phase 2 prompt 的差異（四處，全部有意為之）

| # | 原始 prompt | 本專案採用 | 理由 |
|---|---|---|---|
| 1 | **四組**（Real-only／+Unfiltered／+Filtered／Full-real） | **六組訓練 + 零樣本 = 主表七行** | prompt 漏了實驗鐵律要求的 `+Standard Aug`（關鍵消融）；再加 D-004 的等量對照與 D-007 的零樣本 baseline |
| 2 | `Real-only(1,200)` | 以 `splits/manifest.json` 的**真實筆數**為準 | R-5：MASSIVE 各 intent 數量不均，抽樣是 `min(20, available)`，總數低於 1,200 |
| 3 | 成本總帳「API 總共花 $X、每筆 accepted 樣本 $Y」 | **「API $0；GPU wall-clock N 小時 + 估算電費 + 等值 API 成本對照」** | D-002 走本機開放權重 teacher |
| 4 | 「vLLM 或 transformers」；`notebooks/01_sft_qwen.ipynb` | **transformers**；檔名 `notebooks/01_sft_student.ipynb` | vLLM 是 Linux-only（D-001）；student 已非 Qwen（D-007） |

另：prompt 寫 `scripts/eval.py`，既有骨架是 `src/evaluation/`。**折衷**——邏輯放 `src/evaluation/`，`scripts/eval.py` 當薄的 CLI 入口。

---

## 1. Student 與輸出契約

| 項目 | 值 |
|---|---|
| Base model | **`google/gemma-4-E4B-it`** |
| 授權 | Apache-2.0 |
| 規格 | 4.5B 總參數／2.3B effective（Per-Layer Embeddings）、128K context、多模態輸入（本專案只用文字） |
| 微調方式 | 4-bit QLoRA |
| 家族關係 | teacher = Qwen3（本機 Ollama）／student = Gemma 4／judge = gpt-oss → **三家族、全 Apache-2.0、跨家族蒸餾** |

### 輸出契約

訓練與推論兩端使用**完全相同**的 prompt 模板與 chat template（模板存 `src/training/prompt_template.py`，帶版本號）。目標輸出是單一 JSON 物件，無 markdown 圍欄、無前後說明文字：

```json
{"intent": "<intent>", "slots": [{"type": "<slot_type>", "value": "<value>"}]}
```

**設計約束：**

1. **評測時不得使用 constrained decoding / JSON grammar。** `JSON-valid rate` 是要報告的指標之一，強制合法會讓它恆等於 100% 而失去意義。訓練讓模型學會輸出 JSON，評測就誠實地量它學會了多少。
2. Label set 不寫進 prompt（60 intents × 55 slot types 太長且會變成 few-shot 洩題）；模型要從訓練資料學會 label 空間。**零樣本 baseline 例外**——它沒被訓練過，必須在 prompt 裡給 label 清單，這個差異要在主表註明。
3. 生成長度上限固定（依 M8 實測的 JSON 長度分布設定），超長即視為 JSON-invalid。
4. Greedy decoding（`do_sample=False`），確保可重現。

### VRAM 注意事項（M8 實測項）

Gemma 4 E4B 是多模態模型。本專案只用文字，**要確認能否只載入語言塔、跳過 vision/audio towers**以省 VRAM。若 transformers 沒提供乾淨的做法就照常載入並記錄實際佔用——E4B LoRA 官方稱需約 17GB，QLoRA 更低，24GB 有餘裕，這不是阻塞項。

---

## 2. 訓練設計

### 2.1 超參策略

實際數值在 **M8 上網查證當前建議後定案**（規則：套件版本、模型名稱、超參一律先查證）。以下是需要被定死並記錄的**契約**，不是拍板的數值：

| 項目 | 契約 |
|---|---|
| 量化 | `load_in_4bit=True`（NF4 + double quant） |
| Optimizer | `adamw_8bit`（省約 2GB VRAM） |
| LoRA | rank / alpha / dropout / `target_modules` —— M8 定案後寫進 `configs/train.yaml`，**六組完全一致** |
| LR / scheduler / warmup | M8 定案，**六組完全一致** |
| Batch | `per_device_train_batch_size` × `gradient_accumulation_steps` = **固定的 effective batch size**，六組一致 |
| 精度 | bf16 |
| Seq length | 依 M8 量測的長度分布設定，六組一致 |

**所有超參只准調一次（M8），之後六組共用。** 任何一組單獨調參都會讓對照失效。

### 2.2 Optimizer steps 對齊（實驗鐵律的核心要求）

各組資料量差異極大（`real_only` 約 1.1k ↔ `full_real` 11,514），因此採 **compute-matched** 設計：

1. **固定 `max_steps = S`**（六組相同，S 在 M8 定案），固定 effective batch size。
2. 每 `eval_steps` 在**真實 Val**（只用真實資料）上評測，**六組使用完全相同的評測協定與 Val 子集**。
3. **以 Val 上的主指標選最佳 checkpoint**（early stopping / best-checkpoint selection）。小資料組（`real_only`）會在早期就過擬合，這由 Val 選點處理，是預期行為不是 bug。
4. 主表**必須同時報告**三個數字，否則對照不誠實：
   - 最佳 checkpoint 的 step 數
   - 該點對應的 epoch 數
   - **真實樣本曝光次數**（該組看過真實樣本幾遍）

### 2.3 目錄契約與斷點續跑

```
runs/<group>/seed_<n>/
├── adapter/                 # 最佳 checkpoint 的 LoRA adapter
├── checkpoints/             # 中途 checkpoint（供 resume）
├── trainer_state.json
├── metrics.jsonl            # 每次 eval 的原始數字（主表一律從這裡重算）
├── config.snapshot.yaml     # 該次 run 的完整超參快照
└── env.json                 # 套件版本、GPU、driver、commit hash
```

- **每個 run 一個唯一目錄**，不共用、不覆蓋。
- **必須支援斷點續跑**（`resume_from_checkpoint`）。本機是 5–8 小時的過夜批次，中斷是常態不是例外。
- `metrics.jsonl` 是唯一真相來源。README 的每個數字都要能從它重算，**不准抄畫面**。

### 2.4 六組 → run 對應

| Group id | 訓練資料 | 資料量 | 用途 |
|---|---|---|---|
| `real_only` | 20-shot 真實 | 見 manifest | 基準線（下限） |
| `real_std_aug` | 20-shot 真實 + 傳統文字增強 | ＝ filtered N | 關鍵消融：排除「一般增強就夠」 |
| `real_syn_unfiltered_full` | 20-shot 真實 + 未過濾合成（全量） | 全部生成量 | 不過濾的實際影響 |
| `real_syn_unfiltered_eqn` | 20-shot 真實 + 未過濾合成（下採樣） | ＝ filtered N | 隔離「品質 vs 數量」 |
| `real_syn_filtered` | 20-shot 真實 + 過濾後合成 | 8–10k | **主成果組** |
| `full_real` | 完整 MASSIVE train | 11,514 | 上限參照 |

Seed 策略：六組先各跑 1 seed；`real_only` 與最佳 filtered 組補到 3 seeds 報 mean±std。合計約 **10 runs**。

---

## 3. 零樣本 baseline（主表第一行 + M8 閘門）

未微調的 `gemma-4-E4B-it` 直接 prompt 跑真實 Test。

**兩個用途：**

1. **主表第一行** —— 證明「微調本身有價值」。沒有這行，所有訓練組的數字都缺一個下界參照。
2. **M8 的閘門（對應 R-9）** —— Gemma 在繁中的底子大概率不如 Qwen。若零樣本結果顯示 JSON 完全不成形、或 intent accuracy 接近亂猜（1/60 ≈ 1.7%）到無法作為起點，**停下來回報使用者**，並考慮換回 `Qwen3-4B-Instruct-2507`。

**注意**：零樣本必須在 prompt 裡提供 label 清單（模型沒被訓練過，不可能猜到 60 個 intent 的字串），這與訓練組的 prompt 不同，**主表要明確註明這個差異**，不能假裝條件一致。

---

## 4. 本機 / Colab 分工（D-006）

| 項目 | 安排 |
|---|---|
| 主力 | **本機 4090 跑全部 10 runs**，序列執行，估 5–8 小時，過夜批次 |
| 入口 | `scripts/train_all.py`（依序跑六組 + 補 seed，每組獨立 run 目錄，可中斷續跑） |
| Colab 交付物 | `notebooks/01_sft_student.ipynb` —— **包裝同一份 `src/training/train.py`**，不是另寫一套 |
| Colab 實跑 | 只跑**一組**驗證可攜性（約 1.5h units），產出放 `results/colab/` 與本機同組結果比對 |
| 為什麼 | 4090 對此級 QLoRA 約為 L4 的 2.5–3.5 倍；Colab 100 units/月 要留給專案一、二；且「全流程單張 4090 可重現」是更強的敘事 |

Colab 端仍遵守既有鐵則：資料解壓到 `/content/data` 再訓練、checkpoint 定期同步 Drive、支援續跑、唯一輸出目錄、token 只放 Secrets。詳細操作步驟寫在 `docs/instructions_for_me.md`。

---

## 5. 評測設計

### 5.1 架構

```
src/evaluation/
├── run_adapter.py      # 可續跑 adapter 推論（transformers，左側 padding，greedy）
├── eval_all.py         # 六組序列評測 plan / resume / batch report
├── parse.py            # 解析模型輸出 → SyntheticSample schema；解析失敗即 JSON-invalid
├── metrics.py          # 指標實作，正規化沿用 src/data/normalize.py（與過濾 F3 同一份）
├── probe.py            # robustness 探測集建構
└── report.py           # 主表、per-intent 排序、圖表
scripts/eval.py         # 薄 CLI 入口（單組或預設六組；明確 confirmation guard）
scripts/report_results.py
                        # 七行主表、gap-closed、per-intent movement
```

**關鍵一致性要求**：`metrics.py` 的字串正規化**必須 import `src/data/normalize.py`**，與過濾管線的 F3 groundedness 檢查用同一份程式。兩邊各寫一份遲早會不一致，然後某個指標就悄悄錯了。

### 5.2 指標

沿用 `docs/DESIGN.md` §11 的凍結定義：intent accuracy、intent macro-F1、slot F1、exact match、JSON-valid rate，另記 tokens/s、VRAM 峰值、單筆 latency。

**JSON-invalid 樣本如何計分**：視為該筆全錯（intent 錯、slots 全部 miss）。不可以把 invalid 樣本從分母剔除——那會讓愛亂輸出的模型看起來比較好。

### 5.3 輸出

1. **主表七行**（零樣本 + 六組）× 全部指標，含 §2.2 要求的三個訓練狀態數字。
2. **差距補回率**（README 主標，見 §7）。
3. **per-intent 進步排序** —— `real_syn_filtered` 相對 `real_only` 的每個 intent accuracy 差，由大到小排。要同時看最進步與**退步最多**的 intent（退步的那幾個通常最能說明合成資料的失敗模式）。
4. **效能表** —— tokens/s、VRAM、單筆 latency。

---

## 6. Robustness 探測集

- **建構方式**：重用 `src/synthetic/recipes/noise.py` 的擾動器（錯字／繁中英 code-switch／口語助詞／ASR-like noise），施加於**真實 Test**，產出三到四個擾動版本，每版與 Test 同樣大小。
- **標籤不變**（擾動器已保證不破壞 slot span；破壞了就放棄該次擾動）。
- **明確標示為輔助分析，非主指標。** 主表永遠以未經修改的真實 Test 為準。
- **不影響防洩漏**：擾動後的 Test **只用於評測、絕不回流訓練**。這一點要在 README 的防洩漏聲明裡寫清楚，否則「你動了 Test」會是第一個被質疑的地方。
- 這裡是 `tw_colloquial` 那一軸真正該發光的地方；若它在主表扣分卻在探測集加分，那正是我們預期的 R-2 現象，照實報告。

---

## 7. README 結構（D-008）

主標一個數字，支撐兩條證據，一條誠實的輔助分析。

### 7.1 主標：差距補回率

```
gap_closed(%) = (score(group) − score(real_only)) / (score(full_real) − score(real_only)) × 100
```

- **頭條用 exact match**（整份 JSON 全對，最貼近產品意義、最不容易被美化）。
- 表格中對**每個指標**都算一次 gap-closed。
- **誠實護欄**：若 `full_real − real_only` 本身很小，gap-closed% 會非常不穩定（分母趨近 0）。因此**一律同時報絕對差值**，並在分母小於某門檻時明確標註「此比率不可靠」。

### 7.2 支撐一：過濾管線的價值

- `real_syn_unfiltered_full` vs `real_syn_unfiltered_eqn` vs `real_syn_filtered` 三組長條圖 —— 這組對照是「品質 vs 數量」的直接證據。
- 資料漏斗圖（生成 → 七道關卡各刪多少 → 最終）。
- **judge 回報的前六關漏檢率** —— 這是「過濾器本身有沒有用」的量化證據，不是自我宣稱。

### 7.3 支撐二：$0 API 成本、單張 4090 全流程可重現

- 資源總帳：GPU wall-clock 時數（生成 / 訓練 / 評測分開列）、估算電費、**等值 API 成本對照**。
- 一句話版本：整個專案從合成資料生成、微調到評測，都在一張消費級顯卡上完成，API 花費 $0。

### 7.4 輔助分析：台味 robustness

`tw_colloquial` 軸在原始 Test 與 robustness 探測集上的表現，**正負都寫**。若為負，那是 R-2 被驗證，寫進 Limitations 並分析原因。

### 7.5 數字誠實性驗證

`scripts/verify_readme.py`：自動核對 README 每張表的每個數字都能從 `runs/*/metrics.jsonl` 與 `reports/` 的原始檔重算。**M12 建立並首次跑通，M13 發佈前總驗收時再跑一次給使用者看。**

---

## 8. Gradio demo

- 本機 4090 執行。輸入繁中句子 → 顯示 intent、slots、原始 JSON、單筆 latency。
- 併列**微調前 vs 微調後**的輸出（同一句話兩個結果）—— 比單看微調後有說服力得多。
- 預載幾個示範句，含一組易混淆 minimal pair（例：「播放周杰倫」vs「搜尋周杰倫的歌」），直接展示 hard negative recipe 的效果。
- 錄成 GIF 放 README；GIF 產製與檢視都算在「自己產的圖自己打開看過」的規則內。

---

## 9. 發佈（M13）

| 項目 | 值 |
|---|---|
| HF dataset | `steven0226/formosa-nlu-synth-v1`（filtered + unfiltered 兩個 config） |
| HF model | `steven0226/gemma-4-e4b-formosanlu-lora`（LoRA adapter，非合併權重） |
| GitHub | `kuotunyu/03-formosanlu-sdg`，**此時才 `gh repo create`**（D-005） |
| Card | 雙語（英文為主 + 繁中摘要），內容依 `docs/data_card.md` |
| Commit | **絕不帶 `Co-Authored-By` trailer**（Contributors 只能有 kuotunyu） |

授權標註分層：

- **資料集** = MASSIVE（CC BY 4.0，需標示來源）+ teacher（Apache-2.0，對輸出無限制）
- **LoRA adapter** = 繼承 base model 的 Apache-2.0
- **程式碼** = MIT

轉 public 前必須通過發佈前總驗收（重現性、數字誠實性、防洩漏自查、授權相容性、安全掃描），且**使用者過目後才轉**。

---

## 10. 選配：延伸方向（只寫文字，不實作）

README 末尾一段 roadmap：用同一套管線做**台灣在地知識蒸餾**，並以 **TMMLU+** 評測，可提及 twinkle-eval 等台灣社群評測工具。目的是展示 roadmap 思維，**本專案不實作**，不佔任何里程碑。

---

## 11. Phase 2 Known Risks

| ID | 等級 | 風險 | 對策 |
|---|---|---|---|
| **R-9** | 中 | **Gemma 4 在繁中的底子可能不如 Qwen**，導致六組數字整體偏低而噪音大 | M8 零樣本 baseline 當閘門（§3）；不合格就停下來回報，考慮換回 `Qwen3-4B-Instruct-2507`。底子偏弱本身不是壞事——提升空間更大 |
| **R-10** | 中 | **固定 step + Val 選點的協定若六組不一致**，對照立刻失效 | 協定寫進 `configs/train.yaml` 並由 `train_all.py` 統一套用；`config.snapshot.yaml` 逐 run 存檔，M13 驗收比對六份是否一致 |
| **R-11** | 中 | **gap-closed% 在分母小時極不穩定** | 一律同時報絕對差值；分母低於門檻就標註不可靠（§7.1） |
| **R-12** | 低 | Gemma 4 多模態的 vision/audio towers 白佔 VRAM | M8 確認能否只載語言塔；不行就照常載入並記錄實際佔用（24GB 有餘裕，非阻塞） |
| **R-13** | 中 | **本機過夜批次中斷**（Windows 更新、當機、手滑） | `resume_from_checkpoint` 必須先驗證過才開跑；`train_all.py` 逐組獨立，單組失敗不影響其他組 |
| **R-14** | 低 | Colab 那一組的結果與本機不完全一致（硬體、套件版本差異） | 預期之內。`env.json` 記錄兩邊環境；比對的目的是驗證**可攜性**，不是要求逐位元一致 |
| **R-15** | 低 | 零樣本組與訓練組的 prompt 不同（前者需附 label 清單） | 主表明確註明此差異，不假裝條件一致 |
