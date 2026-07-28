# M10 Main Results

Status: **complete**.

| Group | Intent acc | Macro-F1 | Slot F1 | Exact | JSON-valid | Best step | Epoch | Real exposure* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `zero_shot` | 10.66% | 23.12% | 0.00% | 8.10% | 17.38% | — | — | 0 |
| `real_only` | 73.54% | 75.20% | 62.14% | 49.06% | 98.02% | 150 | 2.0272108843537415 | 2400 |
| `real_std_aug` | 74.31% | 75.59% | 62.58% | 46.81% | 96.23% | 200 | 0.6482982171799028 | 762 |
| `real_syn_unfiltered_full` | 75.99% | 76.42% | 65.01% | 51.21% | 97.75% | 350 | 0.45016077170418006 | 529 |
| `real_syn_unfiltered_eqn` | 76.03% | 75.59% | 64.37% | 51.01% | 97.95% | 300 | 0.9724473257698542 | 1144 |
| `real_syn_filtered` | 76.19% | 76.09% | 66.54% | 52.12% | 97.98% | 250 | 0.8103727714748784 | 953 |
| `full_real` | 84.53% | 81.65% | 71.58% | 60.66% | 99.73% | 500 | 0.694806322737537 | 8000 |

\* Real exposure is a clearly marked estimate: best step × effective batch × real rows / assembled rows.

## Gap closed

| Group | Metric | Absolute delta | Gap closed | Reliable |
|---|---|---:|---:|---|
| `real_only` | `intent_accuracy` | +0.00% | 0.0% | yes |
| `real_only` | `intent_macro_f1` | +0.00% | 0.0% | yes |
| `real_only` | `slot_micro_f1` | +0.00% | 0.0% | yes |
| `real_only` | `exact_match` | +0.00% | 0.0% | yes |
| `real_only` | `json_valid_rate` | +0.00% | 0.0% | yes |
| `real_std_aug` | `intent_accuracy` | +0.77% | 7.0% | yes |
| `real_std_aug` | `intent_macro_f1` | +0.39% | 6.0% | yes |
| `real_std_aug` | `slot_micro_f1` | +0.44% | 4.6% | yes |
| `real_std_aug` | `exact_match` | -2.25% | -19.4% | yes |
| `real_std_aug` | `json_valid_rate` | -1.78% | -103.9% | yes |
| `real_syn_unfiltered_full` | `intent_accuracy` | +2.45% | 22.3% | yes |
| `real_syn_unfiltered_full` | `intent_macro_f1` | +1.23% | 19.0% | yes |
| `real_syn_unfiltered_full` | `slot_micro_f1` | +2.87% | 30.4% | yes |
| `real_syn_unfiltered_full` | `exact_match` | +2.15% | 18.6% | yes |
| `real_syn_unfiltered_full` | `json_valid_rate` | -0.27% | -15.7% | yes |
| `real_syn_unfiltered_eqn` | `intent_accuracy` | +2.49% | 22.6% | yes |
| `real_syn_unfiltered_eqn` | `intent_macro_f1` | +0.40% | 6.1% | yes |
| `real_syn_unfiltered_eqn` | `slot_micro_f1` | +2.23% | 23.6% | yes |
| `real_syn_unfiltered_eqn` | `exact_match` | +1.95% | 16.8% | yes |
| `real_syn_unfiltered_eqn` | `json_valid_rate` | -0.07% | -3.9% | yes |
| `real_syn_filtered` | `intent_accuracy` | +2.66% | 24.2% | yes |
| `real_syn_filtered` | `intent_macro_f1` | +0.89% | 13.8% | yes |
| `real_syn_filtered` | `slot_micro_f1` | +4.40% | 46.6% | yes |
| `real_syn_filtered` | `exact_match` | +3.06% | 26.4% | yes |
| `real_syn_filtered` | `json_valid_rate` | -0.03% | -2.0% | yes |
| `full_real` | `intent_accuracy` | +11.00% | 100.0% | yes |
| `full_real` | `intent_macro_f1` | +6.46% | 100.0% | yes |
| `full_real` | `slot_micro_f1` | +9.44% | 100.0% | yes |
| `full_real` | `exact_match` | +11.60% | 100.0% | yes |
| `full_real` | `json_valid_rate` | +1.71% | 100.0% | yes |

## Per-intent movement: filtered vs real-only

Largest gains:

- `qa_factoid`: +51.77%
- `qa_definition`: +33.33%
- `transport_query`: +27.45%
- `email_querycontact`: +15.38%
- `takeaway_order`: +13.64%
- `calendar_query`: +12.70%
- `play_audiobook`: +12.20%
- `iot_hue_lightup`: +11.11%
- `news_query`: +8.87%
- `alarm_query`: +8.82%

Largest regressions:

- `general_quirky`: -31.95%
- `transport_ticket`: -22.86%
- `transport_taxi`: -17.39%
- `music_settings`: -16.67%
- `play_game`: -8.57%
- `calendar_set`: -6.70%
- `transport_traffic`: -6.67%
- `recommendation_locations`: -6.45%
- `takeaway_query`: -5.71%
- `play_music`: -5.68%

> JSON-invalid rows remain in every metric denominator. Gap-closed ratios
> are emitted only when the real-only → full-real denominator is at least 0.01.
