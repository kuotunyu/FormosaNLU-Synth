# M9 Adapter Evaluation — abl_no_slot_substitution seed 42

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\m19\abl_no_slot_substitution\seed_42\adapter` (group `abl_no_slot_substitution`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 96.40%
- Intent accuracy: 77.14%
- Intent macro-F1: 77.11%
- Slot micro-F1: 65.60%
- Exact match: 51.51%
- Parser outcomes: {'unknown_intent': 52, 'unknown_slot_type': 55, 'valid': 2867}
- Diagnostic intent accuracy among strict-valid rows only: 80.01% (2294/2867); this is not a primary metric
- Output tokens: P50 22, P95 37, P99 47, max 62; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1531.14 s

> JSON-invalid rows remain in every denominator.
