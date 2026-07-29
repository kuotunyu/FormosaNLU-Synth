from __future__ import annotations

from scripts.m15_cross_model_report import (
    PRIMARY_METRICS,
    build_cross_model_report,
)
from scripts.paired_statistics import METRICS


def _report(lower: float, mean: float = 2.0) -> dict:
    return {
        "status": "complete",
        "test_rows_per_seed": 2974,
        "seeds": [42, 43, 44],
        "hierarchical_bootstrap": {
            "metrics": {
                metric: {
                    "mean_delta_percentage_points": mean,
                    "hierarchical_bootstrap_95_ci_percentage_points": [
                        lower,
                        3.0,
                    ],
                }
                for metric in METRICS
            }
        },
    }


def test_cross_model_claim_requires_both_primary_cis_above_zero() -> None:
    assert PRIMARY_METRICS == ("intent_accuracy", "exact_match")
    passed = build_cross_model_report(_report(0.1), _report(0.2))
    assert passed["conclusion"] == "replicated_across_student_families"

    phi = _report(0.2)
    phi["hierarchical_bootstrap"]["metrics"]["exact_match"][
        "hierarchical_bootstrap_95_ci_percentage_points"
    ][0] = -0.1
    failed = build_cross_model_report(_report(0.1), phi)
    assert failed["conclusion"] == "not_replicated_under_preregistered_criterion"
