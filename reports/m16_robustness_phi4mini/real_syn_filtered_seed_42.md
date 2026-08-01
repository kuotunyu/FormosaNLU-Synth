# M10 robustness — real_syn_filtered seed 42

Status: **complete**; rows: 8,922

| Probe | Intent acc | Slot F1 | Exact match | JSON valid |
| --- | ---: | ---: | ---: | ---: |
| `asr_noise` | 66.07% | 53.31% | 36.72% | 98.12% |
| `colloquial` | 73.74% | 59.34% | 46.13% | 98.12% |
| `lexical` | 72.83% | 59.46% | 44.79% | 98.22% |

Deltas are computed against the same adapter on untouched real Test.
