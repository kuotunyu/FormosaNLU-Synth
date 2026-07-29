# M10 robustness — real_syn_filtered seed 42

Status: **complete**; rows: 8,922

| Probe | Intent acc | Slot F1 | Exact match | JSON valid |
| --- | ---: | ---: | ---: | ---: |
| `asr_noise` | 70.24% | 61.25% | 44.08% | 97.88% |
| `colloquial` | 74.88% | 65.69% | 51.18% | 97.68% |
| `lexical` | 74.68% | 65.48% | 51.11% | 97.98% |

Deltas are computed against the same adapter on untouched real Test.
