# Robustness across seeds — phi4mini

- Seeds: 42, 43, 44
- Status: `complete`
- Evaluation-only; the probe never re-enters training.

## Per-group means

| Group | Metric | Mean | Sample SD |
|---|---|---:|---:|
| `real_only` | `intent_accuracy` | 64.05% | 3.24% |
| `real_only` | `intent_macro_f1` | 65.44% | 2.71% |
| `real_only` | `slot_micro_f1` | 53.20% | 1.52% |
| `real_only` | `exact_match` | 35.91% | 2.58% |
| `real_only` | `json_valid_rate` | 96.46% | 0.79% |
| `real_syn_filtered` | `intent_accuracy` | 70.27% | 1.05% |
| `real_syn_filtered` | `intent_macro_f1` | 70.14% | 0.68% |
| `real_syn_filtered` | `slot_micro_f1` | 56.93% | 0.61% |
| `real_syn_filtered` | `exact_match` | 42.89% | 0.99% |
| `real_syn_filtered` | `json_valid_rate` | 98.29% | 0.19% |

## Paired delta (filtered − real_only), computed per seed

| Metric | Mean Δ | Sample SD |
|---|---:|---:|
| `intent_accuracy` | +6.22 | 3.46 |
| `intent_macro_f1` | +4.69 | 2.73 |
| `slot_micro_f1` | +3.73 | 1.23 |
| `exact_match` | +6.98 | 3.29 |
| `json_valid_rate` | +1.83 | 0.93 |

Deltas are computed within each seed and then averaged, so the pairing between adapters trained on identical data is preserved. The probe is evaluation-only and never re-enters training.
