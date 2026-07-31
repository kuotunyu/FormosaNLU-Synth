# Robustness across seeds — gemma

- Seeds: 42
- Status: `partial`
- Evaluation-only; the probe never re-enters training.

## Per-group means

| Group | Metric | Mean | Sample SD |
|---|---|---:|---:|
| `real_only` | `intent_accuracy` | 71.61% | — |
| `real_only` | `intent_macro_f1` | 73.33% | — |
| `real_only` | `slot_micro_f1` | 60.59% | — |
| `real_only` | `exact_match` | 46.33% | — |
| `real_only` | `json_valid_rate` | 98.23% | — |
| `real_syn_filtered` | `intent_accuracy` | 73.27% | — |
| `real_syn_filtered` | `intent_macro_f1` | 72.93% | — |
| `real_syn_filtered` | `slot_micro_f1` | 64.13% | — |
| `real_syn_filtered` | `exact_match` | 48.79% | — |
| `real_syn_filtered` | `json_valid_rate` | 97.85% | — |

## Paired delta (filtered − real_only), computed per seed

| Metric | Mean Δ | Sample SD |
|---|---:|---:|
| `intent_accuracy` | +1.66 | — |
| `intent_macro_f1` | -0.40 | — |
| `slot_micro_f1` | +3.54 | — |
| `exact_match` | +2.45 | — |
| `json_valid_rate` | -0.38 | — |

Deltas are computed within each seed and then averaged, so the pairing between adapters trained on identical data is preserved. The probe is evaluation-only and never re-enters training.
