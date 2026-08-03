# DECISIONS.md — 決策紀錄（ADR）

> 用途：避免隔一段時間回來重新爭論已經定案的事。
> 規則：**每個會影響後續實作的選擇都要留一筆**，包含「考慮過但沒選的選項」與「什麼情況下該推翻這個決定」。
> 狀態：`accepted`（已定案）／`pending`（待驗證後定案）／`superseded by D-XXX`（已被推翻）。

---

## D-001 · 不使用 WSL，留在 Windows 11 原生

- **日期**：2026-07-27
- **狀態**：`accepted`
- **決策**：整個專案在 `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU` 以 Windows 原生執行，不遷移到 WSL。

**考慮過的選項**

| 選項 | 評估 |
|---|---|
| 遷移到 WSL2（原專案計畫的預設） | 要搬 repo、重裝 Python 環境、重登 gh／hf、Ollama 要重來；`.env`、conda、uv 0.11.18、gh 2.96、git-lfs 全在 Windows 側 |
| **Windows 原生（採用）** | Phase 1 全部工作（本機 LLM 生成、資料處理、過濾）在 Windows 都可完成；Ollama 0.32.0 已裝在 Windows，CUDA 直通 4090 |

**理由**

1. Phase 2 的長時間訓練本來就在 Colab（Linux），與本機無關。
2. 唯一 Linux-only 的依賴是 **vLLM**；Phase 2 評測預設用 `transformers` 批次推論，4B 模型跑 2,974 筆 Test 在 4090 上十幾分鐘即可。
3. 切換成本明確、收益接近零。

**什麼情況該推翻**：Phase 2 若真的需要 vLLM 的吞吐數據。屆時**不搬家**，在 WSL 掛 `/mnt/c/.../3_FormosaNLU` 跑同一份 repo 即可（4B 模型 I/O 量小，`/mnt/c` 的效能懲罰無感）。

**連帶約束**：為了保持 Linux 可重現性，CLAUDE.md 加了四條跨平台硬規則（pathlib、UTF-8 + LF、`PYTHONUTF8=1`、uv 鎖版）。

---

## D-002 · Teacher 改用本機開放權重模型（Ollama），judge 換家族

- **日期**：2026-07-27
- **狀態**：`accepted-complete`（最終型號與實測由 D-010 定案）
- **決策**：合成資料的 teacher 用**本機 Ollama 上的 Apache-2.0 開放權重模型**；品質審查 judge 用**不同家族**的 Apache-2.0 開放權重模型。Phase 1 不使用任何雲端 API。

**觸發原因**

Gemini API Terms（effective **2026-03-23**）明文：

> "You may not use the Services to develop models that compete with the Services (e.g., Gemini API or Google AI Studio). You also may not attempt to reverse engineer, extract or replicate any component of the Services"

付費層雖保證 Google 不拿使用者的 prompt/response 訓練自家模型，但**未解除**上述使用限制。本專案要把整份蒸餾語料**公開發佈到 Hugging Face**，等於讓任意第三方拿 Gemini 衍生輸出訓練任意模型 —— 這正好命中原始計畫的但書條件（「若封閉模型 ToS 對『拿輸出訓練模型並發佈』有疑慮，改用開放權重 teacher」）。

**考慮過的選項**

| 選項 | 成本 | 授權風險 | 評估 |
|---|---|---|---|
| Gemini Flash-Lite Batch | 低（約半價） | **高**（上述條款 + 公開發佈） | 否決 |
| 雲端開放權重 API（Together / Fireworks 的 Qwen3 大杯或 DeepSeek 級） | 約 $5–15 | 低（但各家 serving ToS 仍需逐一查證） | 保留為升級路徑 |
| **本機開放權重 via Ollama（採用）** | **$0** | **極低**（Apache-2.0） | 採用 |

**理由**

1. Apache-2.0 對輸出無使用限制，公開發佈語料零法律灰區。
2. 成本 $0，且**任何有一張 4090 的人都能完整重現**——這比「總共花了 $X」是更強的可重現性論述。
3. Teacher 與 student 同為 Qwen3 家族，data card 上「family-internal distillation」的敘事乾淨。
4. Judge 換家族（`gpt-oss:20b`，OpenAI 的開放權重模型，Apache-2.0）既達成原計畫「不同供應商以降低自我審查偏差」的目的，又把 judge 端的 ToS 灰區一併消掉。

**候選型號**（M2 實測後定案）

| 角色 | 模型 | 大小 | 授權 |
|---|---|---|---|
| Teacher（主） | `qwen3:30b`（Qwen3-30B-A3B MoE） | 19 GB | Apache-2.0 |
| Teacher（保險） | `qwen3:14b` | 9.3 GB | Apache-2.0 |
| Judge | `gpt-oss:20b` | 14 GB | Apache-2.0 |

**什麼情況該推翻**：M4 pilot 顯示本機模型的 JSON 合格率或標籤正確率低到無法接受。屆時升級到**雲端開放權重 API**（非封閉模型），且**需使用者另行核可**（要新註冊帳號並儲值）。

**連帶影響**：`logs/cost.json` 記的是 GPU wall-clock 時數 + 估算電費 + 等值 API 成本對照，不是美元帳單。

---

## D-003 · 文件結構

- **日期**：2026-07-27
- **狀態**：`accepted`
- **決策**：`CLAUDE.md`（規則）／`PLAN.md`（進度與驗證）／`docs/DESIGN.md`（技術設計）／`docs/DECISIONS.md`（本檔）＋ `.claude/skills/` 下的專案 skill。

**理由**：四份文件各有單一職責，恢復脈絡有固定路徑（CLAUDE → PLAN 狀態頁首 → DECISIONS）。專案 skill 則把「怎麼做」的 SOP 沉澱下來，隨里程碑增建（`formosanlu` → `formosanlu-generate` → `formosanlu-filter` → `formosanlu-colab`）。

**考慮過但沒選**：把所有東西塞進單一 CLAUDE.md（規則與進度混在一起，隔幾週回來很難掃）。

---

## D-004 · 實驗組加「等量對照」，不做 per-recipe 消融

- **日期**：2026-07-27
- **狀態**：`accepted`
- **決策**：主實驗六組（見 `docs/DESIGN.md` §8），新增 `real_syn_unfiltered_eqn`（未過濾合成下採樣至與 filtered 完全相同筆數）。**不做** per-recipe leave-one-out 消融。

**理由**

- 加等量對照：沒有它的話，「filtered 比 unfiltered 好」同時混到**品質**與**數量**兩個變因，是審稿人第一個會問的問題。成本只多一組訓練。
- 不做 per-recipe 消融：需要多 3–4 組訓練（約 +4–8 小時 L4），會吃掉半個月的 Colab 配額。改在 README 的 Limitations 誠實寫「未做此消融」。

**什麼情況該推翻**：Colab 配額有餘裕，或主結果顯示某個 recipe 明顯可疑而需要單獨驗證。

---

## D-005 · 只做本機 git，發佈時才建 GitHub remote

- **日期**：2026-07-27
- **狀態**：`accepted`
- **決策**：現在只 `git init`（本機），**不建 GitHub remote**。等 Phase 2 通過發佈前總驗收，才 `gh repo create` 並 push。

**理由**：不用現在定 repo 名稱，也不會有半成品掛在 GitHub。代價是沒有異地備份——使用者已知悉並接受。

**什麼情況該推翻**：使用者要異地備份，或需要在別台機器上接續工作。

---

## D-006 · Phase 2 訓練以本機 4090 為主，Colab notebook 降為可攜性交付物

- **日期**：2026-07-27
- **狀態**：`accepted`
- **決策**：六組主實驗 + 3-seed 複跑（合計約 10 runs）**全部在本機 4090 執行**；同時產出一本 Colab notebook 作為交付物，並實際在 Colab 跑**一組**驗證可攜性。

> ⚠️ **本決策修訂了 CLAUDE.md【分工】原文的「超過 30 分鐘的 GPU 訓練一律寫成 Colab notebook」。** 這是使用者明示核可的例外，不是默默偏離。原則本身（長訓練不佔用互動式工作階段）仍然有效，只是在本專案由「過夜批次 + 斷點續跑」滿足。

**考慮過的選項**

| 選項 | 評估 |
|---|---|
| 全部走 Colab（照原規則） | 六組 + 複跑估 9–15 h L4，約吃 60–75 units。可平行開多本，但專案一、二會跟它搶同一個月的 100 units |
| **本機為主 + 一本 Colab notebook（採用）** | 4090 對此級 QLoRA 約為 L4 的 2.5–3.5 倍，10 runs 估 5–8 h 可過夜；Colab 配額幾乎全留給專案一、二 |
| 全部本機、不做 Colab notebook | 最省事，但少掉「會寫 Colab 訓練 notebook」這個可展示的工程能力，而原專案規劃是把它當交付物的 |

**理由**

1. 算力：4090 明顯快於 L4，且本機沒有 units 上限。
2. 資源配置：Colab 的 100 units/月 是三個專案共用的稀缺資源，這個專案讓出來最划算。
3. 敘事：搭配 D-002（本機 teacher），整條線變成「**合成資料生成 → 微調 → 評測 → demo 全部在一張 RTX 4090 上完成，API 成本 $0**」，任何有消費級顯卡的人都能重現。這比「訓練在 Colab」強得多。
4. Colab notebook 仍然產出，且**包裝同一份 `src/training/train.py`**（不是另寫一套），實跑一組驗證可攜性。

**什麼情況該推翻**：本機批次實測遠慢於預期（例如單組 >2 小時），或本機需要長時間挪作他用。屆時把部分組別搬回 Colab —— 因為兩邊共用同一份訓練程式碼，切換成本很低。

---

## D-007 · Student base model 改用 `google/gemma-4-E4B-it`

- **日期**：2026-07-27
- **狀態**：`accepted`
- **決策**：student 從原計畫的 Qwen3-4B 改為 **`google/gemma-4-E4B-it`**。Teacher 維持 Qwen3 家族，judge 維持 `gpt-oss`。

**考慮過的選項**

| 選項 | 發佈 | 授權 | 4090 可行性 | 評估 |
|---|---|---|---|---|
| Qwen3-4B（原計畫，hybrid thinking） | — | Apache-2.0 | 可 | 需在訓練與推論兩端關掉 thinking，多一個易錯環節 |
| Qwen3-4B-Instruct-2507 | — | Apache-2.0 | 可 | non-thinking-only，比原計畫乾淨；但與 teacher 同家族 |
| Llama 3.2 3B | 舊世代（2026 上半年 Meta 未推出新開放權重家族） | Llama Community License：AUP + 「Built with Llama」標示 + 衍生模型命名須含 Llama | 可 | 世代舊且授權帶義務，沒有選它的理由 |
| **Gemma 4 E4B-it（採用）** | 2026-04-02 | **Apache-2.0** | LoRA 需約 17 GB，QLoRA 更低 | 採用 |

**理由**

1. **Gemma 4 起改用 Apache-2.0**，舊版 Gemma Terms 的使用限制與向下游傳遞義務已移除 —— 這消掉了原本排除 Gemma 的唯一理由。
2. 規格對位：4.5B 總參數 / 2.3B effective（Per-Layer Embeddings）、128K context、有 `-it` 指令版，與原計畫的 4B 級 student 同量級。
3. 工具鏈 **day-0 支援**（transformers / Unsloth / TRL / Axolotl）；Unsloth 建議 E4B QLoRA 優於 E2B LoRA。
4. **跨家族蒸餾**：teacher = Qwen3、student = Gemma 4、judge = gpt-oss，三家族全 Apache-2.0。這堵掉「teacher 和 student 同家族，當然有效」的質疑，科學上比同家族更強。
5. 授權影響範圍小：資料集授權由 MASSIVE（CC BY 4.0）+ teacher（Apache-2.0）決定，**student 授權只管到發佈的 LoRA adapter**。

**為什麼不追更新世代**：搜尋顯示 Qwen 已有 Qwen3.5 等更新世代，但 Unsloth 明確警告 Qwen3.5 系列**不建議做 4-bit QLoRA**（量化誤差偏大）。本專案的 student 是**受控變因**而非研究對象，選一個工具鏈成熟、量化行為明確的 base 比追最新更重要。這是有理由的選擇，不是沒跟上。

> 附帶修正：**teacher 只做推論**，不受上述 QLoRA 警告影響。因此 `docs/teacher_choice.md` 在 M2 的查證範圍要擴大到「**當前世代**的 Qwen 開放權重模型」，不預設鎖死 `qwen3:30b`。

**新增風險 R-9**：Gemma 在繁中的底子大概率不如 Qwen。底子偏弱對實驗未必是壞事（提升空間更大），但若弱到離譜會讓六組數字很吵。
**對策**：M8 加一道**零樣本 baseline 量測**當閘門（詳見 `docs/DESIGN_PHASE2.md` §3）。這行本來就該進主表，順便當檢查，成本只有一次推論。

**什麼情況該推翻**：M8 零樣本 baseline 顯示 JSON 完全不成形、或 intent accuracy 接近亂猜（1/60 ≈ 1.7%）到無法作為訓練起點。屆時換回 `Qwen3-4B-Instruct-2507`（會犧牲跨家族的優勢，須在 README 註明）。

---

## D-008 · README 賣點定位

- **日期**：2026-07-27
- **狀態**：`accepted`
- **決策**：使用者授權由我決定。定為「一個主標數字 + 兩條支撐證據 + 一條誠實的輔助分析」。

| 層級 | 內容 |
|---|---|
| **主標** | **差距補回率** —— 以 `real_only` 為 0%、`full_real` 為 100%，合成資料補回了幾 %。頭條用 exact match |
| 支撐一 | **過濾管線的價值** —— filtered / unfiltered 全量 / 等量對照 三組差距，加上 judge 回報的前六關漏檢率 |
| 支撐二 | **$0 API 成本、單張 4090 全流程可重現** —— 取代原計畫的「API 總共花 $X」（D-002 之後不再適用） |
| 輔助 | **台味 robustness** —— `tw_colloquial` 軸在原始 Test 與探測集上的表現，正負都寫 |

**理由**

- 差距補回率是**單一數字、三秒看懂**，而且自帶上下界參照，比裸的 accuracy 有意義。
- 過濾管線的三組對照是「資料工程能力」的直接證據，也是這個專案跟「呼叫一次 API 生資料」的差別所在。
- $0 / 4090 是記憶點與可信度（任何人都能重現）。
- 台味那一軸若因 R-2 在主表為負，就誠實列進 Limitations —— 負面結果加分析比選擇性報告更有分析價值（這本來就是實驗鐵律的要求）。

**誠實護欄**：`full_real − real_only` 若很小，差距補回率的分母趨近 0 會極不穩定。因此**一律同時報絕對差值**，分母低於門檻就明確標註「此比率不可靠」。

**什麼情況該推翻**：實驗結果顯示某個面向明顯更有故事性（例如過濾管線的效果遠比補回率驚人）。README 的排序服務於**真實結果**，不是預先寫好的敘事。

---

## D-009 · 夜間無人監督執行：預先授權與自動閘門

- **日期**：2026-07-27
- **狀態**：`accepted`
- **決策**：使用者在睡覺時由 agent 獨自執行 M0–M8。原本要人點頭的四道閘門改為**預先授權 + 可計算的自動判準**，守則寫在 `docs/AUTONOMOUS_RUN.md`。

**背景**：使用者希望「訂好計畫後，趁睡覺時讓 agent 照著實作大部分內容，剩下需要人操作的等早上再做」。原本的 PLAN.md 是為有人監督設計的，會在 M0 開始沒幾分鐘就卡在模型下載的詢問上，整晚空轉。

**預先授權項目**

| # | 原本的閘門 | 改成 |
|---|---|---|
| 1 | M0 pull Ollama teacher/judge（約 33GB，超過 2GB 門檻要問） | 直接 pull，但下載前檢查磁碟，低於 100GB 餘裕就停 |
| 2 | 下載 MASSIVE `zh-TW` | 直接下載 |
| 3 | M8 下載 `google/gemma-4-E4B-it`（約 10GB 級） | 直接下載 |
| 4 | M2 teacher/judge 選型要使用者點頭 | 依 `AUTONOMOUS_RUN.md` §3 的候選條件自動定案，理由寫滿 `teacher_choice.md`，早上 review |
| 5 | M4 pilot 報告要使用者點頭才跑全量 | 依 §4 的**六道可計算門檻**自動放行，任一項不達標就停 |

**維持不變的硬性禁止**：任何對外寫入（push / gh / HF 上傳 / 發佈）、任何花錢動作、讀取 `../.env`、修改 repo 以外的東西、下載授權清單以外的模型、破壞性 git 操作、**開始 M9 訓練批次**。

**配套措施**

1. **`.claude/settings.json` 權限 allowlist**：把專案會用到的指令列進 allow，危險與對外操作列進 deny。不在 allowlist 的動作會跳確認 → 無人時等於自動停住，這正是想要的保守失敗模式。順帶設 `attribution.commit: ""`，在 harness 層永久關掉 co-author trailer（比靠記憶可靠）。
2. **停損與改道協定**（§5）：卡住就寫 `docs/HANDOFF.md` 然後改做不相依的里程碑，不整條停住。M5（過濾管線可用假資料先寫）與 M8 零樣本是兩張萬用救援牌。
3. **誠實性鐵律**（§8）：明文禁止為了讓流程往下走而放寬門檻、刪測試、跳驗證、捏造數字。**門檻沒過是一個發現，不是一個障礙。**
4. **持續交接**（§9）：`HANDOFF.md` 在每個里程碑開始與結束都更新，不是只有最後一次——凌晨四點掛掉時使用者仍看得到進度。

**附帶決定：不搬 `OLLAMA_MODELS`。** 原本考慮改指 D: 槽，但 C: 尚有約 203GB、33GB 綽綽有餘，而搬遷需改系統環境變數並重啟 Ollama 服務，屬系統層變更、不在授權範圍。維持預設路徑。

**今晚範圍的上界**：M8 零樣本 baseline。**M9 的 5–8 小時訓練批次明確排除**——那要先讓使用者看過 M8 零樣本結果（R-9 的閘門），確認 Gemma 的繁中底子夠用，才值得投入。

**什麼情況該推翻**：夜間執行的實際結果顯示自動判準太寬（放行了不該放行的東西）或太嚴（動不動就停）。屆時調整 §3/§4 的判準並記一筆新決策——但**調整要在事前，不能在當下為了通關而改**。

---

## D-010 — Teacher／Judge／Embedding 依本機實測定案

- **日期**：2026-07-27
- **狀態**：`accepted`
- **決策**：Teacher 使用 `qwen3.6:27b`，judge 使用 `gpt-oss:20b`，F5/F6
  embedding 使用 `BAAI/bge-m3`。Teacher 固定 `num_ctx=4096`、client concurrency
  4；judge 不傳 `think: false`，改在 system prompt 指定 `Reasoning: low`。

**考慮過的選項**

| 選項 | 結果 | 理由 |
|---|---|---|
| `qwen3.6:27b`（17GB） | **採用** | 最新可用 Qwen、Apache-2.0、≤20GB，Ollama structured output 實測通過 |
| Qwen3.6 35B（24GB） | 否決 | 超過 D-009 的 20GB teacher 護欄 |
| Qwen3.5 27B（17GB） | 否決 | 同大小但較舊，沒有優於 Qwen3.6 的理由 |
| `qwen3:30b`／`qwen3:14b` | 保留 fallback | 只有 M4 未過固定門檻或運行退化時才回退 |
| 封閉模型 API | 否決 | 蒸餾與公開語料的服務條款風險，且本機路線已達標 |

**理由**

- Teacher 20 筆真實 seed 實測：JSON 20/20，intent／slot／grounding 全對
  18/20；concurrency 1/4/8 分別為 29.91／35.86／35.86 tok/s，因此選 4。
- Teacher 模型 VRAM 峰值 15,820 MiB，全 GPU 峰值 18,277 MiB，4090 有餘裕。
- Judge 兩輪各 20 筆皆為 20/20 JSON-valid，四個布林判定一致 19/20（95%）。
- gpt-oss 在 Ollama 傳 `think: false` 會產生空內容；移除後 40/40 可解析，
  因此這是後續 client 的硬性相容設定。
- 完整原始結果在 `reports/m2_teacher_benchmark.json` 與
  `reports/m2_judge_benchmark.json`；授權與條款證據在
  `docs/teacher_choice.md`。

**什麼情況該推翻**：M4 在不調低既定門檻的前提下失敗、Ollama 更新造成輸出或
吞吐明顯退化，或 M5 實測顯示 BGE-M3 的中文相似度分布無法形成可解釋的閾值。
若需改走雲端開放權重 API，必須先取得使用者對帳號、ToS 與費用的額外核可。

---

## D-011 — Gemma 4 使用文字塔 QLoRA，M8 runtime 驗證通過

- **日期**：2026-07-27
- **狀態**：`accepted`
- **決策**：FormosaNLU 只載入 `google/gemma-4-E4B-it` 的
  `Gemma4ForCausalLM` 文字塔；採 NF4 double-quant QLoRA、LoRA
  rank/alpha `16/32`、`all-linear` targets、500 steps、effective batch 16、
  max length 512。M8 不得在 one-step smoke test 通過前宣稱可訓練。

**理由**

1. 任務只有文字 NLU，載入 vision/audio towers 沒有研究價值且浪費 24GB VRAM。
2. Transformers 隨目前套件提供官方文字-only `Gemma4ForCausalLM` 路徑；
   PEFT 對 QLoRA 建議以 `all-linear` 覆蓋線性層。
3. 11,514 筆真實訓練樣本的 prompt+target 實測最大 183 tokens，512 不會截斷。
4. 六組實驗共用同一 config digest，避免組間偷偷改超參數。

**Runtime 驗證**

原 Anaconda-based environment 在匯入 `torch\lib\c10.dll` 時得到 WinError
1114。改用 uv-managed CPython 3.11.15 後，PyTorch 2.11.0+cu128、CUDA 與
RTX 4090 均通過。由於 E4B multimodal checkpoint 的文字權重位於
`model.language_model.*`，loader 明確把它映射到 text-only
`Gemma4ForCausalLM` 的 `model.*`；665 個語言權重全部載入，vision/audio
權重則刻意忽略。

One-step `real_only` QLoRA smoke 已產生 adapter 與 `checkpoint-1`：
train loss 1.9862、eval loss 2.9560、peak allocated VRAM 20,646 MiB。
機器可讀證據與 adapter hash 在 `reports/m8_smoke_test.json`。

完整零樣本 Test 的嚴格 intent accuracy 為 10.66%，約為 60 類隨機基準
1.67% 的 6.4 倍；517 筆 strict-valid output 中 61.32% intent 正確。
因此通過 R-9 的「不是接近亂猜」閘門，維持 Gemma 並進入 SFT。JSON-valid
17.38% 與 slot F1 0% 同時證明 schema 遵循很弱，後續訓練與評測不得掩飾。

**重新審視的觸發條件**：text-only key mapping 在 Transformers 升級後失效、
語言權重出現 missing keys，或正式訓練超過 24GB VRAM。

---

## D-012 — Standard Aug 使用固定 Marian round trip 加 slot-aware EDA

- **日期**：2026-07-27
- **狀態**：`accepted`
- **決策**：M9 的 `real_std_aug` 使用 deterministic、slot-protected
  augmentation。Round-trip translation 固定為
  `Helsinki-NLP/opus-mt-zh-en` revision
  `cf109095479db38d6df799875e34039d4938aaa6` 與
  `Helsinki-NLP/opus-mt-en-zh` revision
  `408d9bc410a388e1d9aef112a2daba955b945255`；不足部分以 slot-aware EDA
  與 bounded character noise 補足。增加筆數必須與 filtered synthetic 的
  N 完全相同。

**考慮過的選項**

1. 線上翻譯 API：拒絕，會引入費用、條款與不可重現的服務版本。
2. 只做字元 noise：拒絕，控制組太弱，無法代表常見的 standard augmentation。
3. 未保護 slots 的整句 backtranslation：拒絕，會改壞 literal span labels。

**理由**：兩個模型都能由 Transformers MarianMT 直接本機執行，revision、
license、必要檔與 SHA-256 已凍結。slot placeholder 先切段、逐段翻譯再還原，
避免模型改寫 slot value。正式輸出 3,760 筆包含 EDA 2,200、character noise
514、backtranslation 1,046。

**重新審視的觸發條件**：模型 revision 消失、license 改變、round-trip 造成
slot span 無法還原，或 M9 發現 Standard Aug 被單一變換方式完全主導。

---

## D-013 — M6 未達 8,000 時保留負面結果，不放寬 frozen thresholds

- **日期**：2026-07-27
- **狀態**：`accepted`
- **決策**：11,264-row M6 在 frozen F1–F6 下只通過 3,760 筆，正式記為
  `complete_below_target`。不為達成 8,000 而更動 threshold、刪改報告或挑選
  另一套事後規則。M9 equal-N 控制可先以真實 N=3,760 準備，但長批次須讓
  使用者選擇照實訓練或另開 revised generation run。

**考慮過的選項**

1. 放寬 synthetic duplicate threshold：拒絕，會是看過結果後的 gate hacking。
2. 把 rejected rows 補到 8,000：拒絕，破壞 filtered 組的定義。
3. 只報 pilot 75% yield：拒絕，會掩蓋 corpus-scale mode collapse。
4. 保留結果並用 equal-N 設計比較：採用。

**理由**：F1–F4 survivors 9,114 筆中只有 4,044 個 exact-text distinct
utterances；F5 合理移除 4,596 筆 synthetic duplicates。索引、ID、embedding
archive 與漏斗加總均通過，證據指向 generation mode collapse 而非管線 bug。

**重新審視的觸發條件**：只能在發現可重現的程式錯誤、資料讀取錯誤或 frozen
threshold 實作與 D-010 不一致時重算；單純不喜歡結果不構成推翻理由。

---

## D-014 — M9 過夜批次採明示 3,760 的安全總控，評估分開

- **日期**：2026-07-27
- **狀態**：`accepted`（評估分開的部分已由 D-015 取代）
- **決策**：使用者明確說「開始跑 M9」後，使用
  `scripts.m9_overnight` 執行六組 seed-42 訓練。啟動碼固定包含
  `3760`；執行前必須通過 contributors、工作樹、資料、模型、resume、
  GPU baseline 與磁碟 gate。六組 adapter evaluation 不自動綁在訓練後。

**考慮過的選項**

1. 繼續用兩條人工命令：拒絕，容易漏掉資源衝突或在錯誤狀態下啟動。
2. 訓練後自動跑六組完整評估：拒絕，M8 單次全測已約一小時，可能讓 GPU
   使用超出使用者的睡眠時段。
3. 用明示資料量的 guard，只自動跑六組訓練：採用。

**理由**：這個入口不改任何 threshold、prompt、資料或訓練超參數；它只把
已驗證過的六組順序、checkpoint resume 與資源護欄組合起來。
`M9-OVERNIGHT-3760-4090` 也留下「未達 8,000、仍照實訓練」的可稽核證據。

本決策只在使用者完成 M8 review 後，針對 M9 啟動範圍取代 D-009 的原始
M9 禁令；D-009 的對外寫入、付費、誠實性與安全禁止仍全部有效。

**重新審視的觸發條件**：GPU baseline 超過 3,000 MiB、可用磁碟低於
20 GiB、任何 sibling GPU workload、資料 hash/count 改變、resume smoke
失效，或使用者改選 revised generation run。

---

## D-015 — 夜間 GPU 可超過八小時，M9 訓練後自動接評估

- **日期**：2026-07-27
- **狀態**：`accepted`
- **決策**：使用者說「開始跑 M9」並通過 D-014 gate 後，六組訓練全部成功
  時自動接六組 resumable adapter evaluation，最後產生 M10 主表。使用者已
  明示睡眠約八小時，起床後不一定立即用電腦，因此不以八小時為硬停損。

**考慮過的選項**

1. 八小時到點強制終止：拒絕，可能破壞正在寫入的 checkpoint。
2. 訓練完成就停止等待使用者：不再採用，會浪費已明示可用的夜間 GPU 時間。
3. 健康狀態下自動續跑評估，失敗時保留 checkpoint：採用。

**理由**：evaluation 已有逐筆 JSONL checkpoint、完整結果跳過與獨立 batch
report。將它接在成功訓練後不改變實驗設計，只減少無人時的空轉。M10 僅在
六組 evaluation 都完成後才標成 complete。

**範圍限制**：F7 judge、額外 seeds、generation rerun、發布與 sibling
projects 不由此 pipeline 自動啟動；contributors 仍只能是 `kuotunyu`。

**重新審視的觸發條件**：使用者要求停機、另一專案開始 GPU workload、硬體
異常、磁碟不足、training/evaluation 回傳失敗，或 checkpoint 無法驗證。

---

## D-016 — M14 使用 hierarchical paired bootstrap 與 exact McNemar

- **日期**：2026-07-29
- **狀態**：`accepted`
- **決策**：從既有 `real_only`／`real_syn_filtered` seeds 42–44 的完整
  2,974-row predictions 重建 paired statistical evidence。Effect interval
  使用兩層 bootstrap：先重抽 training seeds，再於各 seed 內重抽相同 Test
  rows；intent accuracy 與 exact match 另逐 seed 做 two-sided exact
  McNemar，六項 p-values 使用 Holm correction。

**理由**

1. 同一 Test row 在兩個 adapter 間是配對觀察，paired 分析比把 aggregate
   seed means 單獨做 t interval 更有效率。
2. 同一 Test set 在三個 seeds 重複出現，不能把 8,922 個結果當成完全獨立；
   hierarchical bootstrap 明確保留 seed 與 row 兩層。
3. Prediction JSONL 已存在且有完整 expected rows，不需額外 GPU，也不需接觸
   validation／Test 來挑選模型或資料。

**限制**：這些檢定只支撐 frozen MASSIVE `zh-TW` Test 與 Gemma 4 contract
內的 paired 差異，不自動變成跨模型、跨資料集或自然台灣口語的泛化證據。

**重新審視的觸發條件**：發現 prediction indices／expected rows 不一致、
評測 parser 有可重現錯誤，或取得更多真正獨立的 student families／datasets。

---

## D-017 — M15 第二 student 採 `microsoft/Phi-4-mini-instruct`

- **日期**：2026-07-29
- **狀態**：`accepted-complete`（artifact audit、amended smoke qualification、
  六組正式 runs 與跨 family report 均已完成）
- **決策**：跨模型 replication 的第二 student 定為
  `microsoft/Phi-4-mini-instruct`。只重跑主比較：
  `real_only`／`real_syn_filtered` × seeds 42–44；資料、prompt、steps、
  effective batch、max length 與 2,974-row Test contract 均保持一致。

**考慮過的選項**

| 選項 | 評估 |
|---|---|
| Qwen 3–4B student | 中文強，但與 Qwen teacher 同 family，較難排除 family affinity |
| SmolLM3 3B | Apache-2.0、工具鏈乾淨，但官方原生語言不含 Chinese |
| Llama 3.2 3B | 模型小，但 Chinese 不是主要支援語言且 license 義務較多 |
| **Phi-4-mini-instruct（採用）** | 3.8B、MIT、官方列出 Chinese、約 7.7 GB，且與三個既有角色皆不同 family |

**理由**

1. 第二 family 的目的不是追最新榜單，而是測 synthetic augmentation 的方向
   是否能跨 student architecture 重現。
2. Phi 官方 model card 明列 24-language／Chinese support，且 3.8B QLoRA
   適合單張 4090 24 GB。
3. MIT 授權讓報告與可能的 adapter 發布沒有額外命名／AUP 義務。

**硬性 gate**：下載前依 >2 GB 規則取得使用者明示同意；下載後固定 revision
與 SHA、完成 tokenizer truncation audit、one-step QLoRA、checkpoint resume
與小型 strict-output probe。任一項失敗就停，不為通關改資料或 primary config。

**完成結果**：固定 revision `cfbefacb99257ffa30c83adab238a50856ac3083`；
`real_only`／`real_syn_filtered` × seeds 42–44 六組各完成 500-step training 與
2,974-row strict evaluation。預先登記的 `intent_accuracy`、`exact_match` 跨兩個
student families 判準通過；完整結果見
`reports/m15_cross_model_replication.json`。原始 strict smoke failure 與 D-018
amendment 同時保留，沒有 parser repair 或事後調參。

**凍結 revision 與 claim（2026-07-29）**：

- revision：`cfbefacb99257ffa30c83adab238a50856ac3083`
- remote selected bytes：7,691,526,227；license：MIT
- primary replication metrics：`intent_accuracy`、`exact_match`
- 宣稱「跨 student families 重現」的必要條件：兩項 primary metrics 在 Gemma
  與 Phi 各自 paired mean Δ 都為正，且各自 hierarchical 95% CI lower bound
  都大於零；若未達標，固定回報
  `not_replicated_under_preregistered_criterion`

**重新審視的觸發條件**：官方 revision／license 變更、Transformers 5.5
無法穩定載入、24 GB OOM、繁中 zero-shot 接近亂猜且 SFT smoke 無法學習，
或 checkpoint resume 不可驗證。

---

## D-018 — M15 smoke 拆分 infrastructure qualification 與 task quality

- **日期**：2026-07-30
- **狀態**：`accepted_before_formal_phi_runs`
- **決策**：保留原始 `m15_phi4mini_smoke.json` 的 strict failure；新增
  `m15.smoke.infrastructure.v2`，只用 checkpoint/resume、32-row evaluation、
  VRAM、JSON syntax 與必要頂層型別判定 pipeline 是否具備執行正式六組的
  infrastructure 資格。正式六組仍用原 strict parser 與預註冊判準。

**觸發證據**

- checkpoint-1 建立成功，跨程序 resume 至 checkpoint-2／global step 2。
- 32-row evaluation 完成；peak reserved VRAM 6,674 MiB。
- 原 strict gate 失敗：`unknown_intent 32/32`、strict JSON-valid `0/32`。
- 結構診斷：`32/32` 可解析 JSON object、intent 為 string、slots 為 list；
  `27/32` slots 為 object list。
- 正式 Phi training/evaluation 在 amendment 登錄前為 **0 runs**。

**考慮過的選項**

| 選項 | 決定 |
|---|---|
| 直接放寬 strict evaluator／加入 label aliases | 拒絕；會改動 primary metric |
| 在 adapted prompt 加入 label catalog | 拒絕；會破壞與 Gemma 的 frozen prompt parity |
| 增加 smoke steps 直到 strict gate 通過 | 拒絕；屬事後調參且混淆 infrastructure 與 task quality |
| 保留 failure，將 smoke 改為 infrastructure-only | 採用；正式 500-step contract 與失敗條件不變 |
| 放棄第二 model family | 暫不採用；現有證據顯示 runtime 正常，尚未測到正式 augmentation effect |

**未改項目**

- model revision `cfbefacb99257ffa30c83adab238a50856ac3083`
- 兩組 frozen training rows 與 SHA-256
- `formosanlu_nlu.v1` prompt、500 steps、effective batch 16、max length 512
- seeds 42／43／44 與 2,974-row Test
- strict parser、`intent_accuracy`、`exact_match`、paired statistics
- 跨 family claim 的 hierarchical 95% CI lower-bound criterion

**研究誠信要求**：原始失敗與 amended qualification 必須同時提交；來源
reports／predictions／run report 以 SHA-256 綁定，不得覆寫原始失敗，不做
parser repair 或 label aliasing。正式六組若仍無法學到 canonical intents，
必須照實回報 `not_replicated_under_preregistered_criterion`。

**重新審視條件**：amended gate 無法由原始 artifacts 重算、來源 SHA 不符、
正式 contract 任一欄位變更，或正式 run 發生 OOM／不可續跑。

---

## D-019 — 取消 Phi `full_real` 參照組

- **日期**：2026-08-01
- **狀態**：`accepted`
- **決策**：不為 Phi-4-mini 增設 `full_real` 上限組。M15 維持兩組（`real_only`、`real_syn_filtered`）× 三種子。

**背景**：這一組原本排在夜間批次第三層，理由是「Phi 也能算差距補回率，跨模型表格會對稱」。第一次取消是因為 10 小時預算不足；使用者之後解除時間限制，因此重新評估。

**重新評估後仍取消，理由與時間無關：**

1. **要改動已凍結的 pipeline。** `scripts/m15_phi4mini.py` 是為「兩組 × 三種子」凍結的，`full_real` 需要新的資料備置與新組別，等於在拿到結果之後回頭動 M15 的執行契約。
2. **在預先登記範圍之外。** 判準只綁 `real_syn_filtered` vs `real_only` 的 paired delta，該結論**完全不依賴** `full_real`。
3. **買到的是呈現，不是證據。** 差距補回率是易讀的包裝，但跨 family 主張已由 paired delta 與 CI 成立。用「動凍結產物」換表格對稱，代價高於收益。

**什麼情況該推翻**：日後要為 Phi 做完整實驗矩陣（而非補一個參照組），且有人監督，並以**新的里程碑**重新登記契約，而不是追加到 M15 上。

---

## D-020 — 工作文件不進 GitHub，並以本機 gate 取代 CI

- **日期**：2026-08-01
- **狀態**：`accepted`
- **決策**：`.claude/`、`.github/`、`CLAUDE.md`、`PLAN.md` 以 `git rm --cached` 移出版本控制並加進 `.gitignore`。**檔案保留在本機**繼續作為工作文件；**不重寫歷史**。

**理由**：使用者要求這些不出現在公開 repo。保留本機是必要的——`.claude/settings.json` 提供無人監督執行的權限 allowlist，`CLAUDE.md` 與 `PLAN.md` 是規則與進度的來源。

**不重寫歷史的取捨**：`git filter-repo` + force-push 可讓它們從舊 commit 也消失，但會改變所有 commit SHA，使 `v1.0.0` tag、GitHub Release 與 HF cards 引用的 commit hash 全部失效。使用者在知情下選擇保留歷史。**因此這四個路徑在舊 commit 中仍可見**，只是不再出現在 repo 首頁、檔案列表與 clone 內容中。

**連帶影響與補救**

| 影響 | 處置 |
|---|---|
| README 有兩個連到 `CLAUDE.md`／`PLAN.md` 的 markdown 連結會 404 | 已移除該兩列。其餘引用都是行文中的反引號提及，不會變成死連結 |
| **移除 `.github/workflows/ci.yml` 等於關掉 CI** | 新增 `scripts/check_gates.py`，一次跑完 ruff、pytest、`verify_readme`、`verify_contributors`；push 前必跑。`tests/test_check_gates.py` 釘住四道門檻不得被悄悄拿掉 |
| M14 引用的那次 CI 綠燈紀錄 | 仍存在且有效，但**之後的 push 不再有自動把關** |

**什麼情況該推翻**：若日後希望恢復 clean-checkout 的自動驗證，可在不發佈工作文件的前提下加回一個精簡 workflow。

---

## D-021 — M19 採 equal-N single-seed recipe ablation，negative result 不升級為 causal claim

- **日期**：2026-08-03
- **狀態**：`accepted-complete`
- **決策**：在 D-004 的成本限制解除後，執行 `abl_all_eqn` 與四個
  leave-one-recipe-out 組別。每組固定為 1,176 筆 real + 2,246 筆 synthetic，
  seed 42、500 steps、相同 strict 2,974-row evaluator；預先登記以 exact match
  相對 equal-N control 的 absolute delta 是否達 **2.5 percentage points**作為
  detectability threshold。

**結果**

| 排除 recipe | exact-match delta vs control（pp） | 達 2.5-point 門檻 |
|---|---:|:---:|
| `paraphrase` | +0.50 | 否 |
| `slot_substitution` | +2.02 | 否 |
| `noise_codeswitch` | -0.74 | 否 |
| `hard_negative` | +1.31 | 否 |

五組都完成 500-step training 與 2,974/2,974 strict evaluation，沒有任何差異達到
門檻。正式判讀為
`no_difference_reaches_preregistered_detectability_threshold`；
`causal_claim_allowed=false`。這是 seed 42（n=1）的 composition comparison，
不能解讀為任何 recipe「有效／無效」的獨立因果證據。

**考慮過的選項**

| 選項 | 決定 |
|---|---|
| 各 recipe 補 seeds 43/44 | 拒絕；超出 M19 預先登記範圍，也會在看到結果後追加 power |
| 以 intent accuracy 的 -2.52 points 另宣稱 `noise_codeswitch` 有效 | 拒絕；detectability metric 已凍結為 exact match，不做事後換指標 |
| 將 +2.02 四捨五入成「接近顯著」 | 拒絕；明確低於 2.5-point 門檻 |
| 完整保留 negative result 與 single-seed 限制 | 採用 |

**資源誠信**：`abl_no_paraphrase` 第一次 attempt 在 final validation 中斷，之後從
checkpoint-475 成功續跑。最終 run report 只記錄 resume session；已用原始 log
timestamps 與 SHA-256 建立 `reports/m19_runtime_audit.json`，把被捨棄 attempt 的
2.084 h 恢復到資源帳本一次，不影響模型、parser、metrics 或結果。

**什麼情況該推翻**：若未來要判定 recipe-level causal effect，需另立新里程碑，
在看新結果前登記多 seeds、power／detectability、multiple-comparison strategy 與
同筆數控制；不得把本次 `n=1` 結果事後升級。

---

<!-- 新決策從 D-022 開始往下加。格式照上面：日期 / 狀態 / 決策 / 考慮過的選項 / 理由 / 什麼情況該推翻 -->
