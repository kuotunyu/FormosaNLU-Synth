# M9 Adapter Evaluation — real_only seed 42

- Completed: 32/32
- Model: `microsoft/Phi-4-mini-instruct` via text-only `AutoModelForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\m15\phi4mini_smoke\seed_42\adapter` (group `real_only`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 0.00%
- Intent accuracy: 0.00%
- Intent macro-F1: 0.00%
- Slot micro-F1: 0.00%
- Exact match: 0.00%
- Parser outcomes: {'unknown_intent': 32}
- Diagnostic intent accuracy among strict-valid rows only: 0.00% (0/0); this is not a primary metric
- Output tokens: P50 13, P95 21, P99 32, max 32; 0 rows reached the generation limit
- Summed generation time (model load excluded): 4.99 s

> JSON-invalid rows remain in every denominator.
