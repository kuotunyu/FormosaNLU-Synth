"""Summarize robustness probe results across seeds for one student family.

The probe batch writes one combined report per seed. This aggregates them into
the per-group mean and sample standard deviation, plus the paired
filtered-minus-real_only delta computed per seed and then averaged, which keeps
the pairing rather than differencing two independently averaged numbers.

Nothing here touches training data. The probe is evaluation-only.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from src.training.train import REPO_ROOT

GROUPS = ("real_only", "real_syn_filtered")
METRICS = (
    "intent_accuracy",
    "intent_macro_f1",
    "slot_micro_f1",
    "exact_match",
    "json_valid_rate",
)
DEFAULT_SEEDS = (42, 43, 44)


def report_path(target: str, seed: int) -> Path:
    """Seed 42 for gemma keeps the original M10 filename."""
    if target == "gemma" and seed == 42:
        return REPO_ROOT / "reports" / "m10_robustness.json"
    return REPO_ROOT / "reports" / f"m16_robustness_{target}_seed_{seed}.json"


def _spread(values: list[float]) -> dict[str, Any]:
    return {
        "values": values,
        "mean": statistics.fmean(values),
        # Sample standard deviation is undefined for a single observation; a
        # lone seed carries no spread information and must not report 0.0.
        "sample_std": statistics.stdev(values) if len(values) > 1 else None,
        "seeds_used": len(values),
    }


def summarize_robustness_seeds(
    reports_by_seed: dict[int, dict[str, Any]],
    *,
    target: str,
    expected_seeds: tuple[int, ...] | list[int] = DEFAULT_SEEDS,
) -> dict[str, Any]:
    """Aggregate complete per-seed reports; incomplete seeds are excluded.

    `expected_seeds` matters: a seed whose report file does not exist never
    reaches this function, so without it a one-seed summary would claim to be
    complete. Status is only `complete` when every expected seed contributed.
    """
    usable = {
        seed: report
        for seed, report in sorted(reports_by_seed.items())
        if report.get("status") == "complete"
    }
    skipped = sorted(set(reports_by_seed) - set(usable))
    absent = sorted(set(expected_seeds) - set(reports_by_seed))

    groups: dict[str, Any] = {}
    for group in GROUPS:
        per_metric: dict[str, Any] = {}
        for metric in METRICS:
            values = [
                float(report["groups"][group]["metrics"][metric])
                for report in usable.values()
                if group in report["groups"]
            ]
            if values:
                per_metric[metric] = _spread(values)
        groups[group] = per_metric

    paired: dict[str, Any] = {}
    for metric in METRICS:
        deltas = [
            float(report["groups"]["real_syn_filtered"]["metrics"][metric])
            - float(report["groups"]["real_only"]["metrics"][metric])
            for report in usable.values()
            if all(group in report["groups"] for group in GROUPS)
        ]
        if deltas:
            paired[metric] = _spread(deltas)

    return {
        "schema_version": 1,
        "target": target,
        "status": "complete" if usable and not skipped and not absent else "partial",
        "expected_seeds": sorted(expected_seeds),
        "seeds": sorted(usable),
        "seeds_skipped": skipped,
        "seeds_missing_report": absent,
        "evaluation_only": True,
        "groups": groups,
        "paired_filtered_minus_real_only": paired,
        "note": (
            "Deltas are computed within each seed and then averaged, so the "
            "pairing between adapters trained on identical data is preserved. "
            "The probe is evaluation-only and never re-enters training."
        ),
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Robustness across seeds — {summary['target']}",
        "",
        f"- Seeds: {', '.join(str(seed) for seed in summary['seeds']) or 'none'}",
        f"- Status: `{summary['status']}`",
        "- Evaluation-only; the probe never re-enters training.",
        "",
        "## Per-group means",
        "",
        "| Group | Metric | Mean | Sample SD |",
        "|---|---|---:|---:|",
    ]
    for group, metrics in summary["groups"].items():
        for metric, item in metrics.items():
            std = item["sample_std"]
            std_text = "—" if std is None else f"{std:.2%}"
            lines.append(
                f"| `{group}` | `{metric}` | {item['mean']:.2%} | {std_text} |"
            )
    lines += [
        "",
        "## Paired delta (filtered − real_only), computed per seed",
        "",
        "| Metric | Mean Δ | Sample SD |",
        "|---|---:|---:|",
    ]
    for metric, item in summary["paired_filtered_minus_real_only"].items():
        std = item["sample_std"]
        std_text = "—" if std is None else f"{std * 100:.2f}"
        lines.append(f"| `{metric}` | {item['mean'] * 100:+.2f} | {std_text} |")
    lines += ["", summary["note"], ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="gemma")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--markdown-out", type=Path, default=None)
    args = parser.parse_args()

    reports: dict[int, dict[str, Any]] = {}
    missing: list[int] = []
    for seed in args.seeds:
        path = report_path(args.target, seed)
        if path.is_file():
            reports[seed] = json.loads(path.read_text(encoding="utf-8"))
        else:
            missing.append(seed)

    if not reports:
        print(f"No robustness reports found for target {args.target}; nothing to do.")
        return 1

    summary = summarize_robustness_seeds(
        reports, target=args.target, expected_seeds=args.seeds
    )

    json_out = args.json_out or (
        REPO_ROOT / "reports" / f"m16_robustness_summary_{args.target}.json"
    )
    markdown_out = args.markdown_out or (
        REPO_ROOT / "reports" / f"m16_robustness_summary_{args.target}.md"
    )
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_out.write_text(render_markdown(summary), encoding="utf-8")

    print(f"{args.target}: status={summary['status']} seeds={summary['seeds']}")
    if missing:
        print(f"  missing reports for seeds: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
