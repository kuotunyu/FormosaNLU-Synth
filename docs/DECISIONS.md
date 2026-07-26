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
| 遷移到 WSL2（原 portfolio plan 的預設） | 要搬 repo、重裝 Python 環境、重登 gh／hf、Ollama 要重來；`.env`、conda、uv 0.11.18、gh 2.96、git-lfs 全在 Windows 側 |
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
- **狀態**：`accepted`（最終型號 `pending`，M2 實測後補記）
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
2. 成本 $0，且**任何有一張 4090 的人都能完整重現**——這比「總共花了 $X」是更強的作品集敘事。
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
| 全部本機、不做 Colab notebook | 最省事，但少掉「會寫 Colab 訓練 notebook」這個可展示的工程能力，而原 portfolio 計畫是把它當交付物的 |

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
- 台味那一軸若因 R-2 在主表為負，就誠實列進 Limitations —— 負面結果加分析比選擇性報告更有面試價值（這本來就是實驗鐵律的要求）。

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

<!-- 新決策從 D-011 開始往下加。格式照上面：日期 / 狀態 / 決策 / 考慮過的選項 / 理由 / 什麼情況該推翻 -->
