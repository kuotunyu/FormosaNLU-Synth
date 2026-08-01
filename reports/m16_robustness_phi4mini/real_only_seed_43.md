# M10 robustness — real_only seed 43

Status: **complete**; rows: 8,922

| Probe | Intent acc | Slot F1 | Exact match | JSON valid |
| --- | ---: | ---: | ---: | ---: |
| `asr_noise` | 56.66% | 49.36% | 30.03% | 95.29% |
| `colloquial` | 63.18% | 54.31% | 36.25% | 95.97% |
| `lexical` | 62.24% | 53.47% | 34.57% | 95.97% |

Deltas are computed against the same adapter on untouched real Test.
