# M10 robustness — real_only seed 42

Status: **complete**; rows: 8,922

| Probe | Intent acc | Slot F1 | Exact match | JSON valid |
| --- | ---: | ---: | ---: | ---: |
| `asr_noise` | 68.49% | 58.62% | 42.54% | 98.52% |
| `colloquial` | 73.50% | 61.20% | 47.98% | 98.18% |
| `lexical` | 72.83% | 61.97% | 48.49% | 97.98% |

Deltas are computed against the same adapter on untouched real Test.
