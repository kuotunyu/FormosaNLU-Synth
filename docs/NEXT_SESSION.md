# NEXT_SESSION.md — 接手指南

> **給誰讀**：在新的 session 接手把這個專案跑完的 agent。
> **本檔自足**：不需要任何先前的對話脈絡。所有指令、判準與陷阱都寫在這裡。
> **最後更新**：2026-08-02，HEAD `b5c9936`

---

## 0. 三十秒摘要

FormosaNLU 用本機開放權重 teacher 生成的合成資料，提升小模型在繁體中文（台灣）
NLU（intent + slot、固定 JSON 輸出）的 low-resource 表現。

**專案已經完成並公開發佈到 v1.1.0**：

- GitHub <https://github.com/kuotunyu/FormosaNLU-Synth>（public）
- HF Dataset `steven0226/formosa-nlu-synth-v1`（3,754 rows）
- HF Model `steven0226/gemma-4-e4b-formosanlu-lora`

核心結論：合成資料的效益**在兩個獨立的 student family（Gemma 4 E4B、
Phi-4-mini）上都複製成功**，判準在看到第二個 family 的結果之前就凍結。
全流程 33.475 GPU 小時、API 花費 $0。

**剩下的只有一件實質工作：M19 per-recipe ablation。** 程式與協定都寫好了，
只差跑 GPU。

---

## 1. 開工順序

1. `CLAUDE.md` —— 工作鐵律。三段原文是使用者指定的，**逐字保留不得改寫**
2. `PLAN.md` 的 📍 狀態區塊
3. `docs/DECISIONS.md` —— 為什麼當初這樣決定。**不要重新爭論已標 `accepted` 的事**
4. **本檔**
5. `docs/M19_ABLATION_PROTOCOL.md` —— 唯一待辦的預先登記設計

也可以直接呼叫專案 skill `/formosanlu`。

---

## 2. 唯一的實質工作：M19 ablation

### 2.1 這是什麼

四個 recipe（`paraphrase`、`slot_substitution`、`noise_codeswitch`、
`hard_negative`）各自貢獻多少。D-004 當初為成本砍掉，現在補做。

**設計已經預先登記在 `docs/M19_ABLATION_PROTOCOL.md`，開跑前必讀。** 重點：

- 五組**合成筆數全部固定 2,246**（最小的 leave-one-out 大小），差別只在組成。
  這是為了排除「筆數」這個混淆變因
- `abl_all_eqn` 是同筆數的對照組
- **不與既有的 `real_syn_filtered`（3,760 筆）直接比較**——筆數不同會重新引入混淆

### 2.2 事前已定死的判讀規則（不准事後改）

三種子的 exact match sample SD 是 **0.88 個百分點**，兩組單 seed 差值的
run-to-run 不確定性約 1.24 點。

| 差異幅度 | 判讀 |
|---|---|
| **< 2.5 點** | **不可區分**。不得宣稱該 recipe 有或沒有貢獻 |
| ≥ 2.5 點 | 值得報告，但仍須標明 n=1 |

`hard_negative` 只佔 7.3%（約 164 筆），**幾乎確定測不出來**。那個 null
**不得**被寫成「hard negative 沒有用」——它只代表解析度不足。

若五組差異全部在 2.5 點內，結論就是「這個設計分辨不出來」。**那是誠實的結果，
不是失敗，也不得改寫成「所有 recipe 同等重要」。**

### 2.3 執行

```bash
# 1. 先 dry run，會印出 confirm token、五組狀態與 GPU 安全檢查
python -m scripts.m19_ablation

# 2. GPU 安全閘門全綠才執行（約 7.4 小時：5 組訓練 + 5 組評測）
python -m scripts.m19_ablation --execute --confirm M19-ABLATION-5GROUPS-4090
```

- **支援斷點續跑**：已完成的組會顯示 `train_skipped_complete`，重下同一指令不會重跑
- 產物：`runs/m19/<group>/seed_42/`、`results/m19/`、`reports/m19/`
- 批次狀態：`runs/m19/batch_report.json`

**GPU 安全閘門會擋在 `siblings_absent: false`**，只要 `2_SafeSynth` 等其他專案
有 python process 在跑就不放行。**不要繞過它。** 正確做法是等待：

```bash
# 每分鐘檢查一次，安全就自動開跑
until python -c "import sys; from src.gpu_safety import safety_status; sys.exit(0 if safety_status().get('safe') else 1)"; do sleep 60; done
python -m scripts.m19_ablation --execute --confirm M19-ABLATION-5GROUPS-4090
```

### 2.4 跑完之後的收尾（不用 GPU，約 1 小時）

1. **彙總五組結果**，比照 `reports/m10_main_results.md` 的格式寫成
   `reports/m19_ablation.md`
2. **更新 README**：新增 ablation 段落，**並同步在 `scripts/verify_readme.py`
   加檢查項**（見 §4 鐵律第 3 條）
3. **改掉 README 的 Limitations**：目前寫著「未執行 per-recipe ablation，因此
   不做單一 recipe 的 causal claim」（約 580 行），改成實際結論
4. **新增 `docs/DECISIONS.md` 的 D-021**，記錄 ablation 的結果與判讀
5. **資源帳本**：把 M19 加進 `scripts/build_m12_artifacts.py` 的
   `robustness_backfill` 之後（比照 `m15_phi4mini_training` 的寫法），
   重新產生並更新 README 的資源表
6. `python -m scripts.check_gates` 全綠後 commit + push

---

## 3. 需要使用者本人的事

**發佈 v1.2.0**（ablation 完成後才有意義，約 15 分鐘）

`gh release create`、`hf upload`、`git tag -a`、`git push origin v*`
**都在 `.claude/settings.json` 的 deny list 裡**，agent 做不到。

要執行必須：

1. **先取得使用者明確授權**（不要自己解鎖）
2. 暫時收窄 deny 規則（只開這次要用的形式，不是整片放行）
3. 執行並逐項驗證
4. **完成後立刻鎖回去**

前一次（v1.1.0）的完整做法記在 `docs/instructions_for_me.md`，照那個流程走。

---

## 4. 鐵律（違反會造成實際損害）

1. **CI 已移除（D-020）。每次 push 前必須 `python -m scripts.check_gates` 全綠。**
   五道：ruff、pytest、verify_readme、verify_contributors、verify_reproduce。
   沒跑就 push 等於沒有任何把關。
2. **commit 絕不帶 `Co-Authored-By` trailer。** GitHub Contributors 只能有
   `kuotunyu`。`.claude/settings.json` 的 `attribution.commit: ""` 已在 harness
   層擋掉，但自己也不要寫。
3. **改 README 的數字，必須在同一次修改裡更新 `verify_readme` 的檢查項。**
   實務上反過來做比較安全：先改 verifier 讓它失敗，再改 README 讓它通過，
   這樣才能確定新數字真的被綁住。目前 83 項檢查。
4. **門檻沒過是一個發現，不是障礙。** 不准為了讓流程往下走而放寬門檻、刪測試、
   跳驗證或捏造數字。
5. **不動已凍結的東西**：v1 release corpus（3,754）、M9 訓練契約（3,760）、
   frozen thresholds、Gemma primary runs、M15 預先登記判準。
6. **不修改 repo 以外的任何東西**，包含其他專案資料夾（`1_DefectForge`、
   `2_SafeSynth`）與上層的 `.env`。
7. **已發佈的 git tag 不移動。**

---

## 5. 已知陷阱（都踩過）

| 陷阱 | 說明 |
|---|---|
| **投 GPU 前先 smoke** | M16 用 32 筆 smoke 抓到 `run_probe` 呼叫寫死 Gemma 的 loader。沒先 smoke 就是三小時空轉 |
| **單一 seed 的 per-intent 數字不可靠** | 基線在最不穩的 intent 上逐 seed 可差 67 個百分點。見 `reports/m17_intent_confusion.md` |
| **等量對照不是可選的** | 只要改變資料量就會混淆。D-004、M19 都因此設計了同筆數對照 |
| **Windows MAX_PATH** | 路徑超過 260 字元時 Python `open()` 會失敗。clone 或建 venv 要選短路徑 |
| **`data/`、`runs/`、`results/` 是 gitignored** | 需要它們的測試帶 `requires_local_artifacts` marker，缺件時會 skip 而非 fail |
| **裸 `python` 指向 anaconda** | 專案一律用 `.venv/Scripts/python.exe` |
| **`du` 在深路徑會逾時並留 stackdump** | `*.stackdump` 已加進 gitignore |

---

## 6. 可選項（做不做都行，建議 ablation 之後再看）

| 項目 | GPU | 估時 | 備註 |
|---|---|---|---|
| Demo GIF | 少量 | 約 1 h | M11 標為非阻塞選配。README 目前有真實輸出的文字範例，已達成大半效果 |
| README 改英文 | ❌ | 2–3 h | `CLAUDE.md` 原文寫「英文 README」，現況繁中且已公開。**這是使用者的決定，問過再動**。verify_readme 有多項比對中文字串，得同步改 |

---

## 7. 不是待辦的事

README Limitations 裡有一條「尚未涵蓋真實 ASR log 或自然 code-switching
corpus」——那是**誠實的範圍限制**，要補得取得真實語音辨識錯誤資料，屬於新專案
等級的工作，不是收尾項目。

同樣地，`docs/DESIGN_PHASE2.md` §10 的 TMMLU+ roadmap 明確標示「只寫文字，
不實作」。

---

## 8. 完成後專案就結束了

M19 收尾 + v1.2.0 發佈之後，這個專案沒有其他待辦。若之後還想推進，方向記在
`docs/HANDOFF.md` 的「接下來的建議起點」，但那些都是新的里程碑。
