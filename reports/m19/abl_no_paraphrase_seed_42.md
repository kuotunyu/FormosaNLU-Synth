# M9 Adapter Evaluation — abl_no_paraphrase seed 42

- Completed: 2974/2974
- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\m19\abl_no_paraphrase\seed_42\adapter` (group `abl_no_paraphrase`, seed `42`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 96.54%
- Intent accuracy: 74.14%
- Intent macro-F1: 74.72%
- Slot micro-F1: 64.09%
- Exact match: 50.00%
- Parser outcomes: {'unknown_intent': 41, 'unknown_slot_type': 62, 'valid': 2871}
- Diagnostic intent accuracy among strict-valid rows only: 76.80% (2205/2871); this is not a primary metric
- Output tokens: P50 22, P95 36, P99 46, max 62; 0 rows reached the generation limit
- Summed generation time (model load excluded): 1537.45 s

> JSON-invalid rows remain in every denominator.
