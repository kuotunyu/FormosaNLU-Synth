from __future__ import annotations

from scripts.build_m12_artifacts import build_resource_ledger
from scripts.verify_readme import (
    expected_main_rows,
    expected_replicate_rows,
    expected_robustness_rows,
)


def test_resource_ledger_uses_measured_phase_times() -> None:
    ledger = build_resource_ledger(
        generation={"generation": {"wall_seconds": 3600}},
        training={
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T02:00:00+00:00",
            "runs": [{}, {}],
        },
        evaluation={
            "started_at": "2026-01-01T02:00:00+00:00",
            "finished_at": "2026-01-01T02:30:00+00:00",
            "runs": [{}],
        },
        zero_shot={"wall_seconds": 1800},
    )

    assert ledger["measured_core_gpu_hours"] == 4.0
    assert ledger["gpu_tdp_energy_upper_bound_kwh"] == 1.8
    assert ledger["phases"]["primary_training_seed_42"]["runs"] == 2
    assert ledger["pending"] == [
        "F7 independent judge audit",
        "M11 real demo evidence",
        "real_only and real_syn_filtered training seeds 43 and 44",
        "four 2,974-row replicate evaluations",
        "two 8,922-row robustness probe evaluations",
    ]


def test_resource_ledger_adds_completed_auxiliary_phases() -> None:
    ledger = build_resource_ledger(
        generation={"generation": {"wall_seconds": 3600}},
        training={
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T01:00:00+00:00",
            "runs": [{}, {}],
        },
        evaluation={
            "started_at": "2026-01-01T01:00:00+00:00",
            "finished_at": "2026-01-01T02:00:00+00:00",
            "runs": [{}, {}],
        },
        zero_shot={"wall_seconds": 3600},
        f7={"status": "complete", "wall_seconds_sum": 1800, "samples": 376},
        m11={
            "status": "complete",
            "comparisons": [
                {
                    "base": {"latency_ms": 900_000},
                    "adapted": {"latency_ms": 900_000},
                }
            ],
        },
        replicate_training={
            "status": "complete",
            "started_at": "2026-01-01T02:00:00+00:00",
            "finished_at": "2026-01-01T03:00:00+00:00",
            "runs": [{}, {}, {}, {}],
        },
        replicate_evaluation={
            "status": "complete",
            "started_at": "2026-01-01T03:00:00+00:00",
            "finished_at": "2026-01-01T04:00:00+00:00",
            "runs": [{}, {}, {}, {}],
        },
        robustness={
            "status": "complete",
            "started_at": "2026-01-01T04:00:00+00:00",
            "finished_at": "2026-01-01T05:00:00+00:00",
            "runs": [{}, {}],
        },
    )
    assert ledger["status"] == "complete_all_local_gpu"
    assert ledger["pending"] == []
    assert ledger["measured_core_gpu_hours"] == 4.0
    assert ledger["measured_auxiliary_gpu_hours"] == 4.0
    assert ledger["measured_total_local_gpu_hours"] == 8.0
    assert ledger["gpu_tdp_total_energy_upper_bound_kwh"] == 3.6


def test_expected_readme_row_is_formatted_from_metrics() -> None:
    rows = expected_main_rows(
        {
            "rows": [
                {
                    "group": "real_only",
                    "metrics": {
                        "intent_accuracy": 0.735373,
                        "intent_macro_f1": 0.751977,
                        "slot_micro_f1": 0.621404,
                        "exact_match": 0.490585,
                        "json_valid_rate": 0.980161,
                    },
                }
            ]
        }
    )

    assert rows == ["| `real_only` | 20-shot real | 73.54% | 75.20% | 62.14% | 49.06% | 98.02% |"]


def test_expected_replicate_row_is_formatted_from_summary() -> None:
    metric = {
        "mean": 0.5,
        "sample_std": 0.01,
        "ci95_low": 0.47,
        "ci95_high": 0.53,
    }
    summary = {
        "metrics": {
            group: {
                name: metric
                for name in (
                    "intent_accuracy",
                    "intent_macro_f1",
                    "slot_micro_f1",
                    "exact_match",
                    "json_valid_rate",
                )
            }
            for group in ("real_only", "real_syn_filtered")
        },
        "paired_filtered_minus_real_only": {
            name: {
                "mean": 0.04,
                "sample_std": 0.02,
                "ci95_low": 0.01,
                "ci95_high": 0.07,
            }
            for name in (
                "intent_accuracy",
                "intent_macro_f1",
                "slot_micro_f1",
                "exact_match",
                "json_valid_rate",
            )
        },
    }

    assert expected_replicate_rows(summary)[0] == (
        "| Intent accuracy | 50.00% ± 1.00% | 50.00% ± 1.00% | +4.00% ± 2.00% | [+1.00%, +7.00%] |"
    )


def test_expected_robustness_row_is_formatted_from_report() -> None:
    metrics = {
        "intent_accuracy": 0.75,
        "slot_micro_f1": 0.5,
        "exact_match": 0.4,
        "json_valid_rate": 0.95,
    }
    report = {
        "groups": {
            group: {
                "metrics_by_probe_kind": {
                    kind: metrics for kind in ("asr_noise", "colloquial", "lexical")
                }
            }
            for group in ("real_only", "real_syn_filtered")
        }
    }

    assert expected_robustness_rows(report)[0] == (
        "| `real_only` | `asr_noise` | 75.00% | 50.00% | 40.00% | 95.00% |"
    )
