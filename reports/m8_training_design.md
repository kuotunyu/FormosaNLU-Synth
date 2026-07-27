# M8 Gemma 4 Training Design

> Status: runtime repaired; the text-only checkpoint loader and audited one-step
> QLoRA smoke test both pass on the local RTX 4090.

## Model artifact

| Item | Verified value |
| --- | --- |
| Model | `google/gemma-4-E4B-it` |
| Hugging Face revision | `ee0ef6023621cff504d758262d4e04895a5af4a2` |
| License | Apache-2.0 |
| Local weight size | 15,992,595,884 bytes |
| Local snapshot total | 16,024,794,203 bytes (14.924 GiB) |
| Weight SHA256 | `cfbd3d2f1cd71bd471c37fe2bf8546d5028d41e5736f64e1ca6c6b8893125503` |
| Remote-size check | exact match |
| Free disk after download | 145.44 GiB |

The repository contains a multimodal conditional-generation architecture, but
FormosaNLU is text-only. The implementation therefore loads
`Gemma4ForCausalLM`, the official Transformers text-only class, rather than
instantiating vision and audio towers that this task never uses. The base weights
are ignored by Git; only their revision, sizes, hash, and license are recorded in
`reports/m8_artifacts.json`.

## QLoRA contract

The frozen configuration is `configs/train.yaml`:

- NF4 4-bit weights, double quantization, bfloat16 compute.
- LoRA rank 16, alpha 32, dropout 0.05, bias disabled.
- `target_modules="all-linear"` following PEFT's QLoRA guidance.
- AdamW 8-bit, learning rate `2e-4`, cosine schedule, 15 warmup steps.
- Batch size 2 with 8 accumulation steps: effective batch size 16.
- 500 optimizer steps, evaluation and checkpointing every 25 steps.
- Gradient checkpointing and completion-only loss.
- Seed 42; each run snapshots its config, environment, and source commit.

All six experiment groups resolve through one shared configuration digest
(`2bfd8edd2575...`). Batch execution deliberately refuses to start before M9
review. The single-group trainer supports `checkpoint-*` discovery and
`resume_from_checkpoint`; every run writes `trainer_state.json`,
`metrics.jsonl`, an environment inventory, and its adapter.

## Prompt and length audit

Prompt template `formosanlu_nlu.v1` is shared by training and inference.
Targets are compact JSON with exactly `intent` and `slots`. Slot values must be
literal contiguous spans. Training rows omit the label catalog because the labels
are present in supervised targets; the zero-shot baseline includes the frozen
60-intent/55-slot catalog.

The Gemma tokenizer was loaded directly with the Rust `tokenizers` package, which
does not import PyTorch. Across all 11,514 real training examples, the combined
system prompt, user prompt, and target length was:

| Statistic | Tokens |
| --- | ---: |
| Minimum | 76 |
| P50 | 92 |
| P95 | 114 |
| P99 | 127 |
| Maximum | 183 |

Thus the 512-token training limit has at least 329 tokens of headroom at the
observed maximum. A representative zero-shot prompt including the entire label
catalog is 586 tokens before the model-specific chat-template control tokens;
zero-shot inference does not truncate it and uses up to 128 generated tokens.

## Locked runtime

| Package | Version |
| --- | --- |
| PyTorch | `2.11.0+cu128` |
| Transformers | `5.14.1` |
| Accelerate | `1.14.0` |
| PEFT | `0.19.1` |
| TRL | `1.9.1` |
| bitsandbytes | `0.50.0` |
| sentence-transformers | `5.6.1` |

`pyproject.toml` pins PyTorch to the official CUDA 12.8 wheel index. `uv.lock`
and the exported `requirements.txt` describe the same environment.

## Validation and resolved runtime blocker

The environment now uses uv-managed CPython 3.11.15. PyTorch
`2.11.0+cu128` imports successfully, reports CUDA available, and detects the
RTX 4090. The previous failure came from the Anaconda-based environment and its
older Visual C++ runtime appearing before the current Windows runtime on PATH.

The E4B artifact is a multimodal checkpoint whose language keys begin with
`model.language_model.*`. Loading it directly as `Gemma4ForCausalLM` does not
remap that prefix, so the first model attempt correctly failed validation: the
language weights were reported missing and a newly initialized model exhausted
VRAM. The adopted loader passes the nested `text_config` and explicitly maps
`^model\.language_model\.` to `model.`. All 665 language weights then load;
vision/audio weights are deliberately ignored.

The audited one-step QLoRA smoke test passed:

| Metric | Result |
| --- | ---: |
| Trainable parameters | 38,879,232 (0.705%) |
| Total text-model parameters | 5,515,496,448 |
| Train loss | 1.9862 |
| Eval loss | 2.9560 |
| Train runtime | 5.41 s |
| Peak allocated VRAM | 20,646 MiB |
| Peak reserved VRAM | 22,280 MiB |
| Adapter | 155,609,536 bytes; SHA256 recorded |

The adapter and `checkpoint-1` were both written. Exact machine-readable values
are in `reports/m8_smoke_test.json`.

The full zero-shot Test baseline also completed all 2,974 rows with greedy,
unconstrained decoding. Strict metrics are JSON-valid 17.38%, intent accuracy
10.66%, intent macro-F1 23.12%, slot micro-F1 0%, and exact match 8.10%.
Among the 517 strict-valid rows, 317 intents were correct (61.32%); this
conditional value is diagnostic only and does not replace the primary
all-rows denominator. Batch-size engineering changed only throughput, from 4
to 8; the frozen prompt and decoding contract did not change.

Static and CPU-safe checks now pass: 53 tests, Ruff, `uv lock --check`, the
six-group plan/digest check, artifact inspection, and `git diff --check`.

During the unattended run, importing PyTorch originally failed before CUDA or
model loading:

```text
OSError: [WinError 1114] A dynamic link library (DLL) initialization routine failed.
Error loading "...\.venv\Lib\site-packages\torch\lib\c10.dll"
or one of its dependencies.
```

Two project-local fixes were attempted:

1. A fresh `uv` resolution with the current PyPI PyTorch 2.13 wheel.
2. Replacement with the official Windows CUDA 12.8 PyTorch 2.11 wheel and a
   locked resync.

Both attempts failed at the same `c10.dll` import boundary. Per the unattended-run
rule, the agent stopped after two fixes. Once the user returned, a separate
uv-managed CPython 3.11 environment removed the Anaconda DLL collision without
changing machine-wide runtimes, PATH, or drivers. The repaired environment was
then promoted to the default project `.venv`.
