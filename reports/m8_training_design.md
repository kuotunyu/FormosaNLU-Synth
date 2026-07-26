# M8 Gemma 4 Training Design

> Status: implementation and static validation complete; model execution is blocked
> by the local Windows PyTorch runtime. No training result is claimed here.

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
- AdamW 8-bit, learning rate `2e-4`, cosine schedule, warmup ratio `0.03`.
- Batch size 2 with 8 accumulation steps: effective batch size 16.
- 500 optimizer steps, evaluation and checkpointing every 25 steps.
- Gradient checkpointing and completion-only loss.
- Seed 42; each run snapshots its config, environment, and source commit.

All six experiment groups resolve through one shared configuration digest
(`6f02f30222a1...`). Batch execution deliberately refuses to start before M9
review. The single-group trainer supports `checkpoint-*` discovery and
`resume_from_checkpoint`.

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

## Validation and blocker

Static and CPU-safe checks pass: 45 tests, Ruff, `uv lock --check`, the six-group
plan/digest check, artifact inspection, and `git diff --check`.

The mandatory one-step QLoRA smoke test and the zero-shot baseline could not
start because importing PyTorch fails before CUDA or model loading:

```text
OSError: [WinError 1114] A dynamic link library (DLL) initialization routine failed.
Error loading "...\.venv\Lib\site-packages\torch\lib\c10.dll"
or one of its dependencies.
```

Two project-local fixes were attempted:

1. A fresh `uv` resolution with the current PyPI PyTorch 2.13 wheel.
2. Replacement with the official Windows CUDA 12.8 PyTorch 2.11 wheel and a
   locked resync.

Both failed at the same `c10.dll` import boundary. Per the unattended-run rule,
the agent stopped after two fixes instead of changing machine-wide DLLs, Visual
C++ runtimes, Conda, PATH, or driver state. M8 remains blocked until the user is
available to authorize or perform that system-level diagnosis.
