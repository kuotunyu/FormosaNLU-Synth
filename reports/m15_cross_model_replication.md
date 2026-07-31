# M15 Cross-model Replication

Conclusion: **replicated_across_student_families**

| Metric | Gemma Δ [95% CI] | Phi Δ [95% CI] | Same positive direction | Both CIs > 0 |
|---|---:|---:|:---:|:---:|
| `intent_accuracy` | +4.14 [+2.60, +5.59] | +5.09 [+1.83, +9.02] | ✅ | ✅ |
| `intent_macro_f1` | +2.01 [+0.35, +3.69] | +3.36 [+0.98, +5.56] | ✅ | ✅ |
| `slot_micro_f1` | +2.92 [+0.87, +4.68] | +1.80 [+0.29, +3.19] | ✅ | ✅ |
| `exact_match` | +3.86 [+2.75, +4.92] | +4.71 [+1.36, +7.59] | ✅ | ✅ |
| `json_valid_rate` | +1.57 [-0.01, +3.77] | +1.77 [+1.05, +2.63] | ✅ | ❌ |

## Preregistered criterion

For both intent_accuracy and exact_match, the paired mean delta must be positive in each family and each hierarchical 95% CI lower bound must exceed zero.

## Scope

This is a two-family replication on one frozen dataset and training contract. Model families are summarized separately and are not pooled.
