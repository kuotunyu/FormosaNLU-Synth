# M9 Adapter Evaluation — real_only seed 44

- Completed: 2974/2974
- Model: `microsoft/Phi-4-mini-instruct` via text-only `AutoModelForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\m15\phi4mini\real_only\seed_44\adapter` (group `real_only`, seed `44`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 96.84%
- Intent accuracy: 68.39%
- Intent macro-F1: 68.44%
- Slot micro-F1: 56.02%
- Exact match: 39.98%
- Parser outcomes: {'schema_validation_error': 1, 'unknown_intent': 59, 'unknown_slot_type': 34, 'valid': 2880}
- Diagnostic intent accuracy among strict-valid rows only: 70.62% (2034/2880); this is not a primary metric
- Output tokens: P50 22, P95 35, P99 46, max 79; 0 rows reached the generation limit
- Summed generation time (model load excluded): 590.70 s

> JSON-invalid rows remain in every denominator.
