# M15 Phi-4-mini Paired Statistical Evidence

- Comparison: `real_syn_filtered minus real_only`
- Seeds: 42, 43, 44
- Paired Test rows per seed: 2,974
- Hierarchical bootstrap: 5,000 repetitions, seed 20260729

## Effect estimates

| Metric | Seed deltas (percentage points) | Mean Δ | Hierarchical 95% CI |
|---|---:|---:|---:|
| `intent_accuracy` | +1.78 / +9.18 / +4.30 | +5.09 | [+1.83, +9.02] |
| `intent_macro_f1` | +0.88 / +5.40 / +3.82 | +3.36 | [+0.98, +5.56] |
| `slot_micro_f1` | +0.53 / +2.74 / +2.12 | +1.80 | [+0.29, +3.19] |
| `exact_match` | +1.21 / +7.43 / +5.48 | +4.71 | [+1.36, +7.59] |
| `json_valid_rate` | +1.21 / +2.66 / +1.45 | +1.77 | [+1.05, +2.63] |

## Exact paired tests

| Test | Baseline-only correct | Filtered-only correct | Exact p | Holm p |
|---|---:|---:|---:|---:|
| `intent_accuracy_seed_42` | 215 | 268 | 0.0179 | 0.0358 |
| `exact_match_seed_42` | 265 | 301 | 0.141 | 0.141 |
| `intent_accuracy_seed_43` | 134 | 407 | 5.46e-33 | 3.28e-32 |
| `exact_match_seed_43` | 197 | 418 | 2.99e-19 | 1.49e-18 |
| `intent_accuracy_seed_44` | 191 | 319 | 1.58e-08 | 4.75e-08 |
| `exact_match_seed_44` | 222 | 385 | 3.73e-11 | 1.49e-10 |

## Scope

Evidence applies to the frozen MASSIVE zh-TW Test set and the preregistered Phi-4-mini training contract. Cross-family conclusions must compare this report with M14 without pooling model families.

Prediction JSONL files remain ignored because they contain upstream Test utterances. Their paths, row counts, and SHA-256 values are recorded in the machine-readable JSON report.
