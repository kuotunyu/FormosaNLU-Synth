# Teacher / Judge 選型與授權分析

> **狀態：M2 自動定案完成，等待使用者 review。**
> 依 D-009 的無人監督授權，M2 可以按照數字判準自動定案；使用者早上仍可改，
> 改了只需重跑生成，程式不用改。
>
> 型號、授權、價格與服務條款查閱日：**2026-07-27**。

---

## 1. 決策摘要

Teacher 定為 `qwen3.6:27b`：它是目前 Ollama 上可取得、Apache-2.0、量化後
不超過 20GB 的最新 Qwen 候選，並在 RTX 4090 上通過 structured output 與吞吐
實測。Judge 維持 `gpt-oss:20b`，與 teacher／student 不同家族；F5/F6 embedding
定為 `BAAI/bge-m3`，但 M2 **沒有下載** embedding 權重。

| 角色 | 選定模型 | 授權 | 定案日 |
|---|---|---|---|
| Teacher | `qwen3.6:27b`（Ollama ID `a50eda8ed977`） | Apache-2.0 | 2026-07-27 |
| Judge | `gpt-oss:20b`（Ollama ID `17052f91a42e`） | Apache-2.0 | 2026-07-27 |
| Embedding（F5/F6） | `BAAI/bge-m3` | MIT | 2026-07-27 |
| Student（D-007） | `google/gemma-4-E4B-it` | Apache-2.0 | 2026-07-27 |

三個生成／訓練／審查角色分屬 Qwen／Gemma／gpt-oss 三個家族。Teacher 若改成
Gemma，會破壞跨家族蒸餾這個實驗優點。

---

## 2. 路線比較

| 路線 | 代表模型 | 2026-07-27 價格 | 發佈蒸餾語料的風險 | 結論 |
|---|---|---:|---|---|
| 封閉模型 API | Gemini 3.1 Flash-Lite Batch | $0.125 input / $0.75 output，每 1M tokens | Gemini Additional Terms 禁止用服務開發競爭模型；公開語料的下游用途不可控 | **否決** |
| 雲端開放權重 API | Together 上的 Qwen3.6-Plus | $0.50 input / $3.00 output，每 1M tokens | 權重授權可行；serving ToS 仍須在實際採用前重查 | 只作需核可的升級路徑 |
| 本機開放權重 | Ollama + Qwen3.6 | **$0 API** | Apache-2.0；輸出可發佈 | **採用** |

價格來源：[Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing)、
[Together pricing](https://www.together.ai/pricing)。價格只是當日快照，不寫進程式。

---

## 3. Gemini Additional Terms

- 來源：[Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)
- Effective date：2026-03-23
- 查閱日：2026-07-27

與本專案直接相關的限制原文（16 words）：

> “You may not use the Services to develop models that compete with the Services”

Google 同頁說明不會主張生成內容的所有權，但使用者仍須自行確保分享與使用生成
內容合法。付費層「不拿 prompts/responses 改善產品」解決的是 Google 的資料使用，
沒有解除上面的競爭模型限制。本專案會把蒸餾語料公開給第三方訓練任意模型，沒有
必要承擔這個合規灰區。

---

## 4. 開放權重授權矩陣

| 模型 | 官方證據 | 結論與義務 |
|---|---|---|
| Qwen3.6-27B | [Qwen3.6 官方 repo](https://github.com/QwenLM/Qwen3.6)、[HF model card](https://huggingface.co/Qwen/Qwen3.6-27B) | Apache-2.0；保留授權與 NOTICE |
| Ollama `qwen3.6:27b` | [Ollama tags](https://ollama.com/library/qwen3.6/tags) | Q4_K_M 17GB，符合 ≤20GB 護欄 |
| gpt-oss-20b | [OpenAI announcement](https://openai.com/index/introducing-gpt-oss/)、[model card](https://huggingface.co/openai/gpt-oss-20b) | Apache-2.0；官方稱 16GB memory 可跑 |
| Gemma 4 | [Google Gemma 4 Apache license](https://ai.google.dev/gemma/apache_2)、[model overview](https://ai.google.dev/gemma/docs/core) | Apache-2.0；舊版 Gemma Terms 不適用 Gemma 4 |
| BGE-M3 | [BAAI model card](https://huggingface.co/BAAI/bge-m3) | MIT；100+ languages、1024-d、最長 8192 tokens |

本專案的句子很短，BGE-M3 的長 context 不是主要賣點；選它是因為多語（含中文）
與成熟的 dense embedding 工具鏈。M5 只用 dense vector，不引入 sparse／ColBERT，
避免增加無關變因。

---

## 5. Teacher 實測

### 方法

- 硬體：RTX 4090 24GB；Ollama 0.32.0；Windows 原生
- 模型：`qwen3.6:27b`，27.8B dense，Q4_K_M，stored size 17GB
- 輸入：`splits/manifest.json` 中 20 個不同 intent 的真實 train seed
- 任務：label-preserving paraphrase，Pydantic JSON Schema 傳入 Ollama `format`
- 固定：`num_ctx=4096`、temperature 0、每筆固定 seed
- 原始結果：`reports/m2_teacher_benchmark.json`

Ollama 官方支援把 Pydantic `model_json_schema()` 傳給 `format`：
[Structured outputs](https://docs.ollama.com/capabilities/structured-outputs)。

### 結果

| Client concurrency | Wall time（20 筆） | 聚合 tok/s | Ollama model VRAM 峰值 | 全 GPU memory 峰值 | JSON 合格 | intent/slot/grounding 全對 |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 22.63 s | 29.91 | 15,820 MiB | 18,277 MiB | 20/20 | 18/20 |
| 4 | 18.88 s | **35.86** | 15,820 MiB | 18,277 MiB | 20/20 | 18/20 |
| 8 | 18.88 s | 35.86 | 15,820 MiB | 18,275 MiB | 20/20 | 18/20 |

結論：

- Structured output 為 100%；模型、授權、大小、Ollama 取得性五項硬條件全過。
- Concurrency 4 比 1 快 19.9%，8 沒有額外收益，因此 `num_parallel/client
  concurrency = 4`。
- 兩筆 task-invalid 都是模型改寫了 slot value 的字面（`星期二的`→`星期二`、
  `會議`→`開會`），JSON 與 label 仍合法，但 groundedness 會由 F3 正確拒收。
- 20 筆 dry-run 的 F1–F3 通過率 90%，高於 M4 的 70% 放行門檻；沒有理由退回
  `qwen3:30b` 或 `qwen3:14b`。

這 20 筆是吞吐／契約 smoke benchmark，不取代 M4 的 500 筆 pilot，也不能拿來
調低 M4 門檻。

---

## 6. Judge 實測

用 teacher benchmark 最快一組的 20 筆輸出，固定 temperature 0、client concurrency
4，換兩組 request seed 各審一次。原始結果在
`reports/m2_judge_benchmark.json`。

| Pass | Wall time | 聚合 tok/s | JSON 合格 | accepted |
|---:|---:|---:|---:|---:|
| 1 | 34.00 s | 27.80 | 20/20 | 18/20 |
| 2 | 34.29 s | 28.12 | 20/20 | 17/20 |

四個布林判定（accepted／intent／slots／natural）一致率為 **19/20 = 95%**。
不一致的樣本是「設一個早上六點的鬧鐘」；一輪判自然，一輪認為應寫「設定」。
這顯示 judge 適合作抽審與漏檢率估計，不應被當成絕對真值。

重要運維發現：對 Ollama 的 gpt-oss request 傳 `think: false` 會得到空的
`message.content`；移除該欄並在 system prompt 使用 `Reasoning: low` 後為 40/40
JSON-valid。M4/M5 的 judge client 必須沿用這個設定。

Teacher 與 judge 都已在實測後卸載；兩顆模型不會同時常駐。

---

## 7. Pilot 放行與升級條款

M4 仍沿用 `docs/AUTONOMOUS_RUN.md` 的既定門檻，M2 不修改：

| 指標 | 門檻 |
|---|---:|
| F1 JSON schema 合格率 | ≥95% |
| F1–F3 累積通過率 | ≥70% |
| F1–F6 累積通過率 | ≥45% |
| Judge 抽審 50 筆通過率 | ≥80% |
| 全量預估 wall-clock | ≤5 小時 |
| 預估 filtered 產出 | ≥8,000 |

若本機 teacher 未通過，升級方向只能是「雲端代管的開放權重 Qwen」，不是封閉模型。
這會產生外部帳號、ToS 與費用，因此仍須使用者另行核可。

---

## 8. Review 狀態

- [x] D-009 無人監督規則下自動定案，可進 M3
- [ ] 使用者已 review `qwen3.6:27b` / `gpt-oss:20b` / `BAAI/bge-m3`
- 使用者 review 日期：待填
