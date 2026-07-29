from __future__ import annotations

import pytest

from src.training import replicates


def test_replicate_plan_is_exactly_two_groups_by_two_seeds() -> None:
    plans = replicates.build_replicate_run_plan()
    assert [(plan.group, plan.seed) for plan in plans] == [
        ("real_only", 43),
        ("real_only", 44),
        ("real_syn_filtered", 43),
        ("real_syn_filtered", 44),
    ]
    assert len({plan.output_dir for plan in plans}) == 4


def test_replicate_eval_paths_do_not_overlap_primary_or_each_other() -> None:
    plans = replicates.build_replicate_eval_plan()
    assert len({plan.output for plan in plans}) == 4
    assert len({plan.report_json for plan in plans}) == 4
    assert all("seed_42" not in str(plan.output) for plan in plans)


@pytest.mark.requires_local_artifacts
def test_replicate_inputs_change_random_seed_not_training_rows() -> None:
    validation = replicates.validate_replicate_inputs()
    assert validation["status"] == "validated"
    for group in validation["groups"].values():
        assert set(group["replicates"]) == {"43", "44"}
        assert all(
            replicate["sha256"] == group["sha256"]
            for replicate in group["replicates"].values()
        )
