# FormosaNLU — Synthetic Data Distillation for Traditional Chinese (Taiwan) NLU

> **Status:** the frozen corpus, primary seed-42 experiment matrix, M10
> evaluation, M11 comparison demo, and M12 report artifacts are complete.
> Four additional-seed runs, the F7 judge audit, robustness inference, and
> release work remain pending.

Can locally generated synthetic data help a small language model in a
low-resource setting? FormosaNLU measures that question on Traditional Chinese
(Taiwan) spoken-language understanding: joint intent classification and slot
filling under a strict JSON output contract.

| | |
| --- | --- |
| **Dataset** | MASSIVE `zh-TW` (CC BY 4.0), 60 intents and 55 slot types |
| **Low-resource setting** | `min(20, available)` real train examples per intent, seed 42 |
| **Teacher** | `qwen3.6:27b`, run locally through Ollama |
| **Student** | `google/gemma-4-E4B-it`, 4-bit QLoRA |
| **Independent judge** | `gpt-oss` open-weight model |
| **Hardware / API spend** | One RTX 4090 24 GB / **$0** |

Teacher, student, and judge are from different model families. The primary
results below are measured on all 2,974 untouched MASSIVE `zh-TW` Test rows.

## TL;DR

With seed 42, adding the 3,760-row filtered synthetic corpus to the 20-shot real
baseline raised exact match by **+3.06%** (3.06 percentage points), closing
**26.4%** of the gap to full-real training. Slot F1 improved by 4.40 points and
closed 46.6% of its gap. Filtering produced the strongest synthetic-data result
despite using one third as many synthetic rows as the unfiltered-full group.
These are primary-run results, not confidence intervals; seeds 43 and 44 for
`real_only` and `real_syn_filtered` are still pending.

![Primary M9 results](assets/m12_main_results.png)

## Results

### Primary seed-42 matrix

| Group | Training data | intent acc | intent macro-F1 | slot F1 | exact match | JSON-valid |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `zero_shot` | not trained | 10.66% | 23.12% | 0.00% | 8.10% | 17.38% |
| `real_only` | 20-shot real | 73.54% | 75.20% | 62.14% | 49.06% | 98.02% |
| `real_std_aug` | + classical augmentation | 74.31% | 75.59% | 62.58% | 46.81% | 96.23% |
| `real_syn_unfiltered_full` | + all unfiltered synthetic | 75.99% | 76.42% | 65.01% | 51.21% | 97.75% |
| `real_syn_unfiltered_eqn` | + equal-N unfiltered synthetic | 76.03% | 75.59% | 64.37% | 51.01% | 97.95% |
| `real_syn_filtered` | + filtered synthetic | 76.19% | 76.09% | 66.54% | 52.12% | 97.98% |
| `full_real` | full MASSIVE train | 84.53% | 81.65% | 71.58% | 60.66% | 99.73% |

The zero-shot row uses the frozen catalog prompt containing the valid intent and
slot labels. Trained groups use the frozen SFT prompt without that catalog, so
zero-shot should be read as a deployment baseline rather than a prompt-identical
ablation.

### Gap closed

`real_only` defines 0% and `full_real` defines 100%. The filtered synthetic run
changed the primary metrics as follows:

| Metric | Absolute change vs `real_only` | Gap closed |
| --- | ---: | ---: |
| Intent accuracy | +2.66 points | 24.2% |
| Intent macro-F1 | +0.89 points | 13.8% |
| Slot micro-F1 | +4.40 points | 46.6% |
| Exact match | +3.06 points | 26.4% |

### Per-intent movement

The largest improvements were `qa_factoid` (+51.77 points),
`qa_definition` (+33.33), and `transport_query` (+27.45). The largest
regressions were `general_quirky` (-31.95), `transport_ticket` (-22.86), and
`transport_taxi` (-17.39). Reporting both sides matters: the synthetic corpus
did not improve every intent.

![Per-intent movement](assets/m12_intent_movement.png)

## Does the filter pipeline earn its keep?

The three synthetic groups separate data quality from quantity. Against all
11,264 unfiltered rows, the 3,760-row filtered corpus improved intent accuracy
by 0.20 points, slot F1 by 1.53 points, and exact match by 0.91 points. Against
the equal-N unfiltered control, it improved intent accuracy by 0.17 points, slot
F1 by 2.17 points, and exact match by 1.11 points. On seed 42, the filter
therefore helped beyond simply changing the number of training rows.

![Filtered and unfiltered controls](assets/m12_filter_comparison.png)

### Filter funnel

The preregistered 8,000–9,000 accepted-row target was not met. Frozen F1–F6
retained 3,760 / 11,264 rows (33.38%); thresholds were not relaxed after seeing
the outcome.

| Stage | Removed | Remaining |
| --- | ---: | ---: |
| Generated / F1 schema | 0 | 11,264 |
| F2 label contract | 461 | 10,803 |
| F3 grounded slots | 738 | 10,065 |
| F4 Taiwan locale/language | 951 | 9,114 |
| F5 seed copy / synthetic duplicate / outlier | 5,106 | 4,008 |
| F6 Val/Test contamination exclusion | 248 | **3,760** |
| F7 independent judge audit | pending | pending |

![F1–F6 filter funnel](assets/m12_filter_funnel.png)

The dominant loss was 4,596 synthetic near-duplicates. Among 9,114 F1–F4
survivors, only 4,044 utterances were exact-text distinct. This corpus-scale mode
collapse was much less visible in the 500-row pilot and is retained as a
negative result. The 376-row F7 independent-judge sample is frozen and ready,
but its GPU audit has not yet run; no judge miss-rate claim is made yet.

## Cost and reproducibility

The measured core GPU path totals **14.440 h** on one RTX 4090:

| Phase | GPU wall-clock | Evidence |
| --- | ---: | --- |
| Synthetic generation | **4.073 h** | `reports/generation_report.json` |
| Primary training, seed 42 | **6.540 h** | six runs in `runs/m9_batch_report.json` |
| Trained evaluation, seed 42 | **2.777 h** | six runs in `results/m9_eval_batch_report.json` |
| Zero-shot evaluation | **1.050 h** | generation timing in the M8 report |
| **Measured core total** | **14.440 h** | excludes pending extra seeds, F7, and robustness inference |
| **API spend** | **$0** | all model work ran locally |

At the RTX 4090's 450 W TDP, 14.440 hours corresponds to a conservative
GPU-only upper-bound envelope of 6.498 kWh. This is not a wall-socket energy
measurement. The machine was not assumed to draw TDP continuously.

The ledger is generated at
[`reports/m12_resource_ledger.json`](reports/m12_resource_ledger.json); the
figures and ledger are rebuilt with:

```bash
python -m scripts.build_m12_artifacts
python -m scripts.verify_readme
```

## Robustness probe

The auxiliary perturbation manifest contains 8,922 rows spanning typo,
code-switching, and ASR-like noise. It is frozen and ready for inference, but it
has not yet been evaluated. Robustness results are therefore intentionally not
included in the headline table.

## Method

![FormosaNLU pipeline](assets/m12_pipeline.png)

### Generation recipes

| Recipe | Purpose |
| --- | --- |
| `paraphrase` | Label-preserving rewrites of seed utterances |
| `slot_substitution` | Procedural Taiwan-local slot replacement followed by a constrained natural-language rewrite |
| `noise_codeswitch` | Code-switching, typos, spoken particles, and ASR-like noise without breaking slot spans |
| `hard_negative` | Minimal pairs across confusable intents |

Labels are produced automatically; there is no per-sample manual annotation.
Human involvement was limited to spot-checking 20 samples. The frozen semantic
thresholds are: synthetic duplicate 0.999, seed copy 0.995, outlier 0.650, and
Val/Test contamination 0.990.

Full design: [`docs/DESIGN.md`](docs/DESIGN.md).

### Interactive comparison demo

M11 provides a side-by-side base-versus-filtered-adapter Gradio interface. The
real runtime loads one 4-bit Gemma model and toggles the LoRA adapter, avoiding
two simultaneous model copies.

```bash
uv sync --extra demo
python -m scripts.demo
```

For UI-only validation without loading model weights:

```bash
python -m scripts.demo --mock
```

## Reproduce

> Native Windows, one RTX 4090, no WSL required.

```bash
# 1. Environment
uv sync --extra demo
python -m scripts.check_env

# 2. Freeze or verify the split manifest
python -m src.data.freeze_split
python -m src.data.freeze_split --verify

# 3. Generate the frozen corpus
python -m src.synthetic.generate --pilot 500
python -m src.synthetic.generate --full 11264

# 4. Apply frozen F1-F6 filters
python -m src.filtering.run \
  --input data/generated/full_unfiltered.jsonl \
  --accepted data/filtered/full_f1_f4.jsonl \
  --rejected data/filtered/full_rejected_f1_f4.jsonl \
  --report reports/m6_cheap_filter_funnel.json
python -m src.filtering.embed_full --batch-size 64
python -m src.filtering.apply_semantic \
  --input data/filtered/full_f1_f4.jsonl \
  --cheap-report reports/m6_cheap_filter_funnel.json \
  --embeddings data/embeddings/m6_full_bge_m3.npz \
  --accepted data/filtered/full_f1_f6.jsonl \
  --rejected data/filtered/full_rejected_f5_f6.jsonl \
  --exclusions data/filtered/full_f6_exclusions.jsonl \
  --report reports/m6_full_filter_funnel.json

# 5. Prepare, validate, train, evaluate, and report
python -m scripts.prepare_m9_data
python -m scripts.train_all --validate-inputs
python -m scripts.m9_overnight
python -m scripts.m9_overnight --execute --confirm M9-OVERNIGHT-3760-4090
python -m scripts.eval --execute --confirm M9-EVAL-LOCAL-4090
python -m scripts.report_results

# 6. Rebuild and verify M12
python -m scripts.build_m12_artifacts
python -m scripts.verify_readme

# 7. Inspect the pending F7 and three-seed plans (CPU-only)
python -m scripts.judge_full
python -m scripts.m9_replicates

# Execute only after their printed sibling/GPU safety gates are green
python -m scripts.judge_full --execute --confirm F7-GPT-OSS-20B
python -m scripts.m9_replicates \
  --execute --confirm M9-REPLICATES-43-44-4090
```

The Colab notebook
[`notebooks/01_sft_student.ipynb`](notebooks/01_sft_student.ipynb) wraps the
same training code for portability. Its bundle, GPU-memory preflight,
two-minute Drive checkpoint sync, and resume path are prepared; the one-group
Colab evidence run still requires a user-operated Colab session.

## Leakage and contamination statement

- The generator never reads validation or test examples. Seeds come only from
  the frozen 20-shot train manifest.
- Validation and test are always real data and never enter training.
- Decontamination against Val/Test is exclusion-only: near-duplicates are
  removed, while Val/Test are never used to rank or select training samples.
- The robustness probe perturbs Test for evaluation only and never flows back
  into training.
- Split manifest, seed, and source hashes are recorded in
  [`splits/manifest.json`](splits/manifest.json).

## Limitations

- The primary M9 table currently has one seed. Four preregistered reruns
  (`real_only` and `real_syn_filtered`, seeds 43 and 44) are pending, so no
  variance or significance claim is made.
- F7 independent-judge auditing and robustness inference are pending.
- No per-recipe ablation was run; recipe-specific causal claims are out of
  scope.
- MASSIVE `zh-TW` is translated from English SLURP and may not reflect the full
  distribution of spontaneous Taiwan speech.
- Synthetic data inherits teacher biases and Taiwan-specific knowledge gaps.
- F5 removed 4,596 synthetic near-duplicates, demonstrating substantial
  generator mode collapse.

## Licenses

| Artifact | License |
| --- | --- |
| Code in this repository | MIT ([LICENSE](LICENSE)) |
| MASSIVE `zh-TW` seed data | CC BY 4.0 |
| Teacher, judge, and student weights | Apache-2.0; see upstream model cards |
| Synthetic dataset | See [`docs/data_card.md`](docs/data_card.md) |
| LoRA adapter | Apache-2.0, inherited from the student base model |

## Roadmap

Complete the extra-seed uncertainty runs, F7 audit, robustness probe, and one
real-model demo capture; then perform the clean-environment M13 release audit.
A future extension could apply the same pipeline to Taiwan-specific knowledge
distillation and evaluate with TMMLU+ and community tooling such as
`twinkle-eval`.

## Documents

| File | Purpose |
| --- | --- |
| [`CLAUDE.md`](CLAUDE.md) | Repository working rules |
| [`PLAN.md`](PLAN.md) | Milestones, verification, and current status |
| [`docs/DESIGN.md`](docs/DESIGN.md) | Data pipeline design |
| [`docs/DESIGN_PHASE2.md`](docs/DESIGN_PHASE2.md) | Training, evaluation, demo, and release design |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | ADR-style decision log |
| [`docs/teacher_choice.md`](docs/teacher_choice.md) | Model selection and licensing analysis |
| [`docs/data_card.md`](docs/data_card.md) | Synthetic dataset card |
| [`docs/instructions_for_me.md`](docs/instructions_for_me.md) | Human-operated Colab, Hugging Face, and GitHub steps |
