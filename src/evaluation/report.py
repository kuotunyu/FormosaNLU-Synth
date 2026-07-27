"""Build the M10 seven-row table and comparison diagnostics from raw reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.training.train import REPO_ROOT

GROUPS = (
    "zero_shot",
    "real_only",
    "real_std_aug",
    "real_syn_unfiltered_full",
    "real_syn_unfiltered_eqn",
    "real_syn_filtered",
    "full_real",
)
METRICS = (
    "intent_accuracy",
    "intent_macro_f1",
    "slot_micro_f1",
    "exact_match",
    "json_valid_rate",
)
REAL_ROWS = {
    "real_only": 1176,
    "real_std_aug": 1176,
    "real_syn_unfiltered_full": 1176,
    "real_syn_unfiltered_eqn": 1176,
    "real_syn_filtered": 1176,
    "full_real": 11514,
}


def gap_closed(
    score: float,
    *,
    real_only: float,
    full_real: float,
    minimum_denominator: float = 0.01,
) -> dict[str, float | bool | None]:
    denominator = full_real - real_only
    reliable = abs(denominator) >= minimum_denominator
    return {
        "absolute_delta": score - real_only,
        "denominator": denominator,
        "gap_closed_percent": (
            100.0 * (score - real_only) / denominator if reliable else None
        ),
        "reliable": reliable,
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _checkpoint_step(path: str | None) -> int | None:
    if not path:
        return None
    name = Path(path).name
    if not name.startswith("checkpoint-"):
        return None
    try:
        return int(name.removeprefix("checkpoint-"))
    except ValueError:
        return None


def _best_epoch(metrics_path: Path, best_step: int | None) -> float | None:
    if best_step is None or not metrics_path.exists():
        return None
    with metrics_path.open("r", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    candidates = [row for row in rows if row.get("step") == best_step and "eval_loss" in row]
    if not candidates:
        return None
    epoch = candidates[-1].get("epoch")
    return float(epoch) if epoch is not None else None


def _zero_shot_row(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "reports" / "m8_zeroshot_baseline.json"
    if not path.exists():
        return {"group": "zero_shot", "status": "missing"}
    report = _load_json(path)
    return {
        "group": "zero_shot",
        "status": "complete",
        "metrics": report["metrics"],
        "best_checkpoint_step": None,
        "best_epoch": None,
        "real_sample_exposure_estimate": 0,
        "performance": {
            "output_tokens_per_second": report.get("output_tokens_per_second"),
            "peak_gpu_memory_mib": report.get("peak_device_wide_gpu_memory_mib"),
            "mean_latency_seconds": (
                report["wall_seconds"] / report["completed"]
                if report.get("completed")
                else None
            ),
        },
        "per_intent": report.get("per_intent", {}),
    }


def _trained_row(repo_root: Path, group: str, seed: int) -> dict[str, Any]:
    eval_path = repo_root / "reports" / "m9" / f"{group}_seed_{seed}.json"
    run_dir = repo_root / "runs" / group / f"seed_{seed}"
    run_path = run_dir / "run_report.json"
    if not eval_path.exists() or not run_path.exists():
        return {
            "group": group,
            "seed": seed,
            "status": "missing",
            "missing": [
                str(path.relative_to(repo_root))
                for path in (run_path, eval_path)
                if not path.exists()
            ],
        }
    evaluation = _load_json(eval_path)
    run = _load_json(run_path)
    best_step = _checkpoint_step(run.get("best_model_checkpoint"))
    effective_batch = int(run["effective_batch_size"])
    train_examples = int(run["train_examples"])
    real_exposure = (
        round(best_step * effective_batch * REAL_ROWS[group] / train_examples)
        if best_step is not None
        else None
    )
    return {
        "group": group,
        "seed": seed,
        "status": "complete",
        "metrics": evaluation["metrics"],
        "best_checkpoint_step": best_step,
        "best_epoch": _best_epoch(run_dir / "metrics.jsonl", best_step),
        "real_sample_exposure_estimate": real_exposure,
        "real_sample_exposure_note": (
            "step × effective_batch × real_rows / assembled_train_rows; "
            "rounded because sampler order is not logged per example"
        ),
        "performance": {
            "output_tokens_per_second": evaluation.get("output_tokens_per_second"),
            "peak_gpu_memory_mib": evaluation.get("peak_device_wide_gpu_memory_mib"),
            "mean_latency_seconds": (
                evaluation["wall_seconds"] / evaluation["completed"]
                if evaluation.get("completed")
                else None
            ),
        },
        "per_intent": evaluation.get("per_intent", {}),
    }


def build_results(*, repo_root: Path = REPO_ROOT, seed: int = 42) -> dict[str, Any]:
    rows = [_zero_shot_row(repo_root)]
    rows.extend(_trained_row(repo_root, group, seed) for group in GROUPS[1:])
    complete = {row["group"]: row for row in rows if row["status"] == "complete"}
    gaps: dict[str, dict[str, dict[str, float | bool | None]]] = {}
    if "real_only" in complete and "full_real" in complete:
        for group, row in complete.items():
            if group == "zero_shot":
                continue
            gaps[group] = {
                metric: gap_closed(
                    float(row["metrics"][metric]),
                    real_only=float(complete["real_only"]["metrics"][metric]),
                    full_real=float(complete["full_real"]["metrics"][metric]),
                )
                for metric in METRICS
            }
    movements: list[dict[str, Any]] = []
    if "real_only" in complete and "real_syn_filtered" in complete:
        real_intents = complete["real_only"]["per_intent"]
        filtered_intents = complete["real_syn_filtered"]["per_intent"]
        for intent in sorted(set(real_intents) | set(filtered_intents)):
            real_accuracy = float(real_intents[intent]["accuracy"])
            filtered_accuracy = float(filtered_intents[intent]["accuracy"])
            movements.append(
                {
                    "intent": intent,
                    "real_only_accuracy": real_accuracy,
                    "filtered_accuracy": filtered_accuracy,
                    "absolute_delta": filtered_accuracy - real_accuracy,
                }
            )
        movements.sort(key=lambda row: (-row["absolute_delta"], row["intent"]))
    missing = [row["group"] for row in rows if row["status"] != "complete"]
    return {
        "schema_version": 1,
        "status": "complete" if not missing else "pending",
        "seed": seed,
        "rows": rows,
        "missing_groups": missing,
        "gap_closed": gaps,
        "per_intent_movement": movements,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# M10 Main Results",
        "",
        f"Status: **{payload['status']}**.",
        "",
        "| Group | Intent acc | Macro-F1 | Slot F1 | Exact | JSON-valid | "
        "Best step | Epoch | Real exposure* |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["rows"]:
        if row["status"] != "complete":
            lines.append(
                f"| `{row['group']}` | pending | pending | pending | "
                "pending | pending | — | — | — |"
            )
            continue
        metrics = row["metrics"]
        step = row["best_checkpoint_step"]
        epoch = row["best_epoch"]
        exposure = row["real_sample_exposure_estimate"]
        lines.append(
            f"| `{row['group']}` | {metrics['intent_accuracy']:.2%} | "
            f"{metrics['intent_macro_f1']:.2%} | {metrics['slot_micro_f1']:.2%} | "
            f"{metrics['exact_match']:.2%} | {metrics['json_valid_rate']:.2%} | "
            f"{step if step is not None else '—'} | "
            f"{epoch if epoch is not None else '—'} | "
            f"{exposure if exposure is not None else '—'} |"
        )
    lines.extend(
        [
            "",
            "\\* Real exposure is a clearly marked estimate: best step × effective "
            "batch × real rows / assembled rows.",
        ]
    )
    if payload["gap_closed"]:
        lines.extend(
            [
                "",
                "## Gap closed",
                "",
                "| Group | Metric | Absolute delta | Gap closed | Reliable |",
                "|---|---|---:|---:|---|",
            ]
        )
        for group, metrics in payload["gap_closed"].items():
            for metric, values in metrics.items():
                ratio = values["gap_closed_percent"]
                lines.append(
                    f"| `{group}` | `{metric}` | "
                    f"{values['absolute_delta']:+.2%} | "
                    f"{ratio:.1f}% | yes |"
                    if ratio is not None
                    else f"| `{group}` | `{metric}` | "
                    f"{values['absolute_delta']:+.2%} | unreliable | no |"
                )
    if payload["per_intent_movement"]:
        movements = payload["per_intent_movement"]
        lines.extend(
            [
                "",
                "## Per-intent movement: filtered vs real-only",
                "",
                "Largest gains:",
                "",
            ]
        )
        lines.extend(
            f"- `{row['intent']}`: {row['absolute_delta']:+.2%}"
            for row in movements[:10]
        )
        lines.extend(["", "Largest regressions:", ""])
        lines.extend(
            f"- `{row['intent']}`: {row['absolute_delta']:+.2%}"
            for row in reversed(movements[-10:])
        )
    if payload["missing_groups"]:
        lines.extend(
            [
                "",
                "Pending trained reports: "
                + ", ".join(f"`{group}`" for group in payload["missing_groups"])
                + ".",
            ]
        )
    lines.extend(
        [
            "",
            "> JSON-invalid rows remain in every metric denominator. Gap-closed ratios",
            "> are emitted only when the real-only → full-real denominator is at least 0.01.",
            "",
        ]
    )
    return "\n".join(lines)
