# M9 Adapter Evaluation — real_syn_filtered seed 44

- Completed: 2974/2974
- Model: `microsoft/Phi-4-mini-instruct` via text-only `AutoModelForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\m15\phi4mini\real_syn_filtered\seed_44\adapter` (group `real_syn_filtered`, seed `44`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 98.29%
- Intent accuracy: 72.70%
- Intent macro-F1: 72.25%
- Slot micro-F1: 58.14%
- Exact match: 45.46%
- Parser outcomes: {'unknown_intent': 23, 'unknown_slot_type': 28, 'valid': 2923}
- Diagnostic intent accuracy among strict-valid rows only: 73.97% (2162/2923); this is not a primary metric
- Output tokens: P50 21, P95 37, P99 47, max 63; 0 rows reached the generation limit
- Summed generation time (model load excluded): 613.53 s

> JSON-invalid rows remain in every denominator.
