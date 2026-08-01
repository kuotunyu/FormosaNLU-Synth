# M10 robustness — real_only seed 42

Status: **complete**; rows: 8,922

| Probe | Intent acc | Slot F1 | Exact match | JSON valid |
| --- | ---: | ---: | ---: | ---: |
| `asr_noise` | 63.25% | 50.73% | 33.32% | 96.44% |
| `colloquial` | 69.33% | 57.65% | 41.90% | 96.20% |
| `lexical` | 68.86% | 56.54% | 40.89% | 96.37% |

Deltas are computed against the same adapter on untouched real Test.
