# M8 Zero-shot Baseline

> **BLOCKED — no baseline metrics were produced.**

The complete, resumable evaluation harness is implemented for the untouched
2,974-example MASSIVE `zh-TW` Test split. It uses:

- `google/gemma-4-E4B-it` at revision
  `ee0ef6023621cff504d758262d4e04895a5af4a2`;
- the text-only `Gemma4ForCausalLM` class;
- NF4 double quantization with bfloat16 compute;
- prompt template `formosanlu_nlu.v1` with all 60 intents and 55 slot types;
- greedy generation with no constrained decoding;
- strict JSON parsing where invalid rows stay in every metric denominator;
- resumable JSONL checkpoints and intent accuracy/macro-F1, slot micro-F1,
  exact-match, throughput, and peak-memory reporting.

Execution stops before model loading because `import torch` raises Windows error
1114 while loading `torch\lib\c10.dll`. A PyPI PyTorch 2.13 environment and a
fresh official CUDA 12.8 PyTorch 2.11 environment both produced the same error.
No further machine-wide repair was attempted while the user was asleep.

All numerical task metrics are therefore deliberately `null`, not zero and not
estimated. See `reports/m8_training_design.md` for the reproducible configuration
and the exact handoff.
