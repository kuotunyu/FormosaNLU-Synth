# FormosaNLU — Synthetic Data Distillation for Traditional Chinese (Taiwan) NLU

> **Status: work in progress.** This README is a placeholder skeleton. Every
> number, table and figure is filled in at **M12** and must be reproducible from
> raw artifacts under `runs/` and `reports/` — nothing here is written by hand.
> Section order follows decision **D-008** (see `docs/DECISIONS.md`).

Can LLM-generated synthetic data rescue a small model in a low-resource setting?
This project measures it on **Traditional Chinese (Taiwan) spoken-language NLU** —
joint intent classification + slot filling with a fixed JSON output contract.

| | |
| --- | --- |
| **Dataset** | MASSIVE `zh-TW` (CC BY 4.0) — 60 intents, 55 slot types |
| **Low-resource setting** | `min(20, available)` samples per intent from train, `seed=42` |
| **Teacher** | Qwen 3 open-weight, run locally via Ollama (Apache-2.0) |
| **Student** | `google/gemma-4-E4B-it`, 4-bit QLoRA (Apache-2.0) |
| **Judge** | gpt-oss open-weight (Apache-2.0) |
| **API cost** | **$0** — everything runs on one RTX 4090 |

Teacher, student and judge come from **three different model families**, all
Apache-2.0. Cross-family distillation rules out the "same family, of course it
works" objection.

---

## TL;DR

<!-- FILL AT M12: one headline number + one sentence.
     Format: "Synthetic data closed X% of the gap between a 20-shot baseline and
     training on the full 11,514-sample train set." Plus one sentence on whether
     filtering mattered. If synthetic data did NOT help, say so here — negative
     results are reported, not buried. -->

---

## Results

### Main table

<!-- FILL AT M12: seven rows — zero-shot + six trained groups.
     Columns: intent acc / intent macro-F1 / slot F1 / exact match / JSON-valid
     rate, plus best-checkpoint step, epochs at that step, and real-sample
     exposure count.
     Note explicitly that the zero-shot row uses a different prompt (it must be
     given the label list; the trained groups are not). -->

| Group | Training data | intent acc | intent macro-F1 | slot F1 | exact match | JSON-valid |
| --- | --- | --- | --- | --- | --- | --- |
| `zero_shot` | *(not trained)* | | | | | |
| `real_only` | 20-shot real | | | | | |
| `real_std_aug` | + classical text augmentation | | | | | |
| `real_syn_unfiltered_full` | + unfiltered synthetic (all) | | | | | |
| `real_syn_unfiltered_eqn` | + unfiltered synthetic (equal-N) | | | | | |
| `real_syn_filtered` | + filtered synthetic | | | | | |
| `full_real` | full MASSIVE train (11,514) | | | | | |

### Gap closed

`real_only` = 0%, `full_real` = 100%. How much of that gap did synthetic data
recover?

<!-- FILL AT M12: gap-closed % per metric, headline on exact match.
     ALWAYS report the absolute delta alongside the ratio. If
     (full_real - real_only) is small, the ratio is unstable — mark it
     "not reliable" rather than quoting a big meaningless percentage. -->

### Per-intent movement

<!-- FILL AT M12: real_syn_filtered vs real_only, per-intent accuracy delta,
     sorted. Show BOTH the biggest gains and the biggest regressions — the
     regressions usually say more about how synthetic data fails. -->

---

## Does the filter pipeline earn its keep?

The whole point of this project is the *data engineering*, not the API call.
Three groups isolate quality from quantity:

<!-- FILL AT M12: bar chart comparing unfiltered-full / unfiltered-equal-N /
     filtered. Equal-N is what separates "the filter improved quality" from
     "we just added more rows". -->

### Filter funnel

<!-- FILL AT M6/M12: generated -> F1 schema -> F2 labels -> F3 groundedness ->
     F4 locale -> F5 dedup -> F6 decontamination -> F7 judge -> final count.
     Include the count removed at each gate. -->

### Judge-reported miss rate

<!-- FILL AT M12: the judge audits ~10% of samples and reports how many bad
     samples the first six gates let through. This is measured evidence that the
     filter works, not a claim that it does. -->

---

## Cost and reproducibility

Generated, trained, evaluated and demoed entirely on **one RTX 4090 (24 GB) on
native Windows**. No WSL. No API spend.

<!-- FILL AT M12: resource ledger — GPU wall-clock split by phase
     (generation / training / evaluation), estimated electricity, and the
     equivalent cost had this been generated through a commercial API. -->

| Phase | GPU wall-clock | Notes |
| --- | --- | --- |
| Synthetic generation | | local teacher via Ollama |
| Training (10 runs) | | six groups + 3-seed reruns |
| Evaluation | | |
| **API spend** | — | **$0** |

---

## Robustness probe (auxiliary analysis, not a headline metric)

MASSIVE `zh-TW` is translated from English SLURP, so its register skews toward
translationese. Synthetic samples are tagged `massive_like` or `tw_colloquial`,
and we report how the colloquial axis behaves on both the untouched test set and
a perturbed probe set (typos, code-switching, ASR-like noise).

<!-- FILL AT M12: results for both axes. If the Taiwanese-colloquial axis costs
     accuracy on the original test set, say so — that is risk R-2 being
     confirmed, and it belongs in Limitations, not hidden. -->

---

## Method

<!-- FILL AT M12: pipeline diagram in assets/ -->

### Generation recipes

| Recipe | What it does |
| --- | --- |
| `paraphrase` | Label-preserving rewrites of the seed utterances |
| `slot_substitution` | **Procedural** slot-value replacement (Taiwan-local values), then the teacher rewrites it into natural speech without touching the values — so the ground truth comes from code, not from the model |
| `noise_codeswitch` | Code-switching, typos, spoken particles, ASR-like noise; never breaks a slot span |
| `hard_negative` | Minimal pairs across confusable intents (e.g. "play Jay Chou" vs "search for Jay Chou's songs") |

Labels are produced **automatically** — there is no per-sample manual annotation
anywhere in this project. Human involvement was limited to spot-checking 20
samples.

Full design: [`docs/DESIGN.md`](docs/DESIGN.md).

---

## Reproduce

> Runs on native Windows with a single RTX 4090. No WSL required.

```bash
# 1. Environment
uv venv && uv pip sync requirements.txt
python -m scripts.check_env

# 2. Freeze the split manifest (must reproduce the same SHA256)
python -m src.data.freeze_split
python -m src.data.freeze_split --verify

# 3. Generate synthetic data (local teacher, no API keys needed)
python -m src.synthetic.generate --pilot 500
python -m src.synthetic.generate --full

# 4. Filter
python -m src.filtering.run
python -m src.filtering.decontaminate

# 5. Train all groups locally (overnight batch, resumable)
python -m scripts.train_all

# 6. Evaluate
python -m scripts.eval --all-groups
python -m scripts.eval --probe

# 7. Verify every number in this README recomputes from raw artifacts
python -m scripts.verify_readme
```

A Colab notebook (`notebooks/01_sft_student.ipynb`) wraps the same training code
for portability; one group was actually run there to prove it works.

<!-- FILL AT M13: confirm a clean venv walks this end to end -->

---

## Leakage and contamination statement

<!-- FILL AT M13 -->

- The generator never read the validation or test split. Seeds come only from the
  frozen 20-shot train manifest, and `src/synthetic/` is audited for imports that
  could reach Val/Test.
- Validation and test are **always** real data, never synthetic.
- Decontamination against Val/Test was **exclusion-only**: near-duplicates were
  removed; Val/Test were never used to rank, weight, or select anything. The
  audit log (removed ids, similarity scores, matched test ids) ships with the
  dataset.
- The robustness probe perturbs the test set for *evaluation only*. Perturbed
  test data never flows back into training.
- Split manifest, seed and source SHA256: [`splits/manifest.json`](splits/manifest.json).

---

## Limitations

<!-- FILL AT M12: including any negative results. These are reported, not hidden. -->

- No per-recipe ablation was run (`docs/DECISIONS.md` D-004) — the Colab/GPU cost
  was not judged worth it.
- Synthetic data inherits the teacher's biases and Taiwan-specific knowledge gaps.
- Seeds come from a 20-shot sample, so coverage of rare intents and rare slot
  types is thin.
- `<FILL AT M12>`

---

## Licenses

| Artifact | License |
| --- | --- |
| Code in this repo | MIT ([LICENSE](LICENSE)) |
| MASSIVE `zh-TW` seed data | CC BY 4.0 |
| Teacher / judge / student weights | Apache-2.0 (see upstream model cards) |
| Synthetic dataset | [`docs/data_card.md`](docs/data_card.md) |
| Released LoRA adapter | Apache-2.0, inherited from the student base model |

---

## Roadmap

<!-- FILL AT M12: short paragraph only, not implemented in this project.
     Same pipeline applied to Taiwan-specific knowledge distillation, evaluated
     with TMMLU+; mention Taiwanese community eval tooling such as twinkle-eval. -->

---

## Documents

| File | Purpose |
| --- | --- |
| [CLAUDE.md](CLAUDE.md) | Working rules for this repo (read first) |
| [PLAN.md](PLAN.md) | Milestones, verification methods, current status |
| [docs/DESIGN.md](docs/DESIGN.md) | Phase 1 — data pipeline design |
| [docs/DESIGN_PHASE2.md](docs/DESIGN_PHASE2.md) | Phase 2 — training, evaluation, demo, release |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Decision log (ADR style) |
| [docs/teacher_choice.md](docs/teacher_choice.md) | Teacher/judge selection and licensing analysis |
| [docs/data_card.md](docs/data_card.md) | Synthetic dataset card |
| [docs/instructions_for_me.md](docs/instructions_for_me.md) | Steps that require a human (Colab, HF, GitHub) |
