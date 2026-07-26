# M0 environment report

Checked on 2026-07-27 at 03:30 (Asia/Taipei).

| Check | Observed | Result |
|---|---|---|
| Python | 3.10.9 | pass |
| uv | 0.11.18 | pass |
| Git | 2.41.0.windows.1 | pass |
| Git LFS | 3.3.0 | pass |
| GPU | NVIDIA GeForce RTX 4090, 24,564 MiB, driver 591.86 | pass |
| Ollama | service reachable, 0.32.0 | pass |
| C: free before model pull | 182.1 GiB | pass |
| C: free after model pull | 164.4 GiB | pass (>100 GiB guardrail) |
| External `../.env` | present; contents were not read | pass |
| Repository Git identity | `kuotunyu <61350295+kuotunyu@users.noreply.github.com>` | pass |

## Reproducible Python environment

- `uv.lock` resolves 85 packages for Python 3.10–3.12.
- A new `.venv` was created with Python 3.10.9.
- `uv pip sync requirements.txt` completed from the generated lock export.
- `uv sync --locked` installed the project plus development tools.
- `uv lock --check`, `python -m src.data`, and Ruff all passed.

## Local model inventory

| Role | Tag | Ollama ID | Stored size | State |
|---|---|---|---:|---|
| Teacher candidate | `qwen3.6:27b` | `a50eda8ed977` | 17 GB | downloaded at M0; benchmark at M2 |
| Judge | `gpt-oss:20b` | `17052f91a42e` | 13 GB | already present |

`qwen3.6:27b` reports architecture `qwen35`, 27.8B parameters, Q4_K_M
quantization, 262,144-token upstream context, and Apache-2.0. Project runtime
context remains capped at 4,096 in `configs/ollama.yaml`.

No model was resident in VRAM when this report was written. GPU wall-clock used
by M0 was 0 hours; model download and environment setup used no paid API.

## Notes

- `OLLAMA_MODELS` was not moved and no system environment variable was changed.
- A broad converted-dataset probe cached about 920 MiB under the ignored
  project path `data/cache/huggingface`. A cleanup attempt was blocked by the
  execution safety policy, so it was left intact; it is reproducible and never
  enters Git. The production loader uses only the three targeted `zh-TW`
  Parquet files under `data/raw/massive`.
