# M14 Paired Statistical Evidence

- Comparison: `real_syn_filtered minus real_only`
- Seeds: 42, 43, 44
- Paired Test rows per seed: 2,974
- Hierarchical bootstrap: 5,000 repetitions, seed 20260729

## Effect estimates

| Metric | Seed deltas (percentage points) | Mean Δ | Hierarchical 95% CI |
|---|---:|---:|---:|
| `intent_accuracy` | +2.66 / +4.34 / +5.41 | +4.14 | [+2.60, +5.59] |
| `intent_macro_f1` | +0.89 / +1.45 / +3.70 | +2.01 | [+0.35, +3.69] |
| `slot_micro_f1` | +4.40 / +3.60 / +0.75 | +2.92 | [+0.87, +4.68] |
| `exact_match` | +3.06 / +4.51 / +4.00 | +3.86 | [+2.75, +4.92] |
| `json_valid_rate` | -0.03 / +3.83 / +0.91 | +1.57 | [-0.01, +3.77] |

## Exact paired tests

| Test | Baseline-only correct | Filtered-only correct | Exact p | Holm p |
|---|---:|---:|---:|---:|
| `intent_accuracy_seed_42` | 175 | 254 | 0.00016 | 0.00017 |
| `exact_match_seed_42` | 218 | 309 | 8.51e-05 | 0.00017 |
| `intent_accuracy_seed_43` | 150 | 279 | 4.78e-10 | 2.39e-09 |
| `exact_match_seed_43` | 173 | 307 | 1e-09 | 4e-09 |
| `intent_accuracy_seed_44` | 127 | 288 | 1.79e-15 | 1.07e-14 |
| `exact_match_seed_44` | 191 | 310 | 1.18e-07 | 3.55e-07 |

## Scope

Evidence applies to the frozen MASSIVE zh-TW Test set and this Gemma 4 training contract. It does not establish cross-model or cross-dataset generalization.

Prediction JSONL files remain ignored because they contain upstream Test utterances. Their paths, row counts, and SHA-256 values are recorded in the machine-readable JSON report.
