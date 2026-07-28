"""Materialize M12 charts and the reproducible GPU resource ledger."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.training.train import REPO_ROOT

M10_REPORT = REPO_ROOT / "reports" / "m10_main_results.json"
GENERATION_REPORT = REPO_ROOT / "reports" / "generation_report.json"
TRAINING_REPORT = REPO_ROOT / "runs" / "m9_batch_report.json"
EVALUATION_REPORT = REPO_ROOT / "results" / "m9_eval_batch_report.json"
ZERO_SHOT_REPORT = REPO_ROOT / "reports" / "m8_zeroshot_baseline.json"
RESOURCE_REPORT = REPO_ROOT / "reports" / "m12_resource_ledger.json"
ASSET_DIR = REPO_ROOT / "assets"

COLORS = {
    "ink": "#071218",
    "panel": "#102832",
    "paper": "#eaf6f5",
    "muted": "#8ba8ac",
    "cyan": "#7ed9e2",
    "amber": "#ffb84d",
    "coral": "#ff6b4a",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _elapsed_hours(started_at: str, finished_at: str) -> float:
    started = datetime.fromisoformat(started_at)
    finished = datetime.fromisoformat(finished_at)
    return (finished - started).total_seconds() / 3600


def build_resource_ledger(
    *,
    generation: dict[str, Any],
    training: dict[str, Any],
    evaluation: dict[str, Any],
    zero_shot: dict[str, Any],
) -> dict[str, Any]:
    """Summarize measured wall times without converting them into cloud costs."""
    generation_hours = float(generation["generation"]["wall_seconds"]) / 3600
    training_hours = _elapsed_hours(training["started_at"], training["finished_at"])
    evaluation_hours = _elapsed_hours(evaluation["started_at"], evaluation["finished_at"])
    zero_shot_hours = float(zero_shot["wall_seconds"]) / 3600
    measured_gpu_hours = (
        generation_hours + training_hours + evaluation_hours + zero_shot_hours
    )
    return {
        "schema_version": 1,
        "status": "complete_primary_seed_42",
        "hardware": "NVIDIA GeForce RTX 4090 24 GB",
        "api_spend_usd": 0.0,
        "phases": {
            "synthetic_generation": {
                "wall_hours": generation_hours,
                "basis": "reports/generation_report.json generation.wall_seconds",
            },
            "primary_training_seed_42": {
                "wall_hours": training_hours,
                "runs": len(training["runs"]),
                "basis": "runs/m9_batch_report.json started_at to finished_at",
            },
            "trained_evaluation_seed_42": {
                "wall_hours": evaluation_hours,
                "runs": len(evaluation["runs"]),
                "basis": "results/m9_eval_batch_report.json started_at to finished_at",
            },
            "zero_shot_evaluation": {
                "wall_hours": zero_shot_hours,
                "basis": "reports/m8_zeroshot_baseline.json summed generation wall_seconds",
            },
        },
        "measured_core_gpu_hours": measured_gpu_hours,
        "gpu_tdp_watts": 450,
        "gpu_tdp_energy_upper_bound_kwh": measured_gpu_hours * 0.45,
        "energy_note": (
            "Upper-bound GPU-only envelope using the RTX 4090 450 W TDP; "
            "not a wall-socket measurement and excludes extra-seed reruns."
        ),
        "pending": [
            "real_only seeds 43 and 44",
            "real_syn_filtered seeds 43 and 44",
            "F7 independent judge audit",
            "robustness probe inference",
        ],
    }


def _style_axis(axis: Any, *, grid: bool = True) -> None:
    axis.set_facecolor(COLORS["ink"])
    axis.tick_params(colors=COLORS["muted"], labelsize=9)
    for spine in axis.spines.values():
        spine.set_color("#21434b")
    axis.xaxis.label.set_color(COLORS["paper"])
    axis.yaxis.label.set_color(COLORS["paper"])
    axis.title.set_color(COLORS["paper"])
    if grid:
        axis.grid(axis="y", color="#21434b", alpha=0.55, linewidth=0.7)
        axis.set_axisbelow(True)


def _save(figure: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(
        path,
        dpi=190,
        bbox_inches="tight",
        facecolor=COLORS["ink"],
    )
    plt.close(figure)


def chart_main_results(m10: dict[str, Any], output: Path) -> None:
    rows = [row for row in m10["rows"] if row["group"] != "zero_shot"]
    labels = [
        "Real only",
        "Std aug",
        "Unfiltered all",
        "Unfiltered =N",
        "Filtered",
        "Full real",
    ]
    metrics = [
        ("intent_accuracy", "Intent acc", COLORS["cyan"]),
        ("slot_micro_f1", "Slot F1", COLORS["amber"]),
        ("exact_match", "Exact match", COLORS["coral"]),
    ]
    figure, axis = plt.subplots(figsize=(11, 5.4), facecolor=COLORS["ink"])
    x_positions = range(len(rows))
    width = 0.24
    for metric_index, (key, label, color) in enumerate(metrics):
        offset = (metric_index - 1) * width
        values = [float(row["metrics"][key]) * 100 for row in rows]
        bars = axis.bar(
            [x + offset for x in x_positions],
            values,
            width=width,
            label=label,
            color=color,
            alpha=0.92,
        )
        axis.bar_label(
            bars,
            fmt="%.1f",
            padding=3,
            color=COLORS["paper"],
            fontsize=7,
        )
    axis.set_xticks(list(x_positions), labels, rotation=16, ha="right")
    axis.set_ylim(40, 90)
    axis.set_ylabel("Score (%)")
    axis.set_title("M9 primary runs · seed 42 · untouched MASSIVE zh-TW Test")
    legend = axis.legend(frameon=False, ncols=3, loc="upper left")
    for text in legend.get_texts():
        text.set_color(COLORS["paper"])
    _style_axis(axis)
    _save(figure, output)


def chart_filter_comparison(m10: dict[str, Any], output: Path) -> None:
    wanted = {
        row["group"]: row
        for row in m10["rows"]
        if row["group"]
        in {
            "real_syn_unfiltered_full",
            "real_syn_unfiltered_eqn",
            "real_syn_filtered",
        }
    }
    order = [
        "real_syn_unfiltered_full",
        "real_syn_unfiltered_eqn",
        "real_syn_filtered",
    ]
    labels = ["Unfiltered all\n11,264 syn", "Unfiltered =N\n3,760 syn", "Filtered\n3,760 syn"]
    keys = ["intent_accuracy", "slot_micro_f1", "exact_match"]
    metric_labels = ["Intent acc", "Slot F1", "Exact match"]
    colors = [COLORS["cyan"], COLORS["amber"], COLORS["coral"]]
    figure, axis = plt.subplots(figsize=(8.7, 5.1), facecolor=COLORS["ink"])
    x_positions = range(len(order))
    width = 0.24
    for metric_index, (key, metric_label, color) in enumerate(
        zip(keys, metric_labels, colors, strict=True)
    ):
        offset = (metric_index - 1) * width
        values = [float(wanted[group]["metrics"][key]) * 100 for group in order]
        bars = axis.bar(
            [x + offset for x in x_positions],
            values,
            width=width,
            label=metric_label,
            color=color,
        )
        axis.bar_label(
            bars,
            fmt="%.2f",
            padding=3,
            color=COLORS["paper"],
            fontsize=8,
        )
    axis.set_xticks(list(x_positions), labels)
    axis.set_ylim(48, 79)
    axis.set_ylabel("Score (%)")
    axis.set_title("Does filtering earn its keep?")
    legend = axis.legend(frameon=False, ncols=3, loc="upper left")
    for text in legend.get_texts():
        text.set_color(COLORS["paper"])
    _style_axis(axis)
    _save(figure, output)


def chart_filter_funnel(generation: dict[str, Any], output: Path) -> None:
    filtering = generation["filtering"]
    stages = ["F1 schema", "F2 labels", "F3 slots", "F4 locale", "F5 semantic", "F6 decontam"]
    remaining = [
        int(filtering["f1_json_valid"]),
        int(filtering["f1_json_valid"])
        - int(filtering["reject_reasons"]["F2_LABEL_CONTRACT_INTENT"])
        - int(filtering["reject_reasons"]["F2_LABEL_CONTRACT_SLOTS"]),
        int(filtering["f1_f3_passed"]),
        int(filtering["f1_f4_passed"]),
        int(filtering["f1_f6_passed"])
        + int(filtering["reject_reasons"]["F6_CONTAM_EVAL"]),
        int(filtering["f1_f6_passed"]),
    ]
    figure, axis = plt.subplots(figsize=(9.3, 5.2), facecolor=COLORS["ink"])
    colors = [COLORS["cyan"]] * 4 + [COLORS["amber"], COLORS["coral"]]
    bars = axis.barh(stages, remaining, color=colors, alpha=0.92)
    axis.invert_yaxis()
    axis.bar_label(
        bars,
        labels=[f"{value:,}" for value in remaining],
        padding=6,
        color=COLORS["paper"],
        fontsize=10,
    )
    axis.set_xlim(0, max(remaining) * 1.14)
    axis.set_xlabel("Rows remaining")
    axis.set_title("Frozen F1–F6 funnel · thresholds were not relaxed")
    _style_axis(axis, grid=False)
    _save(figure, output)


def chart_intent_movement(m10: dict[str, Any], output: Path) -> None:
    movements = m10["per_intent_movement"]
    selected = movements[:5] + movements[-5:]
    selected.sort(key=lambda row: row["absolute_delta"])
    labels = [row["intent"] for row in selected]
    values = [float(row["absolute_delta"]) * 100 for row in selected]
    colors = [COLORS["coral"] if value < 0 else COLORS["cyan"] for value in values]
    figure, axis = plt.subplots(figsize=(9.3, 5.4), facecolor=COLORS["ink"])
    bars = axis.barh(labels, values, color=colors)
    axis.axvline(0, color=COLORS["paper"], linewidth=0.8, alpha=0.55)
    axis.bar_label(
        bars,
        fmt="%+.1f",
        padding=4,
        color=COLORS["paper"],
        fontsize=9,
    )
    axis.set_xlabel("Filtered synthetic − real-only accuracy (percentage points)")
    axis.set_title("Largest per-intent movements · gains and regressions")
    _style_axis(axis, grid=False)
    _save(figure, output)


def chart_pipeline(output: Path) -> None:
    figure, axis = plt.subplots(figsize=(12, 2.7), facecolor=COLORS["ink"])
    axis.set_xlim(0, 12)
    axis.set_ylim(0, 2.7)
    axis.axis("off")
    steps = [
        ("20-shot\nreal seeds", COLORS["cyan"]),
        ("Qwen teacher\n11,264 rows", COLORS["amber"]),
        ("Frozen F1–F6\n3,760 rows", COLORS["coral"]),
        ("Gemma 4\nQLoRA", COLORS["cyan"]),
        ("2,974-row\nreal Test", COLORS["amber"]),
        ("M10 metrics\n+ demo", COLORS["coral"]),
    ]
    box_width = 1.55
    positions = [0.15, 2.2, 4.25, 6.3, 8.35, 10.3]
    for index, ((label, color), x_pos) in enumerate(zip(steps, positions, strict=True)):
        axis.add_patch(
            plt.Rectangle(
                (x_pos, 0.72),
                box_width,
                1.25,
                facecolor=COLORS["panel"],
                edgecolor=color,
                linewidth=1.5,
            )
        )
        axis.text(
            x_pos + box_width / 2,
            1.34,
            label,
            color=COLORS["paper"],
            ha="center",
            va="center",
            fontsize=10,
            weight="bold",
        )
        if index < len(steps) - 1:
            axis.annotate(
                "",
                xy=(positions[index + 1] - 0.14, 1.34),
                xytext=(x_pos + box_width + 0.14, 1.34),
                arrowprops={"arrowstyle": "->", "color": COLORS["muted"], "lw": 1.3},
            )
    axis.text(
        0.15,
        2.33,
        "FORMOSANLU · LOCAL SYNTHETIC-DATA DISTILLATION",
        color=COLORS["amber"],
        fontsize=10,
        weight="bold",
    )
    _save(figure, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-dir", type=Path, default=ASSET_DIR)
    parser.add_argument("--resource-report", type=Path, default=RESOURCE_REPORT)
    args = parser.parse_args()

    generation = _load(GENERATION_REPORT)
    m10 = _load(M10_REPORT)
    training = _load(TRAINING_REPORT)
    evaluation = _load(EVALUATION_REPORT)
    zero_shot = _load(ZERO_SHOT_REPORT)
    ledger = build_resource_ledger(
        generation=generation,
        training=training,
        evaluation=evaluation,
        zero_shot=zero_shot,
    )
    args.resource_report.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    chart_main_results(m10, args.asset_dir / "m12_main_results.png")
    chart_filter_comparison(m10, args.asset_dir / "m12_filter_comparison.png")
    chart_filter_funnel(generation, args.asset_dir / "m12_filter_funnel.png")
    chart_intent_movement(m10, args.asset_dir / "m12_intent_movement.png")
    chart_pipeline(args.asset_dir / "m12_pipeline.png")
    print(
        f"M12 artifacts complete; core GPU hours={ledger['measured_core_gpu_hours']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

