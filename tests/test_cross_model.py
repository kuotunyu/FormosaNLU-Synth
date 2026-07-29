from __future__ import annotations

from src.training.cross_model import (
    GROUPS,
    SEEDS,
    build_eval_plan,
    build_run_plan,
    validate_contract,
)


def test_phi_plan_is_two_groups_by_three_seeds() -> None:
    plans = build_run_plan()
    assert [(plan.group, plan.seed) for plan in plans] == [
        (group, seed) for group in GROUPS for seed in SEEDS
    ]
    assert len(plans) == 6
    assert len({plan.output_dir for plan in plans}) == 6
    assert all("runs" in spec.output_dir.parts for spec in plans)
    assert all("m15" in spec.output_dir.parts for spec in plans)


def test_phi_eval_paths_are_isolated_from_gemma_results() -> None:
    plans = build_eval_plan()
    assert len({spec.output for spec in plans}) == 6
    assert all("m15" in spec.output.parts for spec in plans)
    assert all("phi4mini" in spec.output.parts for spec in plans)


def test_phi_contract_reuses_exact_frozen_rows() -> None:
    validation = validate_contract()
    assert validation["status"] == "validated"
    assert validation["seeds"] == [42, 43, 44]
    assert validation["groups"]["real_only"]["seeds"]["42"]["rows"] == 1176
    assert validation["groups"]["real_syn_filtered"]["seeds"]["42"]["rows"] == 4936
