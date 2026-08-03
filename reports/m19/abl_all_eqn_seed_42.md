# M9 Adapter Evaluation — abl_all_eqn seed 42

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\m19\abl_all_eqn\seed_42\adapter` (group `abl_all_eqn`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 97.34%
- Intent accuracy: 75.99%
- Intent macro-F1: 75.51%
- Slot micro-F1: 63.61%
- Exact match: 49.50%
- Parser outcomes: {'unknown_intent': 20, 'unknown_slot_type': 59, 'valid': 2895}
- Diagnostic intent accuracy among strict-valid rows only: 78.07% (2260/2895); this is not a primary metric
- Output tokens: P50 22, P95 36, P99 46, max 66; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1835.17 s

> JSON-invalid rows remain in every denominator.
