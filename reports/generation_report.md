# M6 Full Generation and Filtering Report

## Outcome

The frozen run completed all **11,264 / 11,264** planned rows with continuous
`generation_index` values 0–11,263 and 11,264 unique IDs. F1–F6 retained
**3,760 rows (33.38%)**, below the pre-registered 8,000-row minimum. The
shortfall is **4,240 rows**.

This is a genuine negative result. No prompt, model, target count, or frozen
threshold was changed after seeing the full-corpus outcome.

## Generation ledger

| Item | Result |
|---|---:|
| Teacher | `qwen3.6:27b`, local Ollama |
| Completed | 11,264 / 11,264 |
| Wall time | 14,663.14 s (4.073 h) |
| Prompt tokens | 2,860,385 |
| Output tokens | 515,170 |
| API spend | **US$0.00** |
| Raw corpus SHA-256 | `a7956a14c992f922ce321faba9652cf9bd96e39b8029105f2cf52c88d36f9447` |
| BGE-M3 embedding time | 19.46 s |
| BGE-M3 peak allocated VRAM | 2,295 MiB |

Electricity cost and a commercial-API equivalent are intentionally left
unpriced: the machine did not measure wall power, and there is no like-for-like
hosted tariff for this exact local model. Fabricating either number would make
the ledger less reproducible.

## Frozen F1–F6 funnel

| Stage / reason | Rows |
|---|---:|
| Generated / F1 JSON-valid | 11,264 |
| F2 invalid intent | −7 |
| F2 invalid slot contract | −454 |
| F3 ungrounded/overlapping slot | −738 |
| F4 language ratio | −300 |
| F4 simplified Chinese | −651 |
| **F1–F4 survivors** | **9,114** |
| F5 too close to a real seed | −460 |
| F5 synthetic duplicate | −4,596 |
| F5 seed outlier | −50 |
| F6 Val/Test contamination exclusion | −248 |
| **F1–F6 accepted** | **3,760 (33.38%)** |

The frozen semantic thresholds remained:

- synthetic duplicate maximum `0.999`
- seed-copy maximum `0.995`
- seed-outlier minimum `0.650`
- validation/test contamination maximum `0.990`

The accepted file is
`data/filtered/full_f1_f6.jsonl`, SHA-256
`e9700b50b85516af01023811bcedb0afb9e6f73a156a39d2d14feca5d5600daf`.

## Why the pilot projection failed

The dominant failure is generation mode collapse, not an indexing, embedding,
or filtering bug. Among the 9,114 cheap-filter survivors:

- only **4,044** utterances are exact-text distinct;
- **5,070** rows are repetitions beyond the first occurrence;
- there are **2,126** duplicate groups;
- the most repeated texts include `關閉客廳喇叭` (51), `打開客廳喇叭`
  (34), and `播放爵士樂` (30).

This is consistent with F5 removing 4,596 synthetic near-duplicates. It also
explains why a 500-row pilot overstated full-corpus yield: collapse became much
more visible as the generation plan exhausted common phrasings.

## Spot check and F7 release audit

Twenty evenly spaced accepted rows were reviewed. Most were readable and their
recorded slots were literal spans, but a few were awkward or underspecified
(for example, generic location or email requests with little context).
F1–F6 therefore defines the M9 filtered training candidate, not a final public
release.

The preregistered F7 audit judged 376 stratified rows with `gpt-oss:20b`:
370 accepted and 6 rejected. The 50-row random stratum is the only unbiased
rate estimator; 3 rows were rejected, giving an observed F1–F6 miss rate of
**6.0%** with a Wilson 95% interval of **2.06%–16.22%**. The targeted
hard-negative (272/275 accepted) and boundary-conflict (51/51 accepted) strata
must not be used as corpus-wide rate estimates.

The six known rejected sample IDs were removed from the release-only artifact,
leaving **3,754 rows** at
`data/filtered/full_f1_f7_release.jsonl`, SHA-256
`0da52fa1e8f63e615d0a950274586cd1696ae613c2734a922b6b59bc9821ecf2`.
The frozen M9 training corpus remains the original 3,760-row F1–F6 file so that
completed experiments and their preregistered contract are not rewritten.

## M9 implication

The prepared equal-N comparisons use the honest **N = 3,760**:

- filtered synthetic addition: 3,760
- deterministic unfiltered control addition: 3,760
- deterministic Standard Aug addition: 3,760

This preserves the scientific comparison without changing the registered
thresholds. Starting the long M9 batch still requires an explicit choice:
train with this honest smaller filtered set, or regenerate with a revised
generation design and treat that as a new run.
