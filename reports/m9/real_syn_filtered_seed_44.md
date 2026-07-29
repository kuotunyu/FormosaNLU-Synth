# M9 Adapter Evaluation — real_syn_filtered seed 44

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\real_syn_filtered\seed_44\adapter` (group `real_syn_filtered`, seed `44`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 98.25%
- Intent accuracy: 78.38%
- Intent macro-F1: 76.78%
- Slot micro-F1: 65.05%
- Exact match: 51.92%
- Parser outcomes: {'unknown_intent': 22, 'unknown_slot_type': 30, 'valid': 2922}
- Diagnostic intent accuracy among strict-valid rows only: 79.77% (2331/2922); this is not a primary metric
- Output tokens: P50 22, P95 35, P99 45, max 62; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1373.36 s

> JSON-invalid rows remain in every denominator.
