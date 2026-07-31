# M9 Adapter Evaluation — real_only seed 42

- Completed: 2974/2974
- Model: `microsoft/Phi-4-mini-instruct` via text-only `AutoModelForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\m15\phi4mini\real_only\seed_42\adapter` (group `real_only`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 96.67%
- Intent accuracy: 72.49%
- Intent macro-F1: 73.14%
- Slot micro-F1: 59.55%
- Exact match: 45.49%
- Parser outcomes: {'unknown_intent': 44, 'unknown_slot_type': 55, 'valid': 2875}
- Diagnostic intent accuracy among strict-valid rows only: 74.99% (2156/2875); this is not a primary metric
- Output tokens: P50 22, P95 36, P99 46, max 60; 0 rows reached the generation limit
- Summed generation time (model load excluded): 602.05 s

> JSON-invalid rows remain in every denominator.
