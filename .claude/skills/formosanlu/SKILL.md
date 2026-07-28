---
name: formosanlu
description: FormosaNLU（FormosaNLU-Synth）專案的脈絡恢復與工作慣例。當在這個 repo 開始新 session、問「我們做到哪了」「下一步是什麼」「當初為什麼這樣決定」、或要開始／收尾任何里程碑時使用。涵蓋目錄地圖、常用指令、記帳與 provenance 慣例、里程碑收尾 checklist。
---

# FormosaNLU 專案導航

用 LLM 合成資料提升 **Gemma 4 E4B-it** 在繁中台灣口語 NLU（intent + slot、固定 JSON 輸出）的 low-resource 表現。最終發佈到 GitHub（kuotunyu）與 Hugging Face（steven0226）。

---

## 1. 恢復脈絡（每次回來先做這幾步）

0. 先看 `docs/HANDOFF.md` 的 **📌 早晨摘要** —— 如果昨晚有 agent 獨自跑過，這裡有做到哪、卡在哪、需要使用者決定什麼。沒有夜間執行就跳過。
1. 讀 `CLAUDE.md` —— 規則。三段原文是使用者指定的，逐字保留不得改寫；`<!-- added -->` 標記的是補充條款。
2. 讀 `PLAN.md` 的 **📍 狀態區塊** —— 現在在哪個里程碑、下一步是什麼、**球在誰身上**、累計成本、有沒有阻塞。
3. 讀 `docs/DECISIONS.md` —— 為什麼當初這樣決定。**不要重新爭論已標 `accepted` 的事**；要推翻就照每筆的「什麼情況該推翻」欄判斷，並新增一筆 D-XXX 標記舊的為 `superseded`。

> 🌙 **要在無人監督下執行**（使用者睡覺時）：改讀 `docs/AUTONOMOUS_RUN.md`，那是授權書兼守則。

技術細節：**Phase 1**（recipe 規格、過濾關卡、實驗矩陣、指標定義）在 `docs/DESIGN.md`；**Phase 2**（訓練、評測、demo、發佈）在 `docs/DESIGN_PHASE2.md`。需要使用者動手的事在 `docs/instructions_for_me.md`。

---

## 2. 七個最容易踩到的專案特性

| # | 事情 | 為什麼重要 |
|---|---|---|
| 1 | **Teacher 是本機 Ollama 開放權重，不是雲端 API** | Gemini ToS 對「公開發佈蒸餾語料」有限制（D-002）。全專案不需要任何 API key，成本 $0 |
| 2 | **生成期間 4090 被佔滿數小時** | 該時段不要排任何其他 GPU 工作。teacher 與 judge **序列執行**，24GB 裝不下兩顆 |
| 3 | **Test 是翻譯腔，合成走台味可能反而扣分** | 每筆樣本必填 `style`（`massive_like` / `tw_colloquial`），見 DESIGN.md §5、R-2 |
| 4 | **去汙染是唯一允許碰 Test 的步驟** | 只排除、不挑選、隔離在單獨腳本、留稽核 log。四條缺一就是洩漏 |
| 5 | **Windows 原生、不用 WSL**（D-001） | 但程式必須維持 Linux 可重現：pathlib、UTF-8、LF、`PYTHONUTF8=1`、uv 鎖版 |
| 6 | **訓練也在本機，不上 Colab**（D-006） | 這是 CLAUDE.md【分工】原文「>30 分鐘訓練一律上 Colab」的**已核可例外**。Colab notebook 仍要產出並實跑一組驗證可攜性 |
| 7 | **Student 是 `google/gemma-4-E4B-it`，不是 Qwen3-4B**（D-007） | 三角色三家族全 Apache-2.0：teacher=Qwen3／student=Gemma 4／judge=gpt-oss。跨家族蒸餾。注意 R-9：Gemma 繁中底子可能較弱，M8 有零樣本閘門 |

---

## 3. 目錄地圖

```
CLAUDE.md    規則（先讀）          PLAN.md      進度與驗證方法
docs/        DESIGN / DECISIONS / teacher_choice / data_card
splits/      ★ 凍結的 split manifest（seed=42、SHA256）—— 必須進 git
reports/     ★ 每個里程碑的報表與圖表 —— 必須進 git
src/data/    MASSIVE 載入、稽核、正規化、split 凍結
src/synthetic/  recipes、prompt 版本、schema、generate.py
src/filtering/  七道關卡、decontaminate.py
configs/ scripts/ tests/ notebooks/ assets/ model_cards/
data/ logs/ runs/ results/   ← gitignored（可重生）
../.env                       ← 共用金鑰，在 repo 外，絕不複製進來
```

---

## 4. 常用指令

```bash
# 環境健檢（金鑰只印有/無）
python -m scripts.check_env

# split 凍結與驗證（--verify 必須得到相同 SHA256）
python -m src.data.freeze_split
python -m src.data.freeze_split --verify

# 生成（支援斷點續跑）
python -m src.synthetic.generate --pilot 500
python -m src.synthetic.generate --full

# 過濾與去汙染
python -m src.filtering.run
python -m src.filtering.decontaminate

# 測試
pytest -q
```

Ollama 相關：

```bash
ollama list
ollama ps          # 看目前常駐哪顆、佔多少 VRAM
ollama stop <model>  # 換模型前先卸載，避免 24GB 擠爆
```

> Teacher 已依 D-010 定為 `qwen3.6:27b`（17GB），judge 為
> `gpt-oss:20b`。新的大型權重下載仍須遵守當次授權。

---

## 5. 慣例

| 項目 | 慣例 |
|---|---|
| 溝通語言 | 繁體中文；**程式碼註解與 README 用英文** |
| 報表命名 | `reports/m<N>_<slug>.md`（例：`reports/m1_data_audit.md`） |
| 圖表 | 存 `assets/`；**自己產的圖自己打開看過**才能寫進報告 |
| 記帳 | `logs/cost.json` 記 GPU wall-clock 時數 + 估算電費 + 等值 API 成本對照（本專案不是美元 API 帳單） |
| Provenance | 每筆合成樣本必填九個欄位，見 DESIGN.md §3。缺一即拒收 |
| 拒絕碼 | `F<關卡編號>_<原因>`，一筆樣本只記**第一個**擋下它的關卡 |
| 數字 | 報告裡每個數字都要能從 `reports/` 或 `results/` 的原始檔重算，**不准抄畫面** |
| Commit | 每個里程碑收尾一次，訊息格式 `M<N>: <做了什麼>`。**絕不加 `Co-Authored-By` trailer** —— GitHub 會把它算進 Contributors，這個 repo 只能有 `kuotunyu` |
| Remote | **目前沒有 GitHub remote**（D-005），發佈前才建 |

---

## 6. 里程碑收尾 checklist

- [ ] 交付物齊全，且 `PLAN.md` 上那一欄的**驗證方法真的跑過**（不是「應該會過」）
- [ ] 自己產的圖表自己打開看過
- [ ] `reports/` 有對應報表
- [ ] `PLAN.md` 勾選 + 更新 📍 狀態區塊（日期、目前里程碑、下一步、球在誰身上、累計成本）
- [ ] 有新決策 → 補 `docs/DECISIONS.md`
- [ ] 有值得沉澱的 SOP → 新增／更新 `.claude/skills/` 下的 skill
- [ ] `git status` 乾淨 → `git commit`
- [ ] 給使用者「**換你做**」清單

---

## 7. 需要停下來等使用者的關卡

| 時機 | 為什麼 |
|---|---|
| M0 pull Ollama 模型前 | 19GB / 14GB 超過 2GB 下載門檻 |
| **M2 teacher/judge 選型定案後** | 一般需使用者核可；D-009 夜間執行可自動定案、早上 review |
| **M4 pilot 報告出爐後** | 一般需使用者核可；D-009 夜間執行只有六道固定門檻全過才能自動接全量 |
| 任何花錢動作 | 例如升級到雲端 API（需新註冊 + 儲值） |
| 轉 public 前 | GitHub / HF 都要使用者過目 |

---

## 8. Skill 增建排程

| 時機 | Skill | 內容 |
|---|---|---|
| ✅ 已建 | `formosanlu` | 本檔 |
| M4 後 | `formosanlu-generate` | 生成／斷點續跑／記帳 SOP、Ollama 調參與 OOM 退場 |
| M5 後 | `formosanlu-filter` | 七道關卡、漏斗報表、去汙染稽核 SOP |
| M8 後 | `formosanlu-train` | 訓練批次 SOP、`runs/` 目錄契約、斷點續跑、六組超參一致性檢查、Colab 往返 |
| M10 後 | `formosanlu-eval` | 評測 harness、主表重算、圖表產製、數字誠實性驗證 |
