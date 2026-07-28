# M9 Adapter Evaluation — real_std_aug seed 42

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\real_std_aug\seed_42\adapter` (group `real_std_aug`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 96.23%
- Intent accuracy: 74.31%
- Intent macro-F1: 75.59%
- Slot micro-F1: 62.58%
- Exact match: 46.81%
- Parser outcomes: {'schema_validation_error': 3, 'unknown_intent': 58, 'unknown_slot_type': 51, 'valid': 2862}
- Diagnostic intent accuracy among strict-valid rows only: 77.22% (2210/2862); this is not a primary metric
- Output tokens: P50 22, P95 38, P99 50, max 63; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1618.18 s

> JSON-invalid rows remain in every denominator.
