# M10 Main Results

Status: **pending**.

| Group | Intent acc | Macro-F1 | Slot F1 | Exact | JSON-valid | Best step | Epoch | Real exposure* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `zero_shot` | 10.66% | 23.12% | 0.00% | 8.10% | 17.38% | — | — | 0 |
| `real_only` | pending | pending | pending | pending | pending | — | — | — |
| `real_std_aug` | pending | pending | pending | pending | pending | — | — | — |
| `real_syn_unfiltered_full` | pending | pending | pending | pending | pending | — | — | — |
| `real_syn_unfiltered_eqn` | pending | pending | pending | pending | pending | — | — | — |
| `real_syn_filtered` | pending | pending | pending | pending | pending | — | — | — |
| `full_real` | pending | pending | pending | pending | pending | — | — | — |

\* Real exposure is a clearly marked estimate: best step × effective batch × real rows / assembled rows.

Pending trained reports: `real_only`, `real_std_aug`, `real_syn_unfiltered_full`, `real_syn_unfiltered_eqn`, `real_syn_filtered`, `full_real`.

> JSON-invalid rows remain in every metric denominator. Gap-closed ratios
> are emitted only when the real-only → full-real denominator is at least 0.01.
