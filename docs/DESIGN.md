# DESIGN.md — Phase 1 技術設計

> 適用範圍：合成資料管線（M0–M7）。Phase 2 的訓練／評測細節等 Phase 1 收尾後再展開。
> 這份文件是**實作的依據**。實作時若發現設計行不通，改的是這份文件（並在 `docs/DECISIONS.md` 記一筆），不是默默偏離。

---

## 1. 任務定義

輸入一句繁中（台灣）口語 → 輸出固定結構的 JSON：

```json
{"intent": "alarm_set", "slots": [{"type": "time", "value": "明天早上八點"}]}
```

- **Intent**：60 類（MASSIVE 定義）
- **Slot type**：55 類（MASSIVE 定義）
- **Student**：Qwen3-4B，4-bit QLoRA，non-thinking mode
- **主指標**：在**未經修改的** MASSIVE `zh-TW` Test（2,974 筆）上評測

---

## 2. 標籤空間的權威來源與凍結

- 唯一權威來源＝ M1 實際載入的 MASSIVE `zh-TW` 資料本身，**不從論文或網頁抄清單**。
- `src/synthetic/labels.py` 存放凍結後的常數（排序後的 intent 清單、slot type 清單），並記錄產生它的 commit 與來源檔 SHA256。
- `splits/manifest.json` 也記一份 label set；兩者不一致就是 bug，M3 的驗證步驟會擋。

---

## 3. 合成樣本 Schema

Pydantic 定義於 `src/synthetic/schema.py`，同一份 schema 同時用於：Ollama 的 `format` 參數（structured output）、過濾關卡 F1、以及最終資料集的欄位契約。

```python
class Slot(BaseModel):
    type: str        # must be in the frozen 55-slot-type set
    value: str       # must be groundable in `utt` after normalization

class SyntheticSample(BaseModel):
    id: str                # stable, content-addressed
    utt: str               # the generated utterance
    intent: str            # must be in the frozen 60-intent set
    slots: list[Slot]
    style: Literal["massive_like", "tw_colloquial"]
    provenance: Provenance
```

### Provenance 欄位（每筆必填，缺一即拒收）

| 欄位 | 說明 |
|---|---|
| `recipe` | `paraphrase` / `slot_substitution` / `noise_codeswitch` / `hard_negative` |
| `model` | teacher 的完整 tag（例：`qwen3:30b`）+ Ollama digest |
| `prompt_version` | 例：`paraphrase.v3`，對應 `src/synthetic/prompts/` 下的檔案 |
| `seed_sample_id` | 來源的 20-shot 真實樣本 id（hard negative 可有兩個） |
| `gen_params` | temperature / top_p / seed / context_length |
| `filter_score` | 各關卡分數（dict） |
| `filter_stage_passed` | 通過到第幾關 |
| `reject_reason` | 拒絕碼（通過者為 `null`） |
| `generated_at` | ISO 8601 |

**unfiltered 版本保留全部樣本（含被拒的，帶 `reject_reason`）**，filtered 版本只留全通過者。兩版都發佈——「被拒絕的長什麼樣」本身就是這個專案的賣點之一。

---

## 4. 四個 Recipe

所有 recipe 的種子都**只**來自 20-shot 真實資料（`splits/manifest.json` 的 `train_20shot`）。任何 recipe 都不得讀取 Val/Test。

### (a) `paraphrase` — 保留 intent/slots 的改寫

- 輸入：一筆種子（utt + intent + slots）
- 要求：語意等價、intent 不變、**所有 slot value 必須在新句子中以可正規化的形式出現**
- 每筆種子產 N 個變體（N 在 pilot 後定），要求彼此不重複
- 兩種 `style` 都產

### (b) `slot_substitution` — 程序化替換 + teacher 潤飾

**兩階段，關鍵在第一階段是程序化的，所以標籤天生正確：**

1. **程序化**：用台灣在地的 slot value 池替換原句的 slot（時間、地點、人名、聯絡人、日期、貨幣、單位…）。地名用台灣地名、人名用台灣常見姓名、時間用中文時間表達。此時句子可能生硬，但 **(slot_type, value) 的 ground truth 是程序給定的，不靠模型**。
2. **teacher 潤飾**：叫模型把生硬的句子改寫自然，**明確約束不得更動任何 slot value 的字面**。
3. 潤飾後仍走 F3 groundedness 檢查；改動了 slot value 就拒收。

> 這個 recipe 是「標註成本歸零」最有說服力的一支，因為標籤來自程序而非模型。

### (c) `noise_codeswitch` — 真實世界擾動

四種擾動，可組合：

| 擾動 | 說明 |
|---|---|
| 繁中英 code-switch | 台灣口語常見的英文夾雜（"幫我 set 一個明天七點的 alarm"） |
| 錯字 / 同音字 | 注音輸入法常見誤選（「在」↔「再」、「的」↔「得」） |
| 口語助詞 | 「欸」「啦」「喔」「一下」「幫我」等填充 |
| ASR-like noise | 同音替換、贅字、斷句錯誤 |

- **強制 `style = tw_colloquial`**（定義上就不是 massive_like）
- 擾動**不得破壞 slot span**：擾動器要知道 slot 的字元範圍並避開；避不開就放棄該次擾動

### (d) `hard_negative` — 易混淆 intent 的 minimal pairs

- 從真實資料的 intent confusion 結構挑出天然易混的 intent 對（例：`play_music` vs `qa_factoid`／「播放周杰倫」vs「搜尋周杰倫的歌」）
- 要求 teacher 產出**字面高度相似但 intent 不同**的成對句子
- 兩句都入庫，各自帶正確標籤，provenance 用 `pair_id` 互相指涉
- 這支最吃推理能力，也最容易產錯 → **judge 抽審時優先抽這一支**

### 目標比例（pilot 後可調，調了要記進 DECISIONS）

| Recipe | 目標佔比 |
|---|---|
| `paraphrase` | 35% |
| `slot_substitution` | 30% |
| `noise_codeswitch` | 20% |
| `hard_negative` | 15% |

---

## 5. `style` 軸（對應風險 R-2）

| 值 | 定義 | 服務對象 |
|---|---|---|
| `massive_like` | 貼近 MASSIVE zh-TW 原本的語域（偏書面／翻譯腔），label-preserving | **主指標**（原始 Test） |
| `tw_colloquial` | 台灣日常口語、code-switch、助詞、ASR noise | robustness 探測集、真實部署場景 |

**為什麼要分**：MASSIVE zh-TW 是從英文 SLURP 翻譯而來，Test 本身就是翻譯腔。若合成資料一面倒往「更台更口語」走，可能把模型帶離 Test 分佈，主表反而掉分。分開標記後，混合比例變成一個可調且**有記錄**的設計參數，而且不論結果正負都能誠實分析（「台味那一軸在原始 Test 上扣分、但在 robustness 探測集上加分」本身就是一個有價值的發現）。

---

## 6. 過濾管線（七道關卡）

順序＝**由便宜到昂貴**，讓貴的關卡只處理少量存活樣本。每關的拒絕碼寫進 `provenance.reject_reason`，一筆樣本只記**第一個**擋下它的關卡。

| # | 關卡 | 檢查內容 | 拒絕碼前綴 | 成本 |
|---|---|---|---|---|
| **F1** | JSON Schema | 可解析、欄位齊全、型別正確、`slots` 結構合法 | `F1_SCHEMA_*` | 極低 |
| **F2** | Label 合法性 | `intent` ∈ 凍結 60 類；每個 `slot.type` ∈ 凍結 55 類 | `F2_LABEL_*` | 極低 |
| **F3** | Groundedness | 每個 `slot.value` 經正規化後必須是 `utt` 的子字串；並檢查 slot 之間不重疊 | `F3_UNGROUNDED_*` | 低 |
| **F4** | 語言與在地性 | OpenCC 繁簡檢查（拒簡體殘留）、大陸用語詞表（視頻→影片、軟件→軟體、信息→訊息…）、非預期語言比例（code-switch recipe 例外放寬） | `F4_LOCALE_*` | 低 |
| **F5** | 去重與多樣性 | embedding 去重（合成集內互比）＋與種子過近者剔除（沒帶來新資訊）＋極端離群者剔除 | `F5_DUP_*` / `F5_OUTLIER_*` | 中（GPU） |
| **F6** | 去汙染 | 與 **Val/Test** 做近似比對，超過門檻即排除 | `F6_CONTAM_*` | 中（GPU） |
| **F7** | LLM judge 抽審 | 換家族模型判定 intent/slot 是否正確、句子是否自然 | `F7_JUDGE_*` | 高（GPU） |

### F5 / F6 的細節

- Embedding 模型在 M1 之後選型（要能處理繁中；候選在 M2 一併查證），選定後寫進 DECISIONS。
- **相似度門檻不能拍腦袋**：pilot 階段畫出相似度分布圖，人工看過再定門檻，門檻值與圖表進 `reports/pilot_report.md`。
- 「與種子過近」與「與 Test 過近」是兩個不同門檻，分開調。

### F7 judge 的抽樣策略（約 10%）

只審三類，不全審：

1. **困難**：`hard_negative` recipe 的全部樣本（這支最容易錯）
2. **衝突**：F5 相似度落在邊界帶、或 slot 數量與種子差異大的樣本
3. **隨機**：其餘樣本隨機抽樣，用來估算整體錯誤率並校準前六關

Judge 的判定結果**同時用於兩件事**：剔除壞樣本，以及**回報前六關的漏檢率**（放進 `reports/generation_report.md`）。後者是評估「過濾管線本身有沒有用」的證據。

---

## 7. 本機推論的運維規格

| 角色 | 模型 | 大小 | 授權 | 備註 |
|---|---|---|---|---|
| Teacher（主） | `qwen3:30b`（Qwen3-30B-A3B MoE，3B 活躍參數） | 19 GB | Apache-2.0 | 256K context |
| Teacher（保險） | `qwen3:14b` | 9.3 GB | Apache-2.0 | OOM 或吞吐不足時退這個 |
| Judge（換家族） | `gpt-oss:20b` | 14 GB | Apache-2.0 | 官方稱 16GB 記憶體可跑 |

> **M2 的查證範圍是「當前世代」，不是鎖死上表。** teacher 只做**推論**，因此不受「Qwen3.5 系列不建議 4-bit QLoRA」這類量化警告影響，可以放心採用更新世代的 Qwen 開放權重模型。上表是查證的起點，不是結論。
> Student 已定為 Gemma 4（D-007），所以 teacher 應**維持 Qwen 家族**以保住跨家族蒸餾的優勢 —— teacher = Qwen／student = Gemma 4／judge = gpt-oss，三家族全 Apache-2.0。

**運維鐵則：**

1. **序列式，不交錯**。先全量生成（teacher 常駐）→ 卸載 → 再跑 judge 抽審。24GB 裝不下 19+14，交錯呼叫會讓 Ollama 反覆換模型，吞吐直接崩掉。
2. `OLLAMA_CONTEXT_LENGTH` 壓到 **4096**。我們的 prompt 很短，不需要 256K；context 開太大會讓 KV cache 吃掉本來就不多的餘裕。
3. `OLLAMA_NUM_PARALLEL` 從 **4** 起跳，M4 pilot 實測後定案。注意 VRAM 需求約略隨 `NUM_PARALLEL × CONTEXT_LENGTH` 成長。
4. **OOM 退場路徑**：降 `NUM_PARALLEL` → 降 `CONTEXT_LENGTH` → 換 `qwen3:14b`。每次退場都記進 `reports/`。
5. `OLLAMA_MODELS` 建議指向 D: 槽（C: 剩約 203GB、D: 剩約 1.7TB）。M0 會問使用者。
6. Structured output 走 Ollama 的 `format` 參數（吃完整 JSON Schema，Python 端用 Pydantic `model_json_schema()`），**不靠 prompt 硬凹 JSON**。
7. 生成期間 4090 被佔滿數小時，該時段不排其他 GPU 工作。

---

## 8. 實驗矩陣

| 組別 | 訓練資料 | 用途 |
|---|---|---|
| `zero_shot` | **（不訓練）** 未微調的 base model 直接 prompt | 主表第一行，下界參照；同時是 D-007 的閘門 |
| `real_only` | 20-shot 真實 | 基準線 |
| `real_std_aug` | 20-shot 真實 + 傳統文字增強 | 排除「一般增強就夠」的質疑 |
| `real_syn_unfiltered_full` | 20-shot 真實 + 未過濾合成（全量） | 不過濾的實際影響 |
| `real_syn_unfiltered_eqn` | 20-shot 真實 + 未過濾合成（**下採樣至 = filtered N**） | **隔離「品質 vs 數量」變因**（D-004） |
| `real_syn_filtered` | 20-shot 真實 + 過濾後合成 | **主成果組** |
| `full_real` | 完整 MASSIVE train（11,514） | 上限參照 |

**公平性控制：**

- 各組對齊 **optimizer steps** 與 batch size；由於資料量不同，各組的 epoch 數與「真實樣本曝光次數」會不同，**這兩個數字必須連同主表一起報**。
- Seed 策略：全組合先 1 seed；`real_only` 與最佳 filtered 組補到 3 seeds 報 mean±std。
- **Val/Test 永遠只用真實資料。**

---

## 9. Standard Aug baseline 的具體定義

原始計畫只寫「傳統文字增強」，太模糊會讓這個關鍵消融失去說服力。本專案定義為三種手法的組合，**全部在本機執行、成本 $0**：

| 手法 | 說明 | Slot 安全性 |
|---|---|---|
| **Slot-aware EDA** | 同義詞替換、隨機交換、隨機刪除、隨機插入 | **必須先取得 slot 的字元範圍，禁止對 slot span 內做刪除／交換**；破壞了就放棄該次增強 |
| **回譯（back-translation）** | 本機 4090 跑 opus-mt / NLLB 級翻譯模型（zh→en→zh） | 回譯後必須通過與 F3 相同的 groundedness 檢查，否則丟棄 |
| **字元級噪音** | 隨機同音字／字元置換 | 同樣避開 slot span |

**產出筆數與 `real_syn_filtered` 對齊**，否則這組的比較同樣會混到數量變因。翻譯模型的選型在實作時上網查證。

---

## 10. 防洩漏與去汙染的邊界

| 規則 | 落地方式 |
|---|---|
| 生成端永不接觸 Test | 種子只從 `splits/manifest.json` 的 `train_20shot` 讀；`src/synthetic/` 下**不得** import 任何載入 Val/Test 的函式（M7 會做一次 import 稽核） |
| 去汙染隔離 | 獨立腳本 `src/filtering/decontaminate.py`，不與生成共用 process |
| **只排除、不挑選** | Test 只能用來刪掉太接近的樣本；不得用來排序、加權、選最佳門檻或做任何形式的模型選擇 |
| 留稽核軌跡 | log 記被刪樣本 id、相似度、對到的 Test id，隨資料集一起公開 |
| Split 先凍結 | `splits/manifest.json`（seed=42、來源 SHA256、真實筆數）在**任何生成開始前**完成，`--verify` 可重現 |

---

## 11. 評測指標定義（Phase 2 用，先在此凍結避免事後調整）

| 指標 | 定義 |
|---|---|
| **Intent accuracy** | 預測 intent 完全正確的比例 |
| **Intent macro-F1** | 60 類的 macro 平均（低頻 intent 不被高頻淹沒） |
| **Slot F1** | 對 `(slot_type, normalized_value)` 配對做 micro-F1；正規化規則與 F3 共用同一個 `src/data/normalize.py` |
| **Exact match** | intent 正確 **且** slot 集合完全相同（順序無關） |
| **JSON-valid rate** | 模型輸出可被 `json.loads` 解析**且**通過 Pydantic schema 的比例 |
| **Robustness 探測集** | 對真實 Test 加擾動（錯字／code-switch／ASR noise）的版本；**標明為輔助分析，非主指標** |
| 效能 | tokens/sec、VRAM 峰值、單筆 latency |

---

## 12. Known Risks

| ID | 等級 | 風險 | 對策 |
|---|---|---|---|
| **R-1** | 高 | **Gemini ToS 與公開發佈蒸餾語料相衝**。Gemini API Terms（effective 2026-03-23）：*"You may not use the Services to develop models that compete with the Services"*。付費層只保證 Google 不拿你的資料訓練，未解除此使用限制；我們要把整份語料公開上 HF 供任意第三方訓練任意模型 | **已由 D-002 解決**：改用 Apache-2.0 的本機開放權重 teacher，judge 也換成 Apache-2.0 的不同家族模型 |
| **R-2** | 高 | **Test 是翻譯腔、合成走台味，方向可能相反** → 主表掉分 | `style` 欄位分軸（§5）；混合比例為記錄在案的設計參數；結果正負都寫進 README |
| **R-3** | 中 | **MASSIVE 載不進來**：`AmazonScience/massive` 是 loading-script 型 dataset，`datasets` ≥ 4.5 已完全移除 script 支援（`trust_remote_code` 亦不再受理） | M1 依序試：① `revision="refs/convert/parquet"` ② `huggingface_hub` 下載 parquet 後本地讀 ③ `alexa/massive` 官方 release tarball ④（不推薦）pin `datasets<4`。成功路徑寫死並註明於 README |
| **R-4** | 中 | **24GB 裝不下 teacher + judge**；且兩顆模型下載都超過「>2GB 先問」門檻 | 序列式執行（§7）；M0 先問使用者才 pull |
| **R-5** | 中 | **每 intent 不足 20 筆**：MASSIVE train 各 intent 數量不均 | 抽樣用 `min(20, available)`；manifest 記真實數字；文件禁止含糊寫「約 1,200」 |
| **R-6** | 中 | **zh-TW 的空白分詞**會讓「slot value 必須出現在 utterance」規則誤判 | M1 實際印樣本確認；`src/data/normalize.py` 統一處理（去空白、全半形、繁簡），F3 與評測共用同一份 |
| **R-7** | 低 | **Colab 配額不足**：六組估 9–15 h L4，再加 2 組 ×3 seeds 可能超出單月 100 units | PLAN.md 已註明 3-seed 複跑允許排到下個月 |
| **R-8** | 低 | 合成資料可能繼承 teacher 的偏誤與台灣在地知識缺口 | judge 抽審（§6 F7）+ M6 人工抽 20 筆目視；限制寫進 data card |
| **R-9** | 中 | **Student 換成 Gemma 4 後，繁中底子大概率不如 Qwen**，可能讓六組數字整體偏低而噪音大 | M8 零樣本 baseline 當閘門，不合格就停下來回報並考慮換回 `Qwen3-4B-Instruct-2507`。詳見 `docs/DESIGN_PHASE2.md` §3、§11 |

> Phase 2 專屬的風險（R-9 ~ R-15）完整列在 `docs/DESIGN_PHASE2.md` §11。
