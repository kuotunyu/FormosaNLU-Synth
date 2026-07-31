# M9 Adapter Evaluation — real_syn_filtered seed 43

- Completed: 2974/2974
- Model: `microsoft/Phi-4-mini-instruct` via text-only `AutoModelForCausalLM`
- Adapter: `C:\Users\3Hml\Desktop\mySyntheticData\3_FormosaNLU\runs\m15\phi4mini\real_syn_filtered\seed_43\adapter` (group `real_syn_filtered`, seed `43`)
- Quantization: NF4 + double quant, bf16 compute
- Prompt template: `formosanlu_nlu.v1`; label catalog not included
- Constrained decoding: **disabled**
- JSON-valid: 98.49%
- Intent accuracy: 74.38%
- Intent macro-F1: 73.62%
- Slot micro-F1: 59.23%
- Exact match: 47.21%
- Parser outcomes: {'unknown_intent': 33, 'unknown_slot_type': 12, 'valid': 2929}
- Diagnostic intent accuracy among strict-valid rows only: 75.52% (2212/2929); this is not a primary metric
- Output tokens: P50 21, P95 35, P99 45, max 60; 0 rows reached the generation limit
- Summed generation time (model load excluded): 576.25 s

> JSON-invalid rows remain in every denominator.
