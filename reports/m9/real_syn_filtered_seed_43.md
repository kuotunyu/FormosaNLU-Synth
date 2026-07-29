# M9 Adapter Evaluation — real_syn_filtered seed 43

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\real_syn_filtered\seed_43\adapter` (group `real_syn_filtered`, seed `43`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 98.08%
- Intent accuracy: 77.84%
- Intent macro-F1: 76.81%
- Slot micro-F1: 66.00%
- Exact match: 53.53%
- Parser outcomes: {'schema_validation_error': 1, 'unknown_intent': 28, 'unknown_slot_type': 28, 'valid': 2917}
- Diagnostic intent accuracy among strict-valid rows only: 79.36% (2315/2917); this is not a primary metric
- Output tokens: P50 21, P95 36, P99 47, max 62; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1374.85 s

> JSON-invalid rows remain in every denominator.
