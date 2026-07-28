# M9 Adapter Evaluation — full_real seed 42

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\full_real\seed_42\adapter` (group `full_real`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 99.73%
- Intent accuracy: 84.53%
- Intent macro-F1: 81.65%
- Slot micro-F1: 71.58%
- Exact match: 60.66%
- Parser outcomes: {'unknown_intent': 2, 'unknown_slot_type': 6, 'valid': 2966}
- Diagnostic intent accuracy among strict-valid rows only: 84.76% (2514/2966); this is not a primary metric
- Output tokens: P50 22, P95 38, P99 49, max 64; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1490.76 s

> JSON-invalid rows remain in every denominator.
