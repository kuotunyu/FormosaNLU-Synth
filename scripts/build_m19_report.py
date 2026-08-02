"""Aggregate the five preregistered M19 evaluation reports.

The experiment contract lives in ``docs/M19_ABLATION_PROTOCOL.md``.  This
module only validates completed artifacts, computes leave-one-recipe-out
deltas against the equal-N control, and renders tracked reports; it does not
train, evaluate, or change the preregistered decision rule.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from src.training.ablation import ABLATION_GROUPS, build_plan
from src.training.train import REPO_ROOT

SEED = 42
TARGET_ROWS = 2_974
CONTROL_GROUP = "abl_all_eqn"
DETECTABILITY_THRESHOLD_PERCENTAGE_POINTS = 2.5
METRICS = (
    "intent_accuracy",
    "intent_macro_f1",
    "slot_micro_f1",
    "exact_match",
    "json_valid_rate",
)
REPORT_DIR = REPO_ROOT / "reports" / "m19"
OUTPUT_JSON = REPO_ROOT / "reports" / "m19_ablation.json"
OUTPUT_MARKDOWN = REPO_ROOT / "reports" / "m19_ablation.md"


def _validated_by_group(
    evaluations: Iterable[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_group: dict[str, dict[str, Any]] = {}
    for payload in evaluations:
        group = payload.get("group")
        if (
            group not in ABLATION_GROUPS
            or payload.get("evaluation_mode") != "trained_adapter"
            or payload.get("seed") != SEED
            or payload.get("completed") != TARGET_ROWS
            or payload.get("target") != TARGET_ROWS
            or not all(metric in payload.get("metrics", {}) for metric in METRICS)
        ):
            raise ValueError(
                "M19 aggregation requires one complete 2,974-row "
                "trained-adapter evaluation per preregistered group"
            )
        if group in by_group:
            raise ValueError(f"Duplicate M19 evaluation group: {group}")
        by_group[group] = payload
    if set(by_group) != set(ABLATION_GROUPS):
        missing = sorted(set(ABLATION_GROUPS) - set(by_group))
        raise ValueError(
            "M19 aggregation requires one complete 2,974-row "
            f"trained-adapter evaluation per preregistered group; missing={missing}"
        )
    return by_group


def build_report(evaluations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Build the frozen single-seed, equal-N leave-one-recipe-out summary."""
    by_group = _validated_by_group(evaluations)
    plan = build_plan(seed=SEED)
    control_metrics = by_group[CONTROL_GROUP]["metrics"]
    groups: list[dict[str, Any]] = []
    detectable: list[str] = []

    for group in ABLATION_GROUPS:
        payload = by_group[group]
        metrics = {metric: float(payload["metrics"][metric]) for metric in METRICS}
        deltas = {
            metric: (metrics[metric] - float(control_metrics[metric])) * 100
            for metric in METRICS
        }
        detectable_on_exact_match = (
            group != CONTROL_GROUP
            and abs(deltas["exact_match"])
            >= DETECTABILITY_THRESHOLD_PERCENTAGE_POINTS
        )
        if detectable_on_exact_match:
            detectable.append(group)
        groups.append(
            {
                "group": group,
                "excluded_recipe": plan["groups"][group]["excluded_recipe"],
                "synthetic_rows": plan["groups"][group]["synthetic_rows"],
                "metrics": metrics,
                "delta_vs_control_percentage_points": deltas,
                "detectable_on_exact_match": detectable_on_exact_match,
            }
        )

    return {
        "schema_version": 1,
        "status": "complete",
        "seed": SEED,
        "sample_size_note": "single seed (n=1); descriptive comparison only",
        "control_group": CONTROL_GROUP,
        "equal_n_synthetic_rows": plan["equal_n"],
        "evaluation_rows_per_group": TARGET_ROWS,
        "detectability_metric": "exact_match",
        "detectability_threshold_percentage_points": (
            DETECTABILITY_THRESHOLD_PERCENTAGE_POINTS
        ),
        "groups": groups,
        "detectable_groups_on_exact_match": detectable,
        "interpretation": (
            "one_or_more_differences_reach_preregistered_detectability_threshold"
            if detectable
            else "no_difference_reaches_preregistered_detectability_threshold"
        ),
        "causal_claim_allowed": False,
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render the tracked human-readable summary from the JSON report."""
    lines = [
        "# M19 Equal-N Per-recipe Ablation",
        "",
        "Status: **complete**.",
        "",
        (
            "所有組別固定 2,246 筆 synthetic rows、相同 prompt／train config／"
            "500 steps，並在同一份 2,974-row Test 上評估。結果僅為 seed 42（n=1）"
            "的描述性比較。"
        ),
        "",
        (
            "預先登記的可偵測門檻為 exact match 絕對差異 "
            f"{report['detectability_threshold_percentage_points']:.1f} percentage points；"
            "低於門檻代表本設計無法分辨，不等於效果為零。單一 seed 結果不支持 "
            "recipe-level causal claim。"
        ),
        "",
        (
            "| Group | Excluded recipe | Intent acc | Macro-F1 | Slot F1 | "
            "Exact | Δ Exact vs control (pp) | JSON-valid | Detectable |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for row in report["groups"]:
        metrics = row["metrics"]
        excluded = row["excluded_recipe"] or "— (equal-N control)"
        mark = "yes" if row["detectable_on_exact_match"] else "no"
        lines.append(
            f"| `{row['group']}` | `{excluded}` | "
            f"{metrics['intent_accuracy']:.2%} | "
            f"{metrics['intent_macro_f1']:.2%} | "
            f"{metrics['slot_micro_f1']:.2%} | "
            f"{metrics['exact_match']:.2%} | "
            f"{row['delta_vs_control_percentage_points']['exact_match']:+.2f} | "
            f"{metrics['json_valid_rate']:.2%} | {mark} |"
        )
    lines.extend(
        [
            "",
            "Machine-readable source: `reports/m19_ablation.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_evaluations(report_dir: Path) -> list[dict[str, Any]]:
    return [
        json.loads((report_dir / f"{group}_seed_{SEED}.json").read_text(encoding="utf-8"))
        for group in ABLATION_GROUPS
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--output-json", type=Path, default=OUTPUT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=OUTPUT_MARKDOWN)
    args = parser.parse_args()

    report = build_report(_load_evaluations(args.report_dir))
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_markdown.write_text(render_markdown(report), encoding="utf-8")
    print(
        "M19 report complete; detectable exact-match groups="
        f"{len(report['detectable_groups_on_exact_match'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
