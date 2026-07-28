# M9 Adapter Evaluation — real_only seed 42

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\real_only\seed_42\adapter` (group `real_only`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 98.02%
- Intent accuracy: 73.54%
- Intent macro-F1: 75.20%
- Slot micro-F1: 62.14%
- Exact match: 49.06%
- Parser outcomes: {'unknown_intent': 25, 'unknown_slot_type': 34, 'valid': 2915}
- Diagnostic intent accuracy among strict-valid rows only: 75.03% (2187/2915); this is not a primary metric
- Output tokens: P50 21, P95 38, P99 49, max 66; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1934.96 s

> JSON-invalid rows remain in every denominator.
