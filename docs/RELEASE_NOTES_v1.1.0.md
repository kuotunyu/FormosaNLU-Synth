# v1.1.0 — Release notes 草稿

> **狀態：草稿。** 這份是給使用者直接貼進 GitHub Release 的內容。
> ⏳ 標記處等 M16 robustness 批次跑完後補上數字。
> **本檔不會自動發佈**——建 tag、發 Release、上傳 HF card 都是使用者的動作。

---

## 這是一個「證據」版本，不是資料或權重版本

**發佈的 dataset 與 LoRA adapter 完全沒有改變。**

- Dataset 仍是 3,754 rows，hash 未變
- Adapter 仍是同一份 seed-42 filtered LoRA，SHA-256 未變
- Frozen thresholds、prompt、training contract、Test set 全部未動

v1.1.0 新增的是**對既有成果的獨立驗證**，以及 repository 的整理。

---

## 主要新增：跨 student family 複製

單一 student 上的提升，可能只是那個 model 的特性。v1.0.0 無法排除這個解釋。

同一份 corpus 以完全相同的 prompt、500 steps、seeds 42–44 與 strict
evaluator，在第二個 family `microsoft/Phi-4-mini-instruct`（MIT，frozen
revision `cfbefacb99257ffa30c83adab238a50856ac3083`）重跑一次三種子 paired
比較，只更換 base model。

**判準在看到任何 Phi 結果之前就凍結**：

> 對 `intent_accuracy` 與 `exact_match` 兩項，paired mean delta 在每個 family
> 都必須為正，且各自的 hierarchical 95% CI 下界都必須大於零。

| Metric | Gemma Δ [95% CI] | Phi Δ [95% CI] | 兩個 family 的 CI 都 > 0 |
| --- | ---: | ---: | :---: |
| `intent_accuracy` | +4.14 [+2.60, +5.59] | +5.09 [+1.83, +9.02] | ✅ |
| `intent_macro_f1` | +2.01 [+0.35, +3.69] | +3.36 [+0.98, +5.56] | ✅ |
| `slot_micro_f1` | +2.92 [+0.87, +4.68] | +1.80 [+0.29, +3.19] | ✅ |
| `exact_match` | +3.86 [+2.75, +4.92] | +4.71 [+1.36, +7.59] | ✅ |
| `json_valid_rate` | +1.57 [-0.01, +3.77] | +1.77 [+1.05, +2.63] | ❌ |

判準通過，結論為 **`replicated_across_student_families`**。

### 沒通過的部分

- `json_valid_rate` 未達同一條門檻，因為 Gemma 側的 CI 跨越零。它不在預先
  登記的判準內，但一併列出。
- Phi 的 `exact_match_seed_42` 在 Holm 校正後 `p = 0.141` 不顯著；另外五項
  paired tests 顯著。

### 範圍

兩個 family、一份 frozen dataset、一種 training contract。兩個 family
**分別彙總、不 pooling**，不宣稱推廣到其他 dataset、其他任務或任意 model。

---

## Robustness 擴充

v1.0.0 的 robustness 只有 Gemma 的 seed 42 兩個 adapter。現在是**兩個 family
× 三個 seed × 兩組，共十二個 adapter**，全部使用既有的 frozen 8,922-row
probe，evaluation-only，不回流訓練。

Paired delta（filtered − real_only，百分點，delta 在每個 seed 內先算再平均）：

| Metric | Gemma Δ ± SD | Phi Δ ± SD |
| --- | ---: | ---: |
| `intent_accuracy` | +3.63 ± 1.72 | +6.22 ± 3.46 |
| `intent_macro_f1` | +2.11 ± 2.19 | +4.69 ± 2.73 |
| `slot_micro_f1` | +2.75 ± 2.76 | +3.73 ± 1.23 |
| `exact_match` | +3.58 ± 2.05 | +6.98 ± 3.29 |
| `json_valid_rate` | +1.49 ± 2.35 | +1.83 ± 0.93 |

**十項全部為正，但不要讀成十個結果。** Phi 的五項 mean 都大於各自的 sample
SD；Gemma 只有 `intent_accuracy` 與 `exact_match` 如此，其餘三項在 `n=3` 下
無法與零區分。

**單一 seed 會誤導。** Gemma 只看 seed 42 時，`intent_macro_f1` 是 −0.40、
`json_valid_rate` 是 −0.38（兩項皆負）；補到三個 seed 後平均都轉正。v1.0.0
的 README 只列了正向的三項——沒有寫錯，但不完整；現在五項全列。

**附帶觀察（非預先登記）**：Phi 上 `real_syn_filtered` 的種子間變異明顯小於
`real_only`（intent accuracy SD 1.05% 對 3.24%），合成資料在該 family 上似乎
也讓訓練更穩定。

---

## 資源帳本

| 項目 | v1.0.0 | v1.1.0 |
| --- | ---: | ---: |
| Primary core | 14.440 h | **14.440 h（刻意未變）** |
| Auxiliary | 8.685 h | 19.035 h |
| 可追溯 local total | 23.124 h | **33.475 h** |
| TDP 上限包絡 | 10.406 kWh | 15.064 kWh |
| API 花費 | $0 | $0 |

新增的 10.35 小時分別是：M15 的 Phi 訓練與評估 3.755 h、M16 的 robustness
backfill 6.596 h（五個批次、十個 runs，逐批次加總而非單一時間窗，避免把批次
之間的閒置計為 GPU 時間）。

**primary core 刻意維持不變**：凍結的比較仍然只有 Gemma seed-42 矩陣，加入
第二個 student family 不應該稀釋它。M15 全部計入 auxiliary。

---

## Repository 變更

- **工作文件不再發佈**：`.claude/`、`.github/`、`CLAUDE.md`、`PLAN.md` 已移出
  版本控制（保留在本機）。歷史未重寫，因此這些路徑在舊 commit 中仍可見。
- **CI 已移除，改為本機 gate**：新增 `scripts/check_gates.py`，一次執行
  ruff、pytest、`verify_readme` 與 `verify_contributors`。push 前必跑。
- **`verify_readme` 從 54 項增加到 64 項**：新增的檢查把 README 的跨 family
  宣稱直接綁在原始 JSON 上——判準旗標必須為真、兩個 primary metric 的 CI 都
  必須排除零、五行表格全部由原始數字重新格式化比對。若結果變了，README 那句
  「複製成功」會讓 verifier 失敗，不會默默留著過期的宣稱。
- **`eval_robustness` 依 target 與 seed 參數化**：Gemma／seed 42 的路徑與
  confirm token 完全不變並有測試釘住；其他組合各有獨立輸出路徑與 token。
- **修正 `run_probe` 的 loader**：原本呼叫寫死 Gemma 的
  `load_quantized_text_model`，改為依 config 的 `model.class` 分派。這是 Phi
  的 32-row smoke 抓出來的。

---

## 取消的項目

**Phi `full_real` 上限組**（D-019）。它需要改動已凍結的 M15 pipeline，是預先
登記範圍外的組，而跨 family 的結論完全不依賴它。用「動凍結產物」換一個表格
對稱不划算。

---

## 使用者發佈步驟

1. `python -m scripts.check_gates` 全綠
2. 建 annotated tag `v1.1.0`（tagger 必須是 `kuotunyu`）
3. 用本檔內容建 GitHub Release
4. 上傳更新後的 `hf_cards/dataset_README.md` 與 `hf_cards/model_README.md`
5. 複驗 GitHub Contributors 仍只有 `kuotunyu`
