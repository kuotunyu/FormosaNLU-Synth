# M9 Adapter Evaluation — real_only seed 44

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\real_only\seed_44\adapter` (group `real_only`, seed `44`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 97.34%
- Intent accuracy: 72.97%
- Intent macro-F1: 73.08%
- Slot micro-F1: 64.30%
- Exact match: 47.92%
- Parser outcomes: {'unknown_intent': 19, 'unknown_slot_type': 60, 'valid': 2895}
- Diagnostic intent accuracy among strict-valid rows only: 74.96% (2170/2895); this is not a primary metric
- Output tokens: P50 22, P95 39, P99 50, max 68; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1469.34 s

> JSON-invalid rows remain in every denominator.
