# M9 Adapter Evaluation — real_only seed 43

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\real_only\seed_43\adapter` (group `real_only`, seed `43`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 94.25%
- Intent accuracy: 73.50%
- Intent macro-F1: 75.36%
- Slot micro-F1: 62.40%
- Exact match: 49.02%
- Parser outcomes: {'unknown_intent': 52, 'unknown_slot_type': 119, 'valid': 2803}
- Diagnostic intent accuracy among strict-valid rows only: 77.99% (2186/2803); this is not a primary metric
- Output tokens: P50 22, P95 38, P99 50, max 64; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1546.00 s

> JSON-invalid rows remain in every denominator.
