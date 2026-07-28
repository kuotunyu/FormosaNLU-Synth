# M9 Adapter Evaluation — real_syn_filtered seed 42

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\real_syn_filtered\seed_42\adapter` (group `real_syn_filtered`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 97.98%
- Intent accuracy: 76.19%
- Intent macro-F1: 76.09%
- Slot micro-F1: 66.54%
- Exact match: 52.12%
- Parser outcomes: {'unknown_intent': 29, 'unknown_slot_type': 31, 'valid': 2914}
- Diagnostic intent accuracy among strict-valid rows only: 77.76% (2266/2914); this is not a primary metric
- Output tokens: P50 22, P95 36, P99 47, max 62; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1537.44 s

> JSON-invalid rows remain in every denominator.
