# M9 Adapter Evaluation — real_syn_unfiltered_eqn seed 42

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\real_syn_unfiltered_eqn\seed_42\adapter` (group `real_syn_unfiltered_eqn`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 97.95%
- Intent accuracy: 76.03%
- Intent macro-F1: 75.59%
- Slot micro-F1: 64.37%
- Exact match: 51.01%
- Parser outcomes: {'unknown_intent': 24, 'unknown_slot_type': 37, 'valid': 2913}
- Diagnostic intent accuracy among strict-valid rows only: 77.62% (2261/2913); this is not a primary metric
- Output tokens: P50 22, P95 38, P99 49, max 66; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1604.46 s

> JSON-invalid rows remain in every denominator.
