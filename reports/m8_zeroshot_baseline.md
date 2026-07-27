# M8 Zero-shot Baseline

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; zero-shot label catalog included
- Constrained decoding: **disabled**
- JSON-valid: 17.38%
- Intent accuracy: 10.66%
- Intent macro-F1: 23.12%
- Slot micro-F1: 0.00%
- Exact match: 8.10%
- Parser outcomes: {'json_decode_error': 466, 'schema_validation_error': 1936, 'unknown_intent': 55, 'valid': 517}
- Diagnostic intent accuracy among strict-valid rows only: 61.32% (317/517); this is not a primary metric
- Output tokens: P50 38, P95 64, P99 85, max 128; 1 rows reached the generation limit
- Summed generation time (model load excluded): 3779.07 s

> JSON-invalid rows remain in every denominator.
