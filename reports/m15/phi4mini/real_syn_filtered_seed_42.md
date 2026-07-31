# M9 Adapter Evaluation — real_syn_filtered seed 42

- Completed: 2974/2974
- Model: `microsoft/Phi-4-mini-instruct` via text-only `AutoModelForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\m15\phi4mini\real_syn_filtered\seed_42\adapter` (group `real_syn_filtered`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 97.88%
- Intent accuracy: 74.28%
- Intent macro-F1: 74.02%
- Slot micro-F1: 60.08%
- Exact match: 46.70%
- Parser outcomes: {'unknown_intent': 31, 'unknown_slot_type': 32, 'valid': 2911}
- Diagnostic intent accuracy among strict-valid rows only: 75.88% (2209/2911); this is not a primary metric
- Output tokens: P50 22, P95 36, P99 44, max 59; 0 rows reached the generation limit
- Summed generation time (model load excluded): 600.99 s

> JSON-invalid rows remain in every denominator.
