# Robustness across seeds — gemma

- Seeds: 42, 43, 44
- Status: `complete`
- Evaluation-only; the probe never re-enters training.

## Per-group means

| Group | Metric | Mean | Sample SD |
|---|---|---:|---:|
| `real_only` | `intent_accuracy` | 70.88% | 0.63% |
| `real_only` | `intent_macro_f1` | 71.88% | 1.51% |
| `real_only` | `slot_micro_f1` | 61.01% | 1.28% |
| `real_only` | `exact_match` | 45.57% | 0.66% |
| `real_only` | `json_valid_rate` | 96.66% | 2.11% |
| `real_syn_filtered` | `intent_accuracy` | 74.51% | 1.09% |
| `real_syn_filtered` | `intent_macro_f1` | 73.99% | 1.05% |
| `real_syn_filtered` | `slot_micro_f1` | 63.76% | 1.48% |
| `real_syn_filtered` | `exact_match` | 49.14% | 1.84% |
| `real_syn_filtered` | `json_valid_rate` | 98.15% | 0.27% |

## Paired delta (filtered − real_only), computed per seed

| Metric | Mean Δ | Sample SD |
|---|---:|---:|
| `intent_accuracy` | +3.63 | 1.72 |
| `intent_macro_f1` | +2.11 | 2.19 |
| `slot_micro_f1` | +2.75 | 2.76 |
| `exact_match` | +3.58 | 2.05 |
| `json_valid_rate` | +1.49 | 2.35 |

Deltas are computed within each seed and then averaged, so the pairing between adapters trained on identical data is preserved. The probe is evaluation-only and never re-enters training.
