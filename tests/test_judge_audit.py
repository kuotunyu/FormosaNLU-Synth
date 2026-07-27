import pytest

from src.filtering.judge_audit import boundary_margin, select_full_audit


def _record(index: int, *, recipe: str = "paraphrase", margin: float = 0.1) -> dict:
    return {
        "generation_index": index,
        "expected": {"intent": "alarm_set", "slots": []},
        "sample": {
            "id": f"syn-{index}",
            "intent": "alarm_set",
            "slots": [],
            "style": "massive_like",
            "provenance": {
                "recipe": recipe,
                "filter_score": {
                    "f5_max_prior_synthetic": 0.999 - margin,
                    "f5_max_seed": 0.8,
                    "f6_max_eval": 0.7,
                },
            },
        },
    }


def test_full_audit_includes_all_hard_then_conflict_and_random() -> None:
    records = [
        _record(index, recipe="hard_negative" if index < 8 else "paraphrase")
        for index in range(100)
    ]
    records[9]["sample"]["provenance"]["filter_score"]["f5_max_prior_synthetic"] = 0.9989
    selected = select_full_audit(records, fraction=0.10, seed=42)
    assert len(selected) == 10
    assert sum(row["f7_selection"]["stratum"] == "hard_negative" for row in selected) == 8
    assert sum(row["f7_selection"]["stratum"] == "boundary_conflict" for row in selected) == 1
    assert sum(row["f7_selection"]["stratum"] == "random" for row in selected) == 1
    assert {f"syn-{index}" for index in range(8)}.issubset(
        {row["sample"]["id"] for row in selected}
    )
    assert "syn-9" in {row["sample"]["id"] for row in selected}


def test_boundary_margin_uses_nearest_frozen_threshold() -> None:
    record = _record(1, margin=0.0005)
    assert boundary_margin(record) == pytest.approx(0.0005)
