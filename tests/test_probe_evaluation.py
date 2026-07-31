from __future__ import annotations

import json

import pytest

from scripts.eval_robustness import (
    CONFIRMATION,
    DEFAULT_BATCH_REPORT,
    DEFAULT_COMBINED_REPORT,
    GEMMA_TARGET,
    GROUPS,
    PHI4MINI_TARGET,
    build_plan,
    confirmation_token,
    default_batch_report,
    default_combined_report,
)
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


def test_default_plan_still_targets_the_original_gemma_paths() -> None:
    """The M10 seed-42 batch must stay byte-identical after parameterization."""
    plan = {spec.group: spec for spec in build_plan()}["real_only"]
    assert plan.adapter_dir.parts[-4:] == ("runs", "real_only", "seed_42", "adapter")
    assert plan.primary_report.parts[-3:] == ("reports", "m9", "real_only_seed_42.json")
    assert plan.output.parts[-3:] == (
        "results",
        "robustness",
        "real_only_seed_42.jsonl",
    )
    assert default_batch_report(GEMMA_TARGET, 42) == DEFAULT_BATCH_REPORT
    assert default_combined_report(GEMMA_TARGET, 42) == DEFAULT_COMBINED_REPORT
    assert confirmation_token(GEMMA_TARGET, 42) == CONFIRMATION


def test_other_seeds_get_their_own_paths_and_token() -> None:
    plans = build_plan(seed=43)
    assert [spec.seed for spec in plans] == [43, 43]
    for spec in plans:
        assert spec.output.name.endswith("_seed_43.jsonl")
        assert spec.adapter_dir.parts[-2] == "seed_43"
    # A distinct token stops a seed-43 batch from running on the seed-42 phrase.
    assert confirmation_token(GEMMA_TARGET, 43) != CONFIRMATION
    assert default_batch_report(GEMMA_TARGET, 43) != DEFAULT_BATCH_REPORT
    assert default_combined_report(GEMMA_TARGET, 43) != DEFAULT_COMBINED_REPORT


def test_phi4mini_target_uses_the_m15_layout_and_config() -> None:
    plans = build_plan(target=PHI4MINI_TARGET, seed=42)
    assert [spec.group for spec in plans] == list(GROUPS)
    for spec in plans:
        assert spec.adapter_dir.parts[-5:-3] == ("m15", "phi4mini")
        assert spec.primary_report.parts[-4:-1] == ("reports", "m15", "phi4mini")
        assert spec.output.parts[-2] == "robustness_phi4mini"
    assert PHI4MINI_TARGET.config.name == "train_phi4mini.yaml"
    assert confirmation_token(PHI4MINI_TARGET, 42) != CONFIRMATION


def test_targets_never_share_an_output_path() -> None:
    """Gemma and Phi results must not overwrite each other."""
    outputs = set()
    for target in (GEMMA_TARGET, PHI4MINI_TARGET):
        for seed in (42, 43, 44):
            for spec in build_plan(target=target, seed=seed):
                outputs.add(spec.output)
                outputs.add(spec.report_json)
    assert len(outputs) == 2 * 3 * 2 * 2
