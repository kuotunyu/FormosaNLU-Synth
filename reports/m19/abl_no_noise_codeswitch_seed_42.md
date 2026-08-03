# M9 Adapter Evaluation — abl_no_noise_codeswitch seed 42

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\m19\abl_no_noise_codeswitch\seed_42\adapter` (group `abl_no_noise_codeswitch`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 96.47%
- Intent accuracy: 73.47%
- Intent macro-F1: 73.03%
- Slot micro-F1: 63.84%
- Exact match: 48.76%
- Parser outcomes: {'unknown_intent': 43, 'unknown_slot_type': 62, 'valid': 2869}
- Diagnostic intent accuracy among strict-valid rows only: 76.16% (2185/2869); this is not a primary metric
- Output tokens: P50 22, P95 38, P99 49, max 68; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1558.41 s

> JSON-invalid rows remain in every denominator.
