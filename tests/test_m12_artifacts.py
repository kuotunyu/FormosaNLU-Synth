from __future__ import annotations

from scripts.build_m12_artifacts import build_resource_ledger
from scripts.verify_readme import (
    expected_ablation_rows,
    expected_main_rows,
    expected_paired_markers,
    expected_publication_markers,
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
        "M15 Phi-4-mini training runs",
        "M15 Phi-4-mini evaluations",
        "M19 equal-N per-recipe ablation",
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
        m15_training={
            "status": "complete",
            "runs": [
                {
                    "started_at": "2026-01-01T05:00:00+00:00",
                    "finished_at": "2026-01-01T05:30:00+00:00",
                },
                {
                    "started_at": "2026-01-01T05:30:00+00:00",
                    "finished_at": "2026-01-01T06:00:00+00:00",
                },
            ],
        },
        m15_evaluation={
            "status": "complete",
            "started_at": "2026-01-01T06:00:00+00:00",
            "finished_at": "2026-01-01T07:00:00+00:00",
            "runs": [{}, {}],
        },
        m19_batch={"status": "complete", "runs": [{"status": "completed"}] * 5},
        m19_training_reports=[
            {"status": "completed", "metrics": {"train_runtime": 360.0}}
            for _ in range(5)
        ],
        m19_evaluation_reports=[
            {
                "evaluation_mode": "trained_adapter",
                "completed": 2_974,
                "target": 2_974,
                "wall_seconds": 360.0,
            }
            for _ in range(5)
        ],
    )
    assert ledger["status"] == "complete_all_local_gpu"
    assert ledger["pending"] == []
    # The second student family is auxiliary, so the frozen primary core must
    # not move when M15 is folded in.
    assert ledger["measured_core_gpu_hours"] == 4.0
    assert ledger["measured_auxiliary_gpu_hours"] == 7.0
    assert ledger["measured_total_local_gpu_hours"] == 11.0
    assert ledger["gpu_tdp_total_energy_upper_bound_kwh"] == 4.95


def test_resource_ledger_uses_measured_m19_training_and_evaluation_times() -> None:
    ledger = build_resource_ledger(
        generation={"generation": {"wall_seconds": 0}},
        training={
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:00+00:00",
            "runs": [{}],
        },
        evaluation={
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:00+00:00",
            "runs": [{}],
        },
        zero_shot={"wall_seconds": 0},
        m19_batch={"status": "complete", "runs": [{"status": "completed"}] * 5},
        m19_training_reports=[
            {"status": "completed", "metrics": {"train_runtime": 360.0}}
            for _ in range(5)
        ],
        m19_evaluation_reports=[
            {
                "evaluation_mode": "trained_adapter",
                "completed": 2_974,
                "target": 2_974,
                "wall_seconds": 360.0,
            }
            for _ in range(5)
        ],
    )

    phase = ledger["phases"]["m19_equal_n_recipe_ablation"]
    assert phase["wall_hours"] == 1.0
    assert phase["training_runs"] == 5
    assert phase["evaluation_rows"] == 14_870
    assert phase["basis"].startswith("summed runs/m19/*/seed_42/run_report.json")


def test_robustness_backfill_sums_batches_rather_than_spanning_them() -> None:
    """The backfill batches ran at different times with gaps between them, so
    bounding them with one window would bill the idle time in between."""
    ledger = build_resource_ledger(
        generation={"generation": {"wall_seconds": 0}},
        training={
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:00+00:00",
            "runs": [{}],
        },
        evaluation={
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:00+00:00",
            "runs": [{}],
        },
        zero_shot={"wall_seconds": 0},
        robustness_backfill=[
            {
                "status": "complete",
                "started_at": "2026-01-01T01:00:00+00:00",
                "finished_at": "2026-01-01T02:00:00+00:00",
                "runs": [{}, {}],
            },
            {
                "status": "complete",
                "started_at": "2026-01-01T09:00:00+00:00",
                "finished_at": "2026-01-01T10:00:00+00:00",
                "runs": [{}, {}],
            },
        ],
    )

    phase = ledger["phases"]["m16_robustness_backfill"]
    assert phase["wall_hours"] == 2.0  # not the 9 hours a single window spans
    assert phase["batches"] == 2
    assert phase["runs"] == 4


def test_incomplete_backfill_batches_are_excluded_and_flagged() -> None:
    ledger = build_resource_ledger(
        generation={"generation": {"wall_seconds": 0}},
        training={
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:00+00:00",
            "runs": [{}],
        },
        evaluation={
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:00+00:00",
            "runs": [{}],
        },
        zero_shot={"wall_seconds": 0},
        robustness_backfill=[
            {
                "status": "complete",
                "started_at": "2026-01-01T01:00:00+00:00",
                "finished_at": "2026-01-01T02:00:00+00:00",
                "runs": [{}],
            },
            {"status": "running", "runs": [{}]},
        ],
    )

    assert ledger["phases"]["m16_robustness_backfill"]["batches"] == 1
    assert "M16 robustness backfill batches" in ledger["pending"]


def test_m15_training_window_spans_unordered_runs() -> None:
    """The M15 training batch stamps each run, not the batch, so the window is
    bounded by the earliest start and the latest finish regardless of order."""
    ledger = build_resource_ledger(
        generation={"generation": {"wall_seconds": 0}},
        training={
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:00+00:00",
            "runs": [{}],
        },
        evaluation={
            "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:00:00+00:00",
            "runs": [{}],
        },
        zero_shot={"wall_seconds": 0},
        m15_training={
            "status": "complete",
            "runs": [
                {
                    "started_at": "2026-01-01T03:00:00+00:00",
                    "finished_at": "2026-01-01T04:00:00+00:00",
                },
                {
                    "started_at": "2026-01-01T01:00:00+00:00",
                    "finished_at": "2026-01-01T02:00:00+00:00",
                },
            ],
        },
    )

    assert ledger["phases"]["m15_phi4mini_training"]["wall_hours"] == 3.0
    assert ledger["phases"]["m15_phi4mini_training"]["runs"] == 2


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


def test_expected_ablation_row_is_formatted_from_report() -> None:
    report = {
        "groups": [
            {
                "group": "abl_no_paraphrase",
                "excluded_recipe": "paraphrase",
                "metrics": {
                    "intent_accuracy": 0.75,
                    "intent_macro_f1": 0.74,
                    "slot_micro_f1": 0.63,
                    "exact_match": 0.47,
                    "json_valid_rate": 0.97,
                },
                "delta_vs_control_percentage_points": {"exact_match": -3.0},
                "detectable_on_exact_match": True,
            }
        ]
    }

    assert expected_ablation_rows(report) == [
        "| `abl_no_paraphrase` | `paraphrase` | 75.00% | 74.00% | "
        "63.00% | 47.00% | -3.00 | 97.00% | yes |"
    ]


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


def test_expected_publication_markers_are_derived_from_report() -> None:
    report = {
        "github": {"url": "https://github.com/example/project"},
        "dataset": {
            "url": "https://huggingface.co/datasets/example/data",
            "rows": 3754,
        },
        "model": {"url": "https://huggingface.co/example/model"},
    }

    assert expected_publication_markers(report) == [
        "https://github.com/example/project",
        "https://huggingface.co/datasets/example/data",
        "https://huggingface.co/example/model",
        "3,754-row",
    ]


def test_expected_paired_markers_are_derived_from_report() -> None:
    report = {
        "hierarchical_bootstrap": {
            "repetitions": 5000,
            "metrics": {
                "intent_accuracy": {
                    "mean_delta_percentage_points": 4.14,
                    "hierarchical_bootstrap_95_ci_percentage_points": [2.60, 5.59],
                },
                "exact_match": {
                    "mean_delta_percentage_points": 3.86,
                    "hierarchical_bootstrap_95_ci_percentage_points": [2.75, 4.92],
                },
            },
        }
    }

    assert expected_paired_markers(report) == [
        "5,000 次",
        "hierarchical paired",
        "+4.14",
        "[+2.60, +5.59]",
        "+3.86",
        "[+2.75, +4.92]",
    ]
