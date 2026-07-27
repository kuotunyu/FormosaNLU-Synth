# PLAN.md — FormosaNLU 里程碑與驗證

> 🌙 **無人監督執行時，先讀 [`docs/AUTONOMOUS_RUN.md`](docs/AUTONOMOUS_RUN.md)。** 那份是夜間執行的授權書與守則：預先授權範圍、卡住時的改道協定、pilot 放行門檻、硬性禁止事項、交接報告格式。
> 進度與問題寫進 [`docs/HANDOFF.md`](docs/HANDOFF.md)。

## 📍 狀態區塊（每次收尾都要更新）

| 項目 | 現況 |
|---|---|
| **最後更新** | 2026-07-27 18:12 +08:00 |
| **目前里程碑** | **M9/M10 CPU 準備完成**；M6 全量 F1–F6 完成但未達 8,000 gate |
| **下一步動作** | 使用者決定：以誠實的 3,760 筆 filtered corpus 跑 M9，或重做 generation design |
| **球在誰身上** | 使用者（只需做科學決策，不需手動操作電腦） |
| **累計 GPU 時數** | M6 generation 4.073 h；M8 零樣本 1.050 h；M2–M4 0.292 h；另有 BGE/QLoRA 短測 |
| **累計 API 花費** | $0（D-002 走本機 teacher，全專案預期維持 $0） |
| **待決事項** | 3,760 筆照實訓練 vs. 修訂 prompts 後另開一次正式生成；凍結 thresholds 不得放寬 |
| **今晚範圍** | 使用者已授權睡覺時跑 M9；目前只完成準備，**長批次尚未啟動** |
| **阻塞項** | 技術上無；長批次只等待上述資料決策與使用者睡前明確開跑 |

---

## Phase 0 — 文件層（本次）

| # | 交付物 | 驗證方法 | ✔ |
|---|---|---|---|
| M-1.1 | 目錄骨架 + 本機 `git init`（不建 remote，D-005） | `find` 對照清單；`git status` | ☑ |
| M-1.2 | `CLAUDE.md`（三段原文逐字保留 + 標記補充） | 與使用者原始訊息逐字比對 | ☑ |
| M-1.3 | `PLAN.md`（本檔，每項驗證方法非空） | 目視每列「驗證方法」欄 | ☑ |
| M-1.4 | `docs/DESIGN.md` | Known Risks 涵蓋 R-1~R-4 + 三項細部風險 | ☑ |
| M-1.5 | `docs/DECISIONS.md`（D-001~D-005） | 每筆有「考慮過的選項」與「理由」 | ☑ |
| M-1.6 | `docs/teacher_choice.md` / `docs/data_card.md` 骨架 | 章節標題齊全、`FILL AT Mx` 標記清楚 | ☑ |
| M-1.7 | `.claude/skills/formosanlu/SKILL.md` | `/formosanlu` 能喚起、內容可讓人三分鐘接回脈絡 | ☑ |
| M-1.8 | `.gitignore` / `.gitattributes` / `LICENSE` / `README.md` 骨架 | `git check-ignore` 確認 `data/` `logs/` `.env` 被擋 | ☑ |
| M-1.9 | `docs/DESIGN_PHASE2.md`（Phase 2 完整技術設計） | §0 四處與原 prompt 的差異都有「採用什麼、為什麼」；§11 Known Risks 涵蓋 R-9~R-15 | ☑ |
| M-1.10 | `docs/instructions_for_me.md`（Colab／HF／GitHub 往返 SOP 骨架） | 每個「請你做」的步驟都有預期耗時與成功確認方式的欄位 | ☑ |
| M-1.11 | D-006 / D-007 / D-008 落地到 CLAUDE.md、DESIGN.md、README、SKILL | 各檔案交叉引用一致；CLAUDE.md 對原文的例外有明確標註 | ☑ |
| M-1.12 | initial commit（**不帶 `Co-Authored-By`**） | `git log --format=%b` 不含任何 co-author trailer；`git status` 乾淨 | ☑ |
| M-1.13 | `docs/AUTONOMOUS_RUN.md`（夜間執行守則：授權、改道協定、放行門檻、禁止事項） | §5 相依表涵蓋 M0–M8；§4 門檻皆為可計算的數字，非主觀判斷 | ☑ |
| M-1.14 | `docs/HANDOFF.md`（早晨交接報告骨架） | 含早晨摘要、執行日誌、里程碑快照三區塊 | ☑ |
| M-1.15 | `.claude/settings.json`（權限 allowlist + `attribution.commit: ""`） | JSON 通過解析；allow/deny 規則數已核對；co-author trailer 由 harness 層擋掉 | ☑ |

---

## Phase 1 — 合成資料管線（本機、無 API 成本）

### M0 · 環境與骨架 ✅ 2026-07-27 驗證完成

| 交付物 | 驗證方法 |
|---|---|
| `uv` venv + `requirements.txt` + `uv.lock` | `uv pip sync` 在乾淨 venv 成功 |
| `scripts/check_env.py` 環境健檢 | 全綠：nvidia-smi 看到 4090、python、uv、git、git-lfs、Ollama 服務、磁碟餘裕、`../.env` 中各 key **只印有/無** |
| `src/**/__init__.py` 套件化 | `python -m src.data` 可 import 不報錯 |
| Ollama 設定（`NUM_PARALLEL`、`CONTEXT_LENGTH`） | `ollama list` 可見；設定值寫進 `configs/ollama.yaml`。**`OLLAMA_MODELS` 維持預設不搬**（C: 餘裕足夠，搬遷屬系統層變更） |
| **模型 pull** | ✅ **已預先授權**（D-009）。下載前檢查磁碟：若下載後 C: 低於 100GB 則停止並寫 `docs/HANDOFF.md` |

### M1 · 資料稽核 + split 凍結 ✅ 2026-07-27 驗證完成

| 交付物 | 驗證方法 |
|---|---|
| `src/data/load_massive.py`（含 R-3 的四條 fallback） | 實際載入成功，成功路徑寫死並註明在 README |
| `reports/m1_data_audit.md` + 圖表 | 必答：`utt`/`annot_utt` 的**空白分詞實況**、slot value 是否為 `utt` 的連續子字串（比例）、每 intent 樣本數分佈、slot type 分佈、有 slot 的句子佔比。圖表**我自己打開看過** |
| `src/data/normalize.py`（去空白、全半形、繁簡正規化） | 單元測試：對稽核發現的每種形態各有一個 case |
| `splits/manifest.json`（seed=42、來源 SHA256、每組 id 清單、**真實筆數**） | `python -m src.data.freeze_split --verify` 重跑得到**完全相同**的 SHA256 |

### M2 · Teacher / Judge 決策 ✅ 2026-07-27 自動定案（D-009／D-010）

| 交付物 | 驗證方法 |
|---|---|
| `docs/teacher_choice.md` | 含：Gemini ToS **原文引用 + 生效日**、三條路線比較表（本機／雲端開放權重／封閉 API）、授權矩陣、本機吞吐實測數字、judge 換家族的理由、**升級條款**（pilot 品質不足時才考慮雲端開放權重 API，需另行核可） |
| 本機吞吐實測 | 用 20 筆真實 seed 實測 tokens/s、VRAM 峰值、`NUM_PARALLEL` 掃描結果，數字進報告 |
| **自動定案** | 依 `docs/AUTONOMOUS_RUN.md` §3 的候選條件與退場順序選定，理由與實測數字寫滿報告，**早上由使用者 review**（換 teacher 只需重跑生成，程式不用改） |

### M3 · Recipes 與 prompt 版本管理 ✅ 2026-07-27 驗證完成

| 交付物 | 驗證方法 |
|---|---|
| `src/synthetic/schema.py`（Pydantic，供 Ollama `format` 用） | `model_json_schema()` 產出可被 Ollama 接受 |
| `src/synthetic/labels.py`（60 intents / 55 slot types 凍結常數） | 與 `splits/manifest.json` 記載的 label set 完全一致 |
| 4 個 recipe + `prompts/*.md`（帶版本號） | — |
| `reports/m3_recipe_samples.md` | **每 recipe 各 5 筆 dry-run 樣本貼出來給使用者看**，兩種 `style` 都要有 |

### M4 · 生成器 + Pilot ⚠️ 500 筆完成，固定 gate 未全過，M6 未放行

| 交付物 | 驗證方法 |
|---|---|
| `src/synthetic/generate.py`（async、Ollama structured output、**斷點續跑**、`logs/cost.json`） | 故意中斷後重跑，不重複、不漏、不覆蓋既有結果 |
| 500 筆 pilot | — |
| `reports/pilot_report.md` | 含：prompt/output tokens、吞吐、GPU 時數、JSON 合格率、filter 接受率、每筆 accepted 的 GPU 秒數、**全量時數預估**、品質抽樣觀察 |
| **自動放行判定** | 依 `docs/AUTONOMOUS_RUN.md` §4 的**六道門檻**，全部達標才進 M6 全量；任一項不達標就停下、寫 `docs/HANDOFF.md`、改做 M5 或 M8。**門檻不准為了放行而調降** |

### M5 · 品質過濾 ✅ BGE-M3 校準、F1–F6 pilot 與 fixed gate 完成

| 交付物 | 驗證方法 |
|---|---|
| `src/filtering/` 七道關卡（見 DESIGN.md） | `tests/` **每道關卡各有 pass 與 fail 案例**，`pytest` 全綠 |
| `src/filtering/decontaminate.py`（隔離、只排除、留 log） | 稽核 log 有被刪樣本 id + 相似度 + 對到的 Test id |
| filtered / unfiltered 雙版本 + 每筆 provenance | schema 驗證：provenance 欄位無缺漏 |
| pilot 資料的漏斗表 | 各階段刪除數加總 = 生成數 − 最終數（對得起來） |

### M6 · 全量生成 + 過濾 ⚠️ 完成，但 3,760 筆未達 8,000 gate

| 交付物 | 驗證方法 |
|---|---|
| filtered 8,000–10,000 筆 | ⚠️ 實得 3,760（33.38%）；主要為 4,596 筆 synthetic duplicates，不調門檻硬湊 |
| `reports/generation_report.md` | ✅ 11,264-row 生成總帳、F1–F6 漏斗、hash、mode-collapse 分析、M9 影響 |
| `data/formosa_synth_v1/{filtered,unfiltered}/` | ⚠️ M9 候選檔與 376-row F7 audit manifest 已完成；judge GPU 執行與 release packaging 待後續 |

### M7 · 收尾

| 交付物 | 驗證方法 |
|---|---|
| `docs/data_card.md` 草稿（方法、teacher、授權、限制） | 文件完整性自查表 |
| PLAN 勾選 + 狀態區塊更新 + `git commit` | `git status` 乾淨 |
| 「換你做」清單 | 交付給使用者 |

---

## Phase 2 — 微調 / 評測 / Demo / 發佈

> 技術設計在 **`docs/DESIGN_PHASE2.md`**。原始 Phase 2 prompt 與本專案鐵律有四處矛盾，全部在該文件 §0 記載了「prompt 說什麼、我們採用什麼、為什麼」。
> Student = `google/gemma-4-E4B-it`（D-007）；訓練以**本機 4090** 為主（D-006）。

### M8 · 訓練管線 + 零樣本 baseline ✅ 完成

| 交付物 | 驗證方法 |
|---|---|
| 超參查證（LoRA rank/alpha/target_modules、lr、scheduler、seq len、`max_steps`） | 上網查證當前建議後定案，寫進 `configs/train.yaml`；**六組共用同一份** |
| `src/training/train.py` + `prompt_template.py`（帶版本號） | 1-step smoke test 在本機跑通；訓練與推論兩端用**完全相同**的模板 |
| `src/training/train_all.py` / `scripts/train_all.py` 批次入口 | 故意中斷後 `resume_from_checkpoint` 能正確續跑（**開跑前必須先驗過**，R-13） |
| 下載 `google/gemma-4-E4B-it` | ✅ **已預先授權**（D-009）；記錄實際大小與 VRAM 佔用（R-12：確認能否只載語言塔） |
| **零樣本 baseline**（未微調 base model 跑真實 Test） | 2,974/2,974；JSON-valid 17.38%、intent accuracy 10.66%、macro-F1 23.12%、slot F1 0%、exact 8.10%；無 constrained decoding |

### M9 · 六組訓練（本機批次）+ Colab 可攜性驗證　🟡 **啟動準備完成**

> 使用者已看過 M8 並授權睡覺期間使用 GPU。六組資料、Standard Aug、
> batch resume 與 evaluation dry plan 已驗證；長批次尚未啟動，先處理 M6
> 只有 3,760 筆通過的科學決策。

| 交付物 | 驗證方法 |
|---|---|
| 六組 × 1 seed，`runs/<group>/seed_<n>/` 各自獨立 | ✅ dry plan / inputs；實際六份 snapshot 等正式 run 完成後比對 |
| `real_only` 與最佳 filtered 組補到 3 seeds（合計約 10 runs） | 每個 run 有 `metrics.jsonl`、`adapter/`、`env.json` |
| 過夜批次（估 5–8 h） | ✅ 1→2 step 跨程序 resume 實測；正式 batch 未啟動 |
| `notebooks/01_sft_student.ipynb`（包裝同一份 `train.py`） | ✅ notebook / bundle / 120 秒 Drive sync / resume preflight；Colab 實跑一組仍待使用者操作 |
| `docs/instructions_for_me.md` 的 Colab 章節填實 | ✅ 上傳檔、GPU 門檻、Secrets、續跑、下載與成功確認皆已填實 |

### M10 · 評測

| 交付物 | 驗證方法 |
|---|---|
| `src/evaluation/`（`run_adapter` / `parse` / `metrics` / `probe` / `report`）+ `scripts/eval.py` CLI | ✅ CPU 程式與測試完成；trained adapter GPU inference 待 M9 |
| **主表七行**（零樣本 + 六組）× 全指標 | 🟡 產生器已完成，zero-shot 列已回填；六個 trained rows 等 M9/M10 |
| 差距補回率 | 同時報絕對差值；分母過小時標註「此比率不可靠」（R-11） |
| per-intent 進步排序 | 最進步與**退步最多**都要列（退步的通常最能說明失敗模式） |
| Robustness 探測集 | ✅ 2,974 Test × 3 種 slot-safe 擾動＝8,922 筆；manifest/hash 完成，明確 evaluation-only |
| 效能表 | tokens/s、VRAM 峰值、單筆 latency |
| **不使用 constrained decoding** | code review 確認：JSON-valid rate 是要量的指標，強制合法會讓它恆等 100% |

### M11 · Gradio demo

| 交付物 | 驗證方法 |
|---|---|
| 本機 Gradio：輸入繁中句 → intent / slots / 原始 JSON / latency | 併列**微調前 vs 微調後**同一句的輸出 |
| 預載示範句，含一組易混淆 minimal pair | 例：「播放周杰倫」vs「搜尋周杰倫的歌」，直接展示 hard negative recipe 的效果 |
| README GIF | **自己錄自己打開看過** |

### M12 · README + 數字誠實性

| 交付物 | 驗證方法 |
|---|---|
| README 依 D-008 排版（主標＝差距補回率 → 過濾管線價值 → $0/4090 → robustness 輔助） | 骨架順序符合 `docs/DESIGN_PHASE2.md` §7 |
| 方法流程圖、資料漏斗圖、七行主表、資源總帳、Limitations（含負面結果） | 圖表**自己打開看過** |
| `scripts/verify_readme.py` | 跑給使用者看：README 每個數字都能從 `runs/*/metrics.jsonl` 與 `reports/` 重算 |
| 選配 roadmap 段落（台灣知識蒸餾 + TMMLU+ / twinkle-eval） | **只寫文字，不實作** |

### M13 · 發佈前總驗收 → 發佈 → ⛔ 需使用者核可

| 交付物 | 驗證方法 |
|---|---|
| 重現性 | 全新虛擬環境照 README 的 Reproduce 走一遍（訓練步驟用縮小規模驗流程） |
| 數字誠實性 | `verify_readme.py` 全綠 |
| 防洩漏自查 | 確認生成管線與過濾器從未讀 Test；`src/synthetic/` 的 import 稽核；split manifest / seed / SHA256 齊全且與實際一致；去汙染 log 完整 |
| 授權相容性 | 資料集（MASSIVE CC BY 4.0 + teacher Apache-2.0）／adapter（Apache-2.0）／程式碼（MIT）標註齊全 |
| 安全掃描 | 全 repo 掃 API key、個人絕對路徑、個資 |
| HF 上傳 | dataset `steven0226/formosa-nlu-synth-v1`、model `steven0226/gemma-4-e4b-formosanlu-lora`，雙語 card |
| GitHub | 此時才 `gh repo create kuotunyu/03-formosanlu-sdg`（先 private，D-005）；**commit 不帶 `Co-Authored-By`** |
| 一頁驗收報告 | 通過項／修正項／殘留風險；**使用者說 OK 才轉 public** |

### Phase 2 資源預估

| 項目 | 估計 |
|---|---|
| 本機 GPU（10 runs） | 5–8 小時，過夜批次 |
| Colab units | 約 1.5 小時（只驗證一組），其餘配額留給專案一、二 |
| API 花費 | **$0** |

---

## 專案 skill 增建排程

| 時機 | Skill | 內容 |
|---|---|---|
| 本次 | `formosanlu` | 恢復脈絡、目錄地圖、慣例、收尾 checklist |
| M4 後 | `formosanlu-generate` | 生成／斷點續跑／記帳 SOP，Ollama 調參與 OOM 退場 |
| M5 後 | `formosanlu-filter` | 七道關卡、漏斗報表、去汙染稽核 SOP |
| M8 後 | `formosanlu-train` | 訓練批次 SOP、`runs/` 目錄契約、斷點續跑、六組超參一致性檢查、Colab 往返 |
| M10 後 | `formosanlu-eval` | 評測 harness、主表重算、圖表產製、數字誠實性驗證 |
