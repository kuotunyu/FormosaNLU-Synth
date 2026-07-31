# M10 robustness — real_only seed 43

Status: **complete**; rows: 8,922

| Probe | Intent acc | Slot F1 | Exact match | JSON valid |
| --- | ---: | ---: | ---: | ---: |
| `asr_noise` | 66.85% | 56.81% | 40.15% | 94.28% |
| `colloquial` | 72.16% | 61.73% | 47.28% | 94.28% |
| `lexical` | 72.60% | 61.51% | 48.15% | 94.22% |

Deltas are computed against the same adapter on untouched real Test.
