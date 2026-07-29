"""Compare preregistered Gemma and Phi paired effects without pooling families."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.paired_statistics import METRICS
from src.training.train import REPO_ROOT

PRIMARY_METRICS = ("intent_accuracy", "exact_match")
DEFAULT_GEMMA = REPO_ROOT / "reports" / "m14_paired_statistics.json"
DEFAULT_PHI = REPO_ROOT / "reports" / "m15_phi4mini_paired_statistics.json"
DEFAULT_JSON = REPO_ROOT / "reports" / "m15_cross_model_replication.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports" / "m15_cross_model_replication.md"


def _metric_row(report: dict[str, Any], metric: str) -> dict[str, Any]:
    return report["hierarchical_bootstrap"]["metrics"][metric]


def build_cross_model_report(
    gemma: dict[str, Any],
    phi: dict[str, Any],
) -> dict[str, Any]:
    if gemma.get("status") != "complete" or phi.get("status") != "complete":
        raise ValueError("Both paired reports must be complete")
    if gemma["test_rows_per_seed"] != phi["test_rows_per_seed"]:
        raise ValueError("Cross-model reports use different Test row counts")
    if gemma["seeds"] != phi["seeds"]:
        raise ValueError("Cross-model reports use different training seeds")

    rows: dict[str, Any] = {}
    for metric in METRICS:
        gemma_row = _metric_row(gemma, metric)
        phi_row = _metric_row(phi, metric)
        gemma_mean = float(gemma_row["mean_delta_percentage_points"])
        phi_mean = float(phi_row["mean_delta_percentage_points"])
        gemma_ci = gemma_row["hierarchical_bootstrap_95_ci_percentage_points"]
        phi_ci = phi_row["hierarchical_bootstrap_95_ci_percentage_points"]
        rows[metric] = {
            "gemma": {"mean_delta_percentage_points": gemma_mean, "ci": gemma_ci},
            "phi": {"mean_delta_percentage_points": phi_mean, "ci": phi_ci},
            "direction_consistent": gemma_mean > 0 and phi_mean > 0,
            "both_ci_exclude_zero_positive": gemma_ci[0] > 0 and phi_ci[0] > 0,
        }

    primary_pass = all(
        rows[metric]["direction_consistent"]
        and rows[metric]["both_ci_exclude_zero_positive"]
        for metric in PRIMARY_METRICS
    )
    return {
        "schema_version": 1,
        "status": "complete",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "comparison": "real_syn_filtered minus real_only",
        "models": {
            "gemma": "google/gemma-4-E4B-it",
            "phi": "microsoft/Phi-4-mini-instruct",
        },
        "seeds": gemma["seeds"],
        "test_rows_per_seed": gemma["test_rows_per_seed"],
        "preregistered_replication_criterion": {
            "primary_metrics": list(PRIMARY_METRICS),
            "rule": (
                "For both intent_accuracy and exact_match, the paired mean delta "
                "must be positive in each family and each hierarchical 95% CI lower "
                "bound must exceed zero."
            ),
            "passed": primary_pass,
        },
        "metrics": rows,
        "conclusion": (
            "replicated_across_student_families"
            if primary_pass
            else "not_replicated_under_preregistered_criterion"
        ),
        "scope": (
            "This is a two-family replication on one frozen dataset and training "
            "contract. Model families are summarized separately and are not pooled."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# M15 Cross-model Replication",
        "",
        f"Conclusion: **{payload['conclusion']}**",
        "",
        "| Metric | Gemma Δ [95% CI] | Phi Δ [95% CI] | Same positive direction | "
        "Both CIs > 0 |",
        "|---|---:|---:|:---:|:---:|",
    ]
    for metric in METRICS:
        row = payload["metrics"][metric]
        gemma = row["gemma"]
        phi = row["phi"]
        lines.append(
            f"| `{metric}` | {gemma['mean_delta_percentage_points']:+.2f} "
            f"[{gemma['ci'][0]:+.2f}, {gemma['ci'][1]:+.2f}] | "
            f"{phi['mean_delta_percentage_points']:+.2f} "
            f"[{phi['ci'][0]:+.2f}, {phi['ci'][1]:+.2f}] | "
            f"{'✅' if row['direction_consistent'] else '❌'} | "
            f"{'✅' if row['both_ci_exclude_zero_positive'] else '❌'} |"
        )
    lines.extend(
        [
            "",
            "## Preregistered criterion",
            "",
            payload["preregistered_replication_criterion"]["rule"],
            "",
            "## Scope",
            "",
            payload["scope"],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemma", type=Path, default=DEFAULT_GEMMA)
    parser.add_argument("--phi", type=Path, default=DEFAULT_PHI)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    payload = build_cross_model_report(
        json.loads(args.gemma.read_text(encoding="utf-8")),
        json.loads(args.phi.read_text(encoding="utf-8")),
    )
    args.json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.markdown.write_text(
        render_markdown(payload),
        encoding="utf-8",
        newline="\n",
    )
    print(payload["conclusion"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
