# FormosaNLU five-minute reviewer path

## Research question

在 frozen 20-shot MASSIVE `zh-TW` contract 下，本機 open-weight teacher 產生並經固定
規則過濾的 synthetic data，能否改善小型 student model 的 intent classification、
slot filling 與 strict JSON output？本頁只索引既有證據，不新增研究主張。

## Frozen evidence

- [v1.2.2 Technical note](https://doi.org/10.5281/zenodo.21879155)：可獨立閱讀的英文技術報告，未經 peer review。
- [`docs/data_card.md`](data_card.md)：資料來源、3,760-row frozen training corpus、3,754-row public release 與 F1–F7 邊界。
- [`reports/m15_cross_model_replication.md`](../reports/m15_cross_model_replication.md)：Gemma 與 Phi-4-mini 的 paired cross-family replication。

## Main result

在相同 paired contract 與 seeds 42–44 下，Gemma 的 intent accuracy／joint exact match
分別提升 4.14／3.86 percentage points；Phi-4-mini 分別提升 5.09／4.71 percentage
points。完整 confidence intervals、判準與不 pooling 邊界見
[`reports/m15_cross_model_replication.md`](../reports/m15_cross_model_replication.md)。

## Reproduce without training

CPU-only 驗證入口是 [`scripts/check_gates.py`](../scripts/check_gates.py)。它檢查 lint、
非本機 artifact tests、README evidence、contributors、reproduction contract 與 closeout
狀態，不啟動訓練或 GPU inference：

```powershell
uv sync --frozen --group dev
uv run python scripts/check_gates.py
```

公開 artifacts 可直接檢查：[Hugging Face Dataset](https://huggingface.co/datasets/steven0226/formosa-nlu-synth-v1)、
[Gemma LoRA](https://huggingface.co/steven0226/gemma-4-e4b-formosanlu-lora)、
[Phi-4-mini LoRA](https://huggingface.co/steven0226/phi-4-mini-formosanlu-lora)。

## Limitations

- Cross-family replication 只支持 frozen contract 下的 paired 結果，不代表可推廣到任意模型、任務或資料集。
- M19 per-recipe ablation 是 single-seed composition comparison；沒有任何差異達到預先登記門檻，不允許 recipe-level causal claim。
- Public Dataset 因 F7 independent audit 排除 6 筆，不能回溯改寫已凍結的 3,760-row training corpus。
- Technical note 是 Zenodo archival report，不是 peer-reviewed paper。
