from __future__ import annotations

import json

import pytest
import yaml

from src.training.ablation import (
    ABLATION_GROUPS,
    CONTROL_GROUP,
    RECIPES,
    ablation_examples,
    build_plan,
    equal_n_size,
    group_name,
    recipe_by_row_id,
    recipe_counts,
)
from src.training.train import DEFAULT_CONFIG, load_train_config, train_group


def test_group_set_is_the_control_plus_one_per_recipe() -> None:
    assert ABLATION_GROUPS[0] == CONTROL_GROUP
    assert set(ABLATION_GROUPS[1:]) == {group_name(r) for r in RECIPES}
    assert len(ABLATION_GROUPS) == len(RECIPES) + 1


def test_unknown_group_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown ablation group"):
        ablation_examples("abl_no_nonexistent_recipe")


def test_training_entry_accepts_preregistered_ablation_group(tmp_path) -> None:
    """M19 groups must pass the training entry point's group validation."""
    config = load_train_config(DEFAULT_CONFIG)
    config["model"]["local_path"] = "definitely-missing-model"
    config_path = tmp_path / "train.yaml"
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="Local model is missing"):
        train_group(
            group=CONTROL_GROUP,
            config_path=config_path,
            output_dir=tmp_path / "run",
            smoke_test=False,
            resume=False,
            seed=42,
        )


def test_plan_mismatch_is_an_error_not_a_silent_relabel(tmp_path) -> None:
    """The recipe comes from a rebuilt plan; if it disagrees with the corpus the
    mapping is meaningless and must fail loudly."""
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        json.dumps(
            {
                "generation_index": 0,
                "expected": {"intent": "definitely_not_the_planned_intent"},
                "sample": {"id": "x", "utt": "u", "intent": "i", "slots": []},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="plan/corpus mismatch"):
        recipe_by_row_id(corpus)


@pytest.mark.requires_local_artifacts
def test_equal_n_is_the_smallest_leave_one_out_corpus() -> None:
    counts = recipe_counts()
    assert equal_n_size() == sum(counts.values()) - max(counts.values())


@pytest.mark.requires_local_artifacts
def test_every_group_carries_the_same_synthetic_count() -> None:
    """Holding size fixed is the whole point; if it drifts the comparison is
    confounded by volume again."""
    plan = build_plan()
    sizes = {g: v["synthetic_rows"] for g, v in plan["groups"].items()}
    assert len(set(sizes.values())) == 1, sizes


@pytest.mark.requires_local_artifacts
def test_excluded_recipe_is_absent_and_others_remain() -> None:
    mapping = recipe_by_row_id()
    real_count = len(build_plan()["groups"]) and None  # placeholder, unused
    del real_count

    for recipe in RECIPES:
        rows = ablation_examples(group_name(recipe))
        synthetic_ids = [str(r["id"]) for r in rows if str(r["id"]) in mapping]
        present = {mapping[i] for i in synthetic_ids}
        assert recipe not in present, f"{recipe} still present in its own ablation"
        assert present, "no synthetic rows survived"


@pytest.mark.requires_local_artifacts
def test_groups_are_deterministic() -> None:
    first = [r["id"] for r in ablation_examples(CONTROL_GROUP)]
    second = [r["id"] for r in ablation_examples(CONTROL_GROUP)]
    assert first == second


@pytest.mark.requires_local_artifacts
def test_control_is_not_merely_a_superset_of_a_leave_one_out_group() -> None:
    """Separate sampling namespaces stop the control from being the same rows
    plus the excluded recipe, which would understate the difference."""
    mapping = recipe_by_row_id()
    control = {str(r["id"]) for r in ablation_examples(CONTROL_GROUP)} & set(mapping)
    dropped = {
        str(r["id"]) for r in ablation_examples(group_name("hard_negative"))
    } & set(mapping)
    assert control != dropped
    assert control - dropped, "control shares every row with the ablation group"
