from __future__ import annotations

from scripts.judge_pilot import select_audit_records


def _record(index: int, recipe: str) -> dict:
    return {
        "generation_index": index,
        "sample": {
            "id": f"syn_{index:020x}",
            "provenance": {"recipe": recipe},
        },
    }


def test_judge_selection_is_deterministic_unique_and_hard_weighted() -> None:
    records = [
        *(_record(index, "hard_negative") for index in range(40)),
        *(_record(index, "paraphrase") for index in range(40, 100)),
        *(_record(index, "slot_substitution") for index in range(100, 150)),
        *(_record(index, "noise_codeswitch") for index in range(150, 200)),
    ]
    selected_a = select_audit_records(records)
    selected_b = select_audit_records(records)
    ids_a = [record["sample"]["id"] for record in selected_a]
    assert ids_a == [record["sample"]["id"] for record in selected_b]
    assert len(ids_a) == len(set(ids_a)) == 50
    hard_count = sum(
        record["sample"]["provenance"]["recipe"] == "hard_negative" for record in selected_a
    )
    assert hard_count >= 25
