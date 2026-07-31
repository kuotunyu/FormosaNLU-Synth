# AUTONOMOUS_RUN.md — 無人監督執行守則

> **給誰讀**：在使用者睡覺時獨自執行本專案的 agent（Claude Code、Codex 或其他）。
> **開工順序**：`CLAUDE.md` → `PLAN.md` 的 📍 狀態區塊 → `docs/DECISIONS.md` → **本檔** → 開始做。
> **授權來源**：使用者於 2026-07-27 明示授權下列全部項目。本檔即授權書。
>
> **2026-07-27 M9 修訂**：本檔原先的 M9 禁令已完成「先讓使用者看過 M8」
> 的目的。使用者之後另行指定睡覺時執行 M9；只有在使用者明確說
> 「開始跑 M9」後，才依 `docs/M9_OVERNIGHT_RUNBOOK.md`、D-014 與 D-015 啟動。
> 本檔其餘安全、誠實性與對外寫入禁令繼續有效。
>
> **2026-07-31 M16 修訂（今夜適用）**：使用者明示「希望一覺醒來專案幾乎完成，
> 只剩下少數需要我操作的部分」，並授權睡眠期間自由使用 GPU（約 12 小時、
> 無其他專案佔用）。今夜範圍見下方 §11。**§7 的對外寫入禁令部分放寬：
> `git push` 已獲明確授權；HF 上傳、tag 與 Release 仍然禁止，留給使用者早上處理。**

---

## 0. 三十秒版本

1. 從 `PLAN.md` 第一個未勾選的里程碑開始，依序往下做。
2. 每個里程碑的「驗證方法」**必須真的執行**。沒過就停在那裡，不要往下堆。
3. 卡住 → 寫進 `docs/HANDOFF.md` → **改做下一個不相依的里程碑**（相依表見 §5），不要整條停住。
4. **今晚的終點是 M8 的零樣本 baseline。絕對不要開始 M9 訓練批次。**
5. 收工前：`git commit`、更新 `PLAN.md` 狀態區塊、把 `HANDOFF.md` 的「早晨摘要」寫完。

---

## 1. 今晚的範圍

| 里程碑 | 在範圍內？ |
|---|---|
| M0 環境與骨架 | ✅ |
| M1 資料稽核 + split 凍結 | ✅ |
| M2 teacher/judge 選型（**自動定案**） | ✅ |
| M3 recipes + prompts + schema | ✅ |
| M4 生成器 + 500 筆 pilot | ✅ |
| M5 過濾管線 + 單元測試 | ✅ |
| M6 全量生成 + 過濾（**須通過 §4 門檻**） | ✅ 有條件 |
| M7 data_card 草稿 | ✅ |
| M8 訓練管線骨架 + **零樣本 baseline** | ✅ |
| **M9 六組訓練批次** | ❌ **明確排除**。5–8 小時的批次留給明天晚上，使用者要先看過 M8 的零樣本結果 |
| M10–M13 評測 / demo / README / 發佈 | ❌ 排除 |

---

## 2. 預先授權（不必問，直接做）

| # | 項目 | 條件 |
|---|---|---|
| 1 | `ollama pull` teacher 與 judge 模型（合計約 33GB） | 下載前檢查磁碟，見 §6 |
| 2 | 下載 MASSIVE `zh-TW` 資料集 | — |
| 3 | 下載 student 權重 `google/gemma-4-E4B-it`（約 10GB 級） | 下載前檢查磁碟 |
| 4 | **M2 teacher/judge 選型自動定案** | 依 §3 的規則，理由寫滿 `docs/teacher_choice.md` 供早上 review |
| 5 | **pilot 通過門檻即自動接全量生成** | 依 §4 的門檻，全部達標才放行 |
| 6 | 安裝 Python 套件（`uv` / `pip install`） | 只裝專案需要的；記進 `requirements.txt` 並鎖版 |
| 7 | 建立、修改、刪除 repo 內的檔案 | `data/` `logs/` `runs/` `results/` 內可自由重生；其餘檔案修改前先確認內容 |
| 8 | `git add` / `git commit`（每個里程碑一次） | commit 訊息格式 `M<N>: <做了什麼>` |

### 關於 Ollama 模型存放位置

**不要動 `OLLAMA_MODELS`。** 原本考慮改指 D: 槽，但 C: 尚有約 203GB，33GB 綽綽有餘，而搬遷需要改系統環境變數並重啟 Ollama 服務——那是系統層變更，不在授權範圍。維持預設的 `C:\Users\3Hml\.ollama`。

---

## 3. M2 自動定案規則

方向已由 **D-002** 定死（本機開放權重 Qwen 家族 teacher、換家族 judge）。M2 只是把型號選定，規則如下：

**Teacher 候選必須全部滿足：**

1. Qwen 家族（保住跨家族蒸餾，student 是 Gemma 4）
2. 授權 Apache-2.0
3. Ollama library 上取得得到
4. 量化後 ≤ 20 GB（24GB 卡要留 KV cache 餘裕）
5. 實測支援 Ollama 的 `format` structured output

**選擇順序**：先上網查證當前世代有什麼 → 挑滿足上述條件中最強的 → 實測吞吐 → 若 OOM 或吞吐不足，依序退 `qwen3:30b` → `qwen3:14b`。

**Judge**：`gpt-oss:20b`。除非裝不下或跑不動，才另找**非 Qwen、非 Gemma** 的 Apache-2.0 開放權重模型。

**必須寫進 `docs/teacher_choice.md`**：候選清單與查證日期、每個候選的授權出處網址、`NUM_PARALLEL` 掃描的實測數字、最終選擇與理由、以及「使用者早上可以改，改了只要重跑生成、程式不用動」這句話。

---

## 4. Pilot → 全量的放行門檻

在 `reports/pilot_report.md` 產出後自動判定。**全部達標才放行**；任一項不達標就停下 M6，改做 §5 的下一項。

| # | 指標 | 門檻 |
|---|---|---|
| 1 | F1 JSON schema 合格率 | **≥ 95%** |
| 2 | F1–F3 累積通過率（schema + label 合法 + groundedness） | **≥ 70%** |
| 3 | F1–F6 累積通過率（含去重與去汙染） | **≥ 45%** |
| 4 | judge 抽審 50 筆的判定通過率 | **≥ 80%** |
| 5 | 全量預估 wall-clock | **≤ 5 小時** |
| 6 | 預估最終 filtered 產出 | **≥ 8,000 筆** |

**第 6 項不達標的唯一合法處置**：提高生成量重新估算，且必須同時仍滿足第 5 項。**不准調降 8,000 這個目標。**

**門檻本身不准改。** 若你認為某個門檻訂得不合理，把理由寫進 `HANDOFF.md` 讓使用者早上判斷——不要自己改了然後放行。

---

## 5. 卡住時：停損與改道協定

### 什麼算「卡住」

- 里程碑的驗證方法沒通過，且**修過兩次仍失敗**
- 需要使用者判斷、花錢、或對外操作
- 權限被拒（表示該動作不在授權範圍）
- 觸及 §7 的硬性禁止事項

### 卡住時做什麼

1. **不要重試第三次。**
2. 在 `docs/HANDOFF.md` 新增一筆：里程碑、卡在哪一步、完整錯誤訊息／traceback、你試過的兩種修法、你建議的下一步、需要使用者決定什麼。
3. 依下表**改做下一個不相依的里程碑**。
4. 若所有剩餘里程碑都相依於卡住的那一項，就收工（見 §9）。

### 相依表與改道順序

| 里程碑 | 相依於 | 卡住時改做 |
|---|---|---|
| M0 | — | 卡住就收工（後面全部相依 M0） |
| M1 | M0 | M5（過濾管線可用假資料先寫 + 測試） |
| M2 | M0 | M1 → M5 |
| M3 | M1, M2 | M5 → M8 零樣本 |
| M4 | M3 | M5 → M8 零樣本 |
| M5 | M3 的 schema | M8 零樣本 |
| M6 | M4, M5 | M8 零樣本 → M7 骨架 |
| M7 | M6 | M8 零樣本 |
| M8 零樣本 | M1（真實 Test）+ student 權重 | 收工 |

**M5 與 M8 零樣本是兩張萬用救援牌**：M5 的七道關卡與單元測試可以用手寫的假樣本先做完，完全不需要 teacher；M8 零樣本只需要 M1 的 Test 與 student 權重，跟 M2–M7 全部無關。

---

## 6. 資源護欄

| 資源 | 規則 |
|---|---|
| 磁碟 | 任何下載前先檢查 C: 剩餘空間。**若下載後會低於 100 GB，停止並寫 HANDOFF。** |
| GPU | **同時只跑一個 GPU 工作。** teacher 與 judge 序列執行（24GB 裝不下兩顆），換模型前先 `ollama stop` |
| 生成時間 | 全量生成超過 §4 第 5 項預估的 **1.5 倍**仍未完成 → 中止、保留已完成的部分（斷點續跑用）、寫 HANDOFF |
| 產出體積 | `data/` + `logs/` 合計超過 **50 GB** → 停止並寫 HANDOFF |
| 網路 | 只從 Hugging Face 與 Ollama library 下載。**不要下載任何其他來源的模型或資料** |

---

## 7. 硬性禁止（無論如何都不做）

1. **任何對外寫入**：`git push`、建立 remote、`gh` 任何指令、上傳到 Hugging Face、發佈任何東西。
2. **任何花錢動作**：註冊雲端 API、儲值、呼叫付費服務。授權範圍內的一切都是 $0。
3. **讀取 `../.env`**。本專案 Phase 1 不需要任何 API key。要檢查金鑰存在與否，用程式判斷並**只印有/無**，絕不把內容讀進上下文。
4. **修改 repo 以外的任何東西**：系統環境變數、其他專案資料夾、上層的 `.env`、Ollama 服務設定。
5. **下載授權清單以外的模型**。想換 teacher 就照 §3 的規則在候選內選，不要自己擴大範圍。
6. **開始 M9 訓練批次**。
7. **破壞性 git 操作**：`reset --hard`、`clean`、`checkout --`、`rebase`、`commit --amend`、任何歷史重寫。
8. **在 commit 訊息加 `Co-Authored-By` 或任何共同作者標記。**（`.claude/settings.json` 的 `attribution.commit: ""` 已在 harness 層擋掉，但你自己也不要寫。）

> 若你不是 Claude Code（例如 Codex），`.claude/settings.json` 的 allowlist 對你無效，**上述禁止事項請自行嚴格遵守**。

---

## 8. 誠實性鐵律（最重要的一節）

無人監督時最大的風險不是做不完，是**為了做完而作弊**。以下行為一律禁止：

- ❌ 為了讓流程往下走而**放寬過濾門檻**、調降 §4 的數字、放寬 label 檢查
- ❌ **刪減或跳過測試**、把失敗的測試標成 skip、改小斷言讓它通過
- ❌ 把沒跑過的驗證方法**當成跑過**
- ❌ **捏造數字**、從畫面抄數字、估一個看起來合理的值填進報告
- ❌ 把「門檻沒過」寫成「大致上通過」

**門檻沒過是一個發現，不是一個障礙。** 使用者要的是真實結果，包含失敗。把它照實寫進 `HANDOFF.md` 與 `reports/`，那比一份漂亮但假的報告有價值得多——這也是實驗鐵律「synthetic 沒提升就如實報告」的同一個原則。

不確定就停下來寫進 HANDOFF，**不要猜**。

### 圖表

自己產的圖表要自己用 Read 開起來看過（多模態可讀 PNG），確認軸標、圖例、數值合理，並把「看過、結論是什麼」寫進對應的報告。看不出來就在 HANDOFF 標記為待使用者確認。

---

## 9. 交接報告協定

`docs/HANDOFF.md` 是使用者早上第一個會看的檔案。

**更新時機**（不是只有最後一次——你可能在凌晨四點掛掉，要讓使用者知道進度到哪）：

1. 每個里程碑**開始**時：加一行「開始 Mx，時間 T」
2. 每個里程碑**結束**時：寫產出、驗證結果、花費時間
3. **每次卡住**時：依 §5 的格式寫一筆
4. **收工前**：寫「早晨摘要」

**早晨摘要必須包含：**

- 完成到哪個里程碑、各花多久
- **需要使用者決定的事**（列成清單，最重要的放最前面）
- 需要使用者 review 的產出（尤其 `docs/teacher_choice.md`、`reports/pilot_report.md`、M8 零樣本結果）
- 卡住的項目與建議處置
- 資源用量：GPU 時數、磁碟增加量
- 明天的建議起點

---

## 10. 收工

滿足任一條件即收工：

- M8 零樣本 baseline 完成
- 所有剩餘里程碑都被卡住的項目擋住
- 觸發任何一條資源護欄

**收工動作（一項都不能跳）：**

1. 確認沒有 GPU 工作還在跑（`ollama ps`）
2. 更新 `PLAN.md` 的 📍 狀態區塊（日期、目前里程碑、下一步、球在誰身上、累計 GPU 時數）
3. 把已完成里程碑的 checkbox 勾掉——**只勾驗證方法真的跑過的**
4. 補齊 `docs/DECISIONS.md`（M2 的定案、任何過程中的新決策）
5. 寫完 `docs/HANDOFF.md` 的早晨摘要
6. `git add -A && git commit`（不帶任何 co-author trailer）
7. `git status` 確認乾淨

---

## 11. 2026-07-31 夜間範圍（M16 收尾 + robustness 補齊）

**前提**：使用者重開機後、睡前才啟動；GPU 約 12 小時無人使用。先跑 GPU
safety gate（沿用既有的兩次連續閒置取樣），沒過就等，不要硬開。

### 11.1 GPU 工作（依序，估約 8 h）

| # | 工作 | 估時 | 契約 |
|---|---|---|---|
| 1 | Gemma robustness 補 seeds 43/44 | 4.2 h | 用**現有 frozen 8,922-row probe**，evaluation-only，不回流訓練 |
| 2 | Phi robustness seed 42 | 1.0 h | 同一 probe、同一 evaluator |
| 3 | Phi robustness seeds 43/44 | 2.0 h | 同上 |
| 4 | Phi `full_real` 上限組（訓練 + 評估） | 0.7 h | ⚠️ **post-hoc / exploratory**，預先登記範圍之外 |
| 5 | README demo GIF（選配） | 數分鐘 | 非阻塞，跑不出來就跳過 |

**第 4 項的紅線**：`full_real` 是**新增的參照組**，不得用來改動或重算 M15 預先
登記的 `real_syn_filtered` vs `real_only` paired 判準。報告中必須明確標示為
post-hoc，且與預先登記結果分開呈現。

**任一項失敗**：照 §5 寫進 `docs/HANDOFF.md`，改做下一項，不要卡住整條。
robustness 各組彼此獨立，單組失敗不影響其他組。

### 11.2 非 GPU 工作

1. README：TL;DR 升級為跨 family 複製；Roadmap 移除已完成的 M15；新增
   cross-model 段落；**改完必須 `scripts/verify_readme.py` 全綠**，新增的
   數字要一併加進 verifier 的檢查項（不准只改 README 不加檢查）。
2. `reports/m12_resource_ledger.json` 補 M15（3.75 h）與今夜各階段實測時數。
3. PLAN.md、HANDOFF.md、`docs/DECISIONS.md`、`docs/data_card.md` 同步。
4. 補建 PLAN 排程但尚未建立的四個 skill：`formosanlu-generate`、
   `formosanlu-filter`、`formosanlu-train`、`formosanlu-eval`。
5. 起草 v1.1.0 release notes 與 HF card 更新內容，**只寫檔案、不發佈**。
6. 每完成一塊就 commit + **push**（push 已獲授權）。

### 11.3 今夜的硬性禁止（在 §7 之外額外強調）

- ❌ **不得** `hf upload` / 更新 HF Dataset 或 Model card 的線上內容
- ❌ **不得**建立 git tag 或 GitHub Release
- ❌ **不得**動 v1 release corpus、frozen thresholds、Gemma primary runs、
  M15 預先登記判準、或任何既有 prediction JSONL
- ❌ **不得**新增第三個 student family（判準是兩個 family，事後擴充會傷敘事）

### 11.4 早上留給使用者的

`docs/HANDOFF.md` 的早晨摘要要把這幾項列成清單：v1.1.0 tag 與 Release、
HF Dataset／Model card 上傳、以及任何需要判斷的殘留項。
