"""Build paired statistical evidence from the frozen three-seed predictions."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from src.evaluation.metrics import score_row
from src.evaluation.parse import parse_prediction
from src.synthetic.labels import INTENTS
from src.training.train import REPO_ROOT

SEEDS = (42, 43, 44)
GROUPS = ("real_only", "real_syn_filtered")
METRICS = (
    "intent_accuracy",
    "intent_macro_f1",
    "slot_micro_f1",
    "exact_match",
    "json_valid_rate",
)
DEFAULT_REPETITIONS = 5_000
DEFAULT_BOOTSTRAP_SEED = 20260729
DEFAULT_JSON = REPO_ROOT / "reports" / "m14_paired_statistics.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports" / "m14_paired_statistics.md"


@dataclass(frozen=True)
class Components:
    """Vectorized row-level scoring components for one evaluated adapter."""

    expected_intent: np.ndarray
    predicted_intent: np.ndarray
    json_valid: np.ndarray
    intent_correct: np.ndarray
    exact_match: np.ndarray
    slot_true_positive: np.ndarray
    slot_false_positive: np.ndarray
    slot_false_negative: np.ndarray

    @property
    def rows(self) -> int:
        return int(self.expected_intent.shape[0])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_prediction_rows(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    indices = [int(row["generation_index"]) for row in rows]
    if indices != list(range(len(rows))):
        raise ValueError(f"Prediction indices are not contiguous in {path}")
    return rows


def validate_pair(
    baseline: list[dict[str, Any]],
    treatment: list[dict[str, Any]],
) -> None:
    if len(baseline) != len(treatment) or not baseline:
        raise ValueError("Paired predictions must have equal non-zero lengths")
    for left, right in zip(baseline, treatment, strict=True):
        if left["generation_index"] != right["generation_index"]:
            raise ValueError("Paired generation indices differ")
        if left["expected"] != right["expected"]:
            raise ValueError("Paired expected rows differ")


def build_components(rows: list[dict[str, Any]]) -> Components:
    intent_index = {intent: index for index, intent in enumerate(INTENTS)}
    expected_intent: list[int] = []
    predicted_intent: list[int] = []
    json_valid: list[bool] = []
    intent_correct: list[bool] = []
    exact_match: list[bool] = []
    slot_true_positive: list[int] = []
    slot_false_positive: list[int] = []
    slot_false_negative: list[int] = []

    for row in rows:
        expected = row["expected"]
        raw_prediction = str(row["raw_prediction"])
        scored = score_row(raw_prediction, expected)
        prediction, _ = parse_prediction(raw_prediction)
        expected_intent.append(intent_index[str(expected["intent"])])
        predicted_intent.append(intent_index[prediction.intent] if prediction is not None else -1)
        json_valid.append(scored.json_valid)
        intent_correct.append(scored.intent_correct)
        exact_match.append(scored.exact_match)
        slot_true_positive.append(sum((scored.expected_slots & scored.predicted_slots).values()))
        slot_false_positive.append(sum((scored.predicted_slots - scored.expected_slots).values()))
        slot_false_negative.append(sum((scored.expected_slots - scored.predicted_slots).values()))

    return Components(
        expected_intent=np.asarray(expected_intent, dtype=np.int16),
        predicted_intent=np.asarray(predicted_intent, dtype=np.int16),
        json_valid=np.asarray(json_valid, dtype=np.bool_),
        intent_correct=np.asarray(intent_correct, dtype=np.bool_),
        exact_match=np.asarray(exact_match, dtype=np.bool_),
        slot_true_positive=np.asarray(slot_true_positive, dtype=np.int16),
        slot_false_positive=np.asarray(slot_false_positive, dtype=np.int16),
        slot_false_negative=np.asarray(slot_false_negative, dtype=np.int16),
    )


def metrics_for_indices(components: Components, indices: np.ndarray) -> dict[str, float]:
    expected = components.expected_intent[indices]
    predicted = components.predicted_intent[indices]
    actual_total = np.bincount(expected, minlength=len(INTENTS))
    valid_prediction = predicted >= 0
    predicted_total = np.bincount(
        predicted[valid_prediction],
        minlength=len(INTENTS),
    )
    correct_prediction = valid_prediction & (predicted == expected)
    true_positive = np.bincount(
        predicted[correct_prediction],
        minlength=len(INTENTS),
    )
    denominator = actual_total + predicted_total
    per_intent_f1 = np.divide(
        2 * true_positive,
        denominator,
        out=np.zeros(len(INTENTS), dtype=np.float64),
        where=denominator != 0,
    )

    slot_tp = int(components.slot_true_positive[indices].sum())
    slot_fp = int(components.slot_false_positive[indices].sum())
    slot_fn = int(components.slot_false_negative[indices].sum())
    slot_denominator = 2 * slot_tp + slot_fp + slot_fn
    return {
        "intent_accuracy": float(components.intent_correct[indices].mean()),
        "intent_macro_f1": float(per_intent_f1.mean()),
        "slot_micro_f1": 2 * slot_tp / slot_denominator if slot_denominator else 1.0,
        "exact_match": float(components.exact_match[indices].mean()),
        "json_valid_rate": float(components.json_valid[indices].mean()),
    }


def exact_mcnemar(
    baseline: np.ndarray,
    treatment: np.ndarray,
) -> dict[str, int | float]:
    """Return the two-sided exact McNemar/binomial result for paired booleans."""
    if baseline.shape != treatment.shape or baseline.size == 0:
        raise ValueError("McNemar inputs must have equal non-zero shapes")
    losses = int(np.sum(baseline & ~treatment))
    gains = int(np.sum(~baseline & treatment))
    discordant = losses + gains
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(discordant, index) for index in range(min(losses, gains) + 1))
        p_value = min(1.0, 2 * tail / (2**discordant))
    return {
        "baseline_only_correct": losses,
        "filtered_only_correct": gains,
        "discordant": discordant,
        "p_value": p_value,
    }


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    """Return Holm-adjusted p-values while preserving the original keys."""
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    adjusted: dict[str, float] = {}
    running_max = 0.0
    total = len(ordered)
    for rank, (name, p_value) in enumerate(ordered):
        candidate = min(1.0, (total - rank) * p_value)
        running_max = max(running_max, candidate)
        adjusted[name] = running_max
    return {name: adjusted[name] for name in p_values}


def hierarchical_bootstrap(
    pairs: dict[int, tuple[Components, Components]],
    *,
    repetitions: int,
    random_seed: int,
) -> dict[str, dict[str, Any]]:
    """Bootstrap paired rows within resampled seeds and summarize metric deltas."""
    if repetitions <= 0:
        raise ValueError("Bootstrap repetitions must be positive")
    seeds = tuple(sorted(pairs))
    if not seeds:
        raise ValueError("At least one seed pair is required")
    row_counts = {pairs[seed][0].rows for seed in seeds}
    if len(row_counts) != 1:
        raise ValueError("Every seed must contain the same number of rows")
    rows = row_counts.pop()
    if any(pairs[seed][1].rows != rows for seed in seeds):
        raise ValueError("Baseline and treatment row counts differ")

    point_deltas: dict[str, list[float]] = {metric: [] for metric in METRICS}
    all_indices = np.arange(rows)
    for seed in seeds:
        baseline_metrics = metrics_for_indices(pairs[seed][0], all_indices)
        treatment_metrics = metrics_for_indices(pairs[seed][1], all_indices)
        for metric in METRICS:
            point_deltas[metric].append(treatment_metrics[metric] - baseline_metrics[metric])

    rng = np.random.default_rng(random_seed)
    draws = {metric: np.empty(repetitions, dtype=np.float64) for metric in METRICS}
    for repetition in range(repetitions):
        sampled_seed_positions = rng.integers(0, len(seeds), size=len(seeds))
        replicate_deltas = {metric: [] for metric in METRICS}
        for position in sampled_seed_positions:
            seed = seeds[int(position)]
            indices = rng.integers(0, rows, size=rows)
            baseline_metrics = metrics_for_indices(pairs[seed][0], indices)
            treatment_metrics = metrics_for_indices(pairs[seed][1], indices)
            for metric in METRICS:
                replicate_deltas[metric].append(
                    treatment_metrics[metric] - baseline_metrics[metric]
                )
        for metric in METRICS:
            draws[metric][repetition] = float(np.mean(replicate_deltas[metric]))

    return {
        metric: {
            "by_seed_percentage_points": {
                str(seed): point_deltas[metric][position] * 100
                for position, seed in enumerate(seeds)
            },
            "mean_delta_percentage_points": float(np.mean(point_deltas[metric]) * 100),
            "hierarchical_bootstrap_95_ci_percentage_points": [
                float(np.quantile(draws[metric], 0.025) * 100),
                float(np.quantile(draws[metric], 0.975) * 100),
            ],
        }
        for metric in METRICS
    }


def build_report(
    *,
    repetitions: int = DEFAULT_REPETITIONS,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> dict[str, Any]:
    pairs: dict[int, tuple[Components, Components]] = {}
    input_files: dict[str, dict[str, Any]] = {}
    exact_tests: dict[str, dict[str, Any]] = {}
    raw_p_values: dict[str, float] = {}
    expected_rows: int | None = None

    for seed in SEEDS:
        group_rows: dict[str, list[dict[str, Any]]] = {}
        for group in GROUPS:
            relative = Path("results") / "m9" / f"{group}_seed_{seed}.jsonl"
            path = REPO_ROOT / relative
            rows = load_prediction_rows(path)
            group_rows[group] = rows
            input_files[f"{group}_seed_{seed}"] = {
                "path": relative.as_posix(),
                "rows": len(rows),
                "sha256": sha256_file(path),
            }
        validate_pair(group_rows["real_only"], group_rows["real_syn_filtered"])
        if expected_rows is None:
            expected_rows = len(group_rows["real_only"])
        elif expected_rows != len(group_rows["real_only"]):
            raise ValueError("Seed row counts differ")

        baseline = build_components(group_rows["real_only"])
        treatment = build_components(group_rows["real_syn_filtered"])
        pairs[seed] = (baseline, treatment)
        for metric, left, right in (
            ("intent_accuracy", baseline.intent_correct, treatment.intent_correct),
            ("exact_match", baseline.exact_match, treatment.exact_match),
        ):
            name = f"{metric}_seed_{seed}"
            result = exact_mcnemar(left, right)
            exact_tests[name] = result
            raw_p_values[name] = float(result["p_value"])

    adjusted = holm_adjust(raw_p_values)
    for name, adjusted_p in adjusted.items():
        exact_tests[name]["holm_adjusted_p_value"] = adjusted_p
        exact_tests[name]["reject_at_0_05"] = adjusted_p < 0.05

    return {
        "schema_version": 1,
        "status": "complete",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "comparison": "real_syn_filtered minus real_only",
        "test_rows_per_seed": expected_rows,
        "seeds": list(SEEDS),
        "input_files": input_files,
        "hierarchical_bootstrap": {
            "repetitions": repetitions,
            "random_seed": bootstrap_seed,
            "method": (
                "Resample three seeds with replacement, then resample paired Test rows "
                "with replacement within each selected seed; average per-seed deltas."
            ),
            "metrics": hierarchical_bootstrap(
                pairs,
                repetitions=repetitions,
                random_seed=bootstrap_seed,
            ),
        },
        "exact_mcnemar": {
            "method": (
                "Two-sided exact McNemar/binomial test on paired row correctness; "
                "Holm correction across six intent/exact tests."
            ),
            "tests": exact_tests,
        },
        "interpretation_scope": (
            "Evidence applies to the frozen MASSIVE zh-TW Test set and this Gemma 4 "
            "training contract. It does not establish cross-model or cross-dataset "
            "generalization."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["hierarchical_bootstrap"]["metrics"]
    lines = [
        "# M14 Paired Statistical Evidence",
        "",
        f"- Comparison: `{report['comparison']}`",
        f"- Seeds: {', '.join(map(str, report['seeds']))}",
        f"- Paired Test rows per seed: {report['test_rows_per_seed']:,}",
        (
            "- Hierarchical bootstrap: "
            f"{report['hierarchical_bootstrap']['repetitions']:,} repetitions, "
            f"seed {report['hierarchical_bootstrap']['random_seed']}"
        ),
        "",
        "## Effect estimates",
        "",
        "| Metric | Seed deltas (percentage points) | Mean Δ | Hierarchical 95% CI |",
        "|---|---:|---:|---:|",
    ]
    for metric in METRICS:
        item = metrics[metric]
        seed_values = " / ".join(
            f"{value:+.2f}" for value in item["by_seed_percentage_points"].values()
        )
        lower, upper = item["hierarchical_bootstrap_95_ci_percentage_points"]
        lines.append(
            f"| `{metric}` | {seed_values} | "
            f"{item['mean_delta_percentage_points']:+.2f} | [{lower:+.2f}, {upper:+.2f}] |"
        )

    lines.extend(
        [
            "",
            "## Exact paired tests",
            "",
            "| Test | Baseline-only correct | Filtered-only correct | Exact p | Holm p |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for name, item in report["exact_mcnemar"]["tests"].items():
        lines.append(
            f"| `{name}` | {item['baseline_only_correct']} | "
            f"{item['filtered_only_correct']} | {item['p_value']:.3g} | "
            f"{item['holm_adjusted_p_value']:.3g} |"
        )

    lines.extend(
        [
            "",
            "## Scope",
            "",
            report["interpretation_scope"],
            "",
            "Prediction JSONL files remain ignored because they contain upstream Test "
            "utterances. Their paths, row counts, and SHA-256 values are recorded in the "
            "machine-readable JSON report.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=DEFAULT_REPETITIONS)
    parser.add_argument("--bootstrap-seed", type=int, default=DEFAULT_BOOTSTRAP_SEED)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    report = build_report(
        repetitions=args.repetitions,
        bootstrap_seed=args.bootstrap_seed,
    )
    args.json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.markdown.write_text(
        render_markdown(report),
        encoding="utf-8",
        newline="\n",
    )
    print(
        "M14 paired statistics complete: "
        f"{report['test_rows_per_seed']} rows × {len(report['seeds'])} seeds"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
