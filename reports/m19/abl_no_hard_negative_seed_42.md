# M9 Adapter Evaluation — abl_no_hard_negative seed 42

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\m19\abl_no_hard_negative\seed_42\adapter` (group `abl_no_hard_negative`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 97.24%
- Intent accuracy: 76.19%
- Intent macro-F1: 76.23%
- Slot micro-F1: 64.69%
- Exact match: 50.81%
- Parser outcomes: {'schema_validation_error': 1, 'unknown_intent': 18, 'unknown_slot_type': 63, 'valid': 2892}
- Diagnostic intent accuracy among strict-valid rows only: 78.35% (2266/2892); this is not a primary metric
- Output tokens: P50 22, P95 37, P99 47, max 66; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1536.61 s

> JSON-invalid rows remain in every denominator.
