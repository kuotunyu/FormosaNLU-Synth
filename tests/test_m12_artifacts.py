from __future__ import annotations

from scripts.build_m12_artifacts import build_resource_ledger
from scripts.verify_readme import expected_main_rows


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

    assert rows == [
        "| `real_only` | 20-shot real | 73.54% | 75.20% | 62.14% | 49.06% | 98.02% |"
    ]
