from __future__ import annotations

from collections import Counter

import pytest

from src.synthetic.planning import build_generation_plans


@pytest.mark.requires_local_artifacts
def test_pilot_plan_has_exact_recipe_mix_and_is_deterministic() -> None:
    plans_a = build_generation_plans(500)
    plans_b = build_generation_plans(500)
    counts = Counter(plan.recipe for plan in plans_a)
    assert counts == {
        "paraphrase": 175,
        "slot_substitution": 150,
        "noise_codeswitch": 100,
        "hard_negative": 75,
    }
    signature_a = [
        (plan.recipe, plan.prompt_version, plan.style, plan.seed_sample_id) for plan in plans_a
    ]
    signature_b = [
        (plan.recipe, plan.prompt_version, plan.style, plan.seed_sample_id) for plan in plans_b
    ]
    assert signature_a == signature_b


@pytest.mark.requires_local_artifacts
def test_noise_plans_are_colloquial_and_hard_negatives_have_pairs() -> None:
    plans = build_generation_plans(100)
    for plan in plans:
        if plan.recipe == "noise_codeswitch":
            assert plan.style == "tw_colloquial"
        if plan.recipe == "hard_negative":
            assert isinstance(plan.seed_sample_id, list)
            assert len(plan.seed_sample_id) == 2
            assert plan.pair_id is not None
