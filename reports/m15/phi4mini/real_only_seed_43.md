# M9 Adapter Evaluation — real_only seed 43

- Completed: 2974/2974
- Model: `microsoft/Phi-4-mini-instruct` via text-only `AutoModelForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\m15\phi4mini\real_only\seed_43\adapter` (group `real_only`, seed `43`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 95.83%
- Intent accuracy: 65.20%
- Intent macro-F1: 68.23%
- Slot micro-F1: 56.49%
- Exact match: 39.78%
- Parser outcomes: {'json_decode_error': 2, 'unknown_intent': 57, 'unknown_slot_type': 65, 'valid': 2850}
- Diagnostic intent accuracy among strict-valid rows only: 68.04% (1939/2850); this is not a primary metric
- Output tokens: P50 22, P95 38, P99 50, max 60; 0 rows reached the generation limit
- Summed generation time (model load excluded): 628.22 s

> JSON-invalid rows remain in every denominator.
