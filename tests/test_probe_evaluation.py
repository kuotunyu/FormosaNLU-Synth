from __future__ import annotations

import json

import pytest

from scripts.eval_robustness import GROUPS, build_plan
from src.evaluation.run_probe import build_probe_report


def _record(index: int, kind: str) -> dict:
    intent = "alarm_query"
    raw = json.dumps({"intent": intent, "slots": []})
    return {
        "generation_index": index,
        "expected": {
            "id": f"probe-{index}",
            "utt": "查鬧鐘",
            "intent": intent,
            "slots": [],
            "probe_kind": kind,
            "source_test_id": f"source-{index}",
        },
        "raw_prediction": raw,
        "wall_seconds": 0.1,
        "output_tokens": 8,
        "gpu_memory_mib": 10_000,
    }


def test_probe_report_groups_metrics_and_primary_deltas(tmp_path) -> None:
    records = [_record(0, "colloquial"), _record(1, "asr_noise")]
    primary = {
        "metrics": {
            "json_valid_rate": 0.9,
            "intent_accuracy": 0.9,
            "intent_macro_f1": 0.9,
            "slot_micro_f1": 1.0,
            "exact_match": 0.9,
        }
    }
    report = build_probe_report(
        records=records,
        group="real_syn_filtered",
        seed=42,
        adapter_dir=tmp_path,
        primary_report=primary,
    )
    assert report["status"] == "complete"
    assert report["probe_kind_counts"] == {"asr_noise": 1, "colloquial": 1}
    assert report["metrics"]["exact_match"] == 1.0
    assert report["delta_vs_primary_by_probe_kind"]["colloquial"][
        "exact_match"
    ] == pytest.approx(
        0.1
    )


def test_robustness_plan_is_two_primary_seed_adapters() -> None:
    plans = build_plan()
    assert [(plan.group, plan.seed) for plan in plans] == [
        (group, 42) for group in GROUPS
    ]
    assert len({plan.output for plan in plans}) == 2
