# M9 Adapter Evaluation — real_syn_unfiltered_full seed 42

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\real_syn_unfiltered_full\seed_42\adapter` (group `real_syn_unfiltered_full`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 97.75%
- Intent accuracy: 75.99%
- Intent macro-F1: 76.42%
- Slot micro-F1: 65.01%
- Exact match: 51.21%
- Parser outcomes: {'unknown_intent': 29, 'unknown_slot_type': 38, 'valid': 2907}
- Diagnostic intent accuracy among strict-valid rows only: 77.74% (2260/2907); this is not a primary metric
- Output tokens: P50 22, P95 38, P99 50, max 66; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1629.81 s

> JSON-invalid rows remain in every denominator.
