# CLAUDE.md — FormosaNLU（`03-formosanlu-sdg`）工作鐵律

> **每個 session 開工前先讀這份，然後讀 `PLAN.md` 的 📍 狀態區塊，再讀 `docs/DECISIONS.md`。**
> 標示 `原文` 的段落是使用者原始指定的規則，**逐字保留、不得改寫**。
> 標示 `<!-- added 2026-07-27 -->` 的是後續補充條款，來源都能在 `docs/DECISIONS.md` 找到對應的 D-XXX。

---

## 【分工】

**原文：**

> 超過 30 分鐘的 GPU 訓練一律寫成 Colab notebook（資料解壓到 /content/data 再訓練、checkpoint 定期同步 Google Drive、支援斷點續跑、每個 notebook 用唯一 runs/ 目錄、token 只放 Colab Secrets）；本機 RTX 4090 負責資料處理、離線生成、過濾、評測、demo 與 smoke test；純 API 生成工作不需 GPU、全在本機做。

<!-- added 2026-07-27 -->
**補充：**

- **本機＝Windows 11 原生，不使用 WSL**（D-001）。理由與未來切換條件見 `docs/DECISIONS.md`。
- **合成生成改走本機 GPU**（D-002）：teacher 是本機 Ollama 上的開放權重模型，不是雲端 API。因此「純 API 生成不需 GPU」這句在本專案的實際落地是：**生成期間 4090 會被佔滿數小時**，該時段不要排任何其他 GPU 工作（含 smoke test、demo、評測）。
- ⚠️ **【本段原文的例外，經使用者核可】Phase 2 的訓練以本機 4090 為主，不上 Colab**（D-006）。六組主實驗 + 3-seed 複跑共約 10 runs，估 5–8 小時的過夜批次。原則（長訓練不佔用互動式工作階段）仍然成立，改由「過夜批次 + 斷點續跑」滿足。**Colab notebook 仍要產出**，包裝同一份 `src/training/train.py`，並實際在 Colab 跑「一組」驗證可攜性。
- **Student base model 是 `google/gemma-4-E4B-it`**（D-007），不是原計畫的 Qwen3-4B。三個角色三個家族、全 Apache-2.0：teacher = Qwen3（本機 Ollama）／student = Gemma 4／judge = gpt-oss。
- Phase 1 **不需要任何 API key**。這是 D-002 的附帶好處，發佈時也少一層合規負擔。
- 唯一已知的 Linux-only 依賴是 **vLLM**。Phase 2 評測預設用 `transformers` 批次推論（Windows 可跑）；若要補 vLLM 的吞吐數字，屆時在 WSL 掛 `/mnt/c/.../3_FormosaNLU` 跑同一份 repo，不搬家。

---

## 【實驗鐵律】

**原文：**

> 五組對照：Real-only／+Standard Aug（此案＝傳統文字增強）／+Unfiltered Syn／+Filtered Syn／（適用時）Full-real 上限；Val/Test 只用真實資料且生成端不得接觸 Test；先凍結 split manifest（seed=42、SHA256）再開始生成；全組合先 1 seed，Real-only 與最佳 Filtered 組補 3 seeds；合成標籤全自動產生；每筆合成樣本記 provenance；synthetic 沒提升就如實報告並分析原因。

<!-- added 2026-07-27 -->
**補充：**

- **第六組「等量對照」**（D-004）：`+Unfiltered Syn` 額外跑一組「隨機下採樣到與 filtered 完全相同筆數」的版本。沒有這組的話，「filtered 比 unfiltered 好」會同時混到**品質**與**數量**兩個變因，是審稿人第一個會問的問題。主表六組：

  | 組別 | 訓練資料 |
  |---|---|
  | `real_only` | 20-shot 真實 |
  | `real_std_aug` | 20-shot 真實 + 傳統文字增強 |
  | `real_syn_unfiltered_full` | 20-shot 真實 + 未過濾合成（全量） |
  | `real_syn_unfiltered_eqn` | 20-shot 真實 + 未過濾合成（下採樣至 = filtered N） |
  | `real_syn_filtered` | 20-shot 真實 + 過濾後合成 ← **主成果組** |
  | `full_real` | 完整 MASSIVE train（上限參照） |

  另加**零樣本 baseline**（未微調的 base model 直接 prompt）作為主表第一行 —— 不是訓練組，但沒有它，所有訓練組的數字就缺一個下界參照。它同時是 D-007 的閘門（詳見 `docs/DESIGN_PHASE2.md` §3）。**主表共七行。**

- **decontamination 是唯一允許碰 Test 的步驟**，且必須滿足全部四條，否則就是洩漏：
  1. 隔離在單獨腳本（`src/filtering/decontaminate.py`），不與生成流程共用 process。
  2. **只做排除，不做挑選**——Test 只能用來刪掉太接近的合成樣本，不得用來排序、加權或選最佳。
  3. 生成端 prompt **永不含 Test 內容**，一個字都不行。
  4. 留下稽核 log（被刪的樣本 id、相似度、比對到的 Test id），發佈時一併公開。

- **每筆合成樣本強制帶 `style` 欄位**（`massive_like` / `tw_colloquial`）。理由見 `docs/DESIGN.md` 的 R-2：Test 是翻譯腔，若合成資料全走台味口語，可能把模型帶離 Test 分佈導致主表掉分。兩種都產、都記，混合比例是**有記錄的設計參數**，結果正負都照實寫進 README。

- **20-shot 的真實筆數要記真實數字**：MASSIVE 各 intent 樣本數不均，抽樣用 `min(20, available)`，總數會低於 1,200。manifest 記實際值，任何文件都不准含糊寫「約 1,200」。

---

## 【工作方式】

**原文：**

> 開工先把本階段拆成 PLAN.md 里程碑並附每項的驗證方法，做完勾掉；繁中溝通、英文註解與 README；>2GB 下載或任何花錢動作先問我；套件版本、模型名稱、價格一律先上網查證再選型；自己產的圖表要自己打開檢視；每階段結束 git commit 並給我「換你做」清單；API key 絕不進 Git。

<!-- added 2026-07-27 -->
**補充 — 跨平台硬規則**（讓將來切 WSL／別人在 Linux 重現不痛）：

1. 路徑一律用 `pathlib`，**禁止硬編碟符或 `C:\`**；所有腳本從 repo 根目錄以 `python -m src.xxx` 執行。
2. 檔案讀寫**一律明確** `encoding="utf-8"`；`.gitattributes` 已設 `* text=auto eol=lf`。
3. 環境變數 `PYTHONUTF8=1` 必開——否則 Windows cp950 主控台印繁中會炸 `UnicodeEncodeError`（繁中專案必踩）。
4. 依賴用 `uv` + `requirements.txt` + `uv.lock` 鎖版；**不使用任何 Windows-only 的 shell 步驟**。

<!-- added 2026-07-27 -->
**補充 — 其他：**

- `.env` 在 **repo 外**的 `..\.env`（即 `mySyntheticData\.env`）。程式以 `python-dotenv` 明確指向該路徑讀取，**絕不複製進 repo**，也不要在 repo 內另建 `.env`。
- **「>2GB 下載先問」包含 Ollama 模型 pull**：`qwen3:30b` 是 19GB、`gpt-oss:20b` 是 14GB，都要先問過才動。
- 成本記帳（`logs/cost.json`）在本專案記的是 **GPU wall-clock 時數 + 估算電費 + 等值 API 成本對照**，不是美元 API 帳單。
- **Commit 訊息不得帶 `Co-Authored-By` trailer**（或任何共同作者標記）。GitHub 會把 co-author 算進 Contributors 清單，而這個 repo 是作品集，Contributors 只能有 `kuotunyu` 一人。
- 每個里程碑收尾的固定動作見下方 checklist，一項都不能跳。

---

## 【專案速查】

### 恢復脈絡三步驟（隔一陣子回來就跑這個）

1. 讀本檔（規則）
2. 讀 `PLAN.md` 頁首狀態區塊（現在在哪、下一步是什麼、卡在誰身上）
3. 讀 `docs/DECISIONS.md`（為什麼當初這樣決定，避免重新爭論已定案的事）

更快的方式：直接呼叫專案 skill `/formosanlu`。

### 目錄地圖

| 路徑 | 用途 | 進 git？ |
|---|---|---|
| `CLAUDE.md` / `PLAN.md` / `docs/` | 規則、進度、設計、決策 | ✅ |
| `splits/` | **凍結的 split manifest**（seed、SHA256、id 清單） | ✅ 必須 |
| `reports/` | 每個里程碑的報表與圖表 | ✅ 必須 |
| `src/data/` | MASSIVE 載入、稽核、split 凍結 | ✅ |
| `src/synthetic/` | recipes、prompt 版本、生成器 | ✅ |
| `src/filtering/` | 七道過濾關卡、去汙染 | ✅ |
| `src/training/` `src/evaluation/` `src/inference/` | Phase 2 | ✅ |
| `configs/` `scripts/` `tests/` `notebooks/` | 設定、入口腳本、測試、Colab | ✅ |
| `assets/` `model_cards/` | 圖表成品、模型卡 | ✅ |
| `data/` `logs/` `runs/` `results/` | 資料與產出（可重生） | ❌ gitignored |
| `..\.env` | 共用金鑰，**在 repo 外** | ❌ 不存在於 repo |

### 里程碑收尾 checklist

- [ ] 交付物齊全，且**驗證方法真的跑過**（不是「應該會過」）
- [ ] 自己產的圖表自己打開看過
- [ ] `reports/` 有對應的報表檔
- [ ] `PLAN.md` 勾選 + 更新頁首狀態區塊（日期、目前里程碑、下一步、累計成本）
- [ ] 有新決策就補進 `docs/DECISIONS.md`
- [ ] 有值得沉澱的 SOP 就新增／更新 `.claude/skills/` 下的專案 skill
- [ ] `git status` 乾淨、`git commit`
- [ ] 給使用者「**換你做**」清單
