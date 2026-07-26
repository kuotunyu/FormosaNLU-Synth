from __future__ import annotations

import json
from pathlib import Path

from scripts.summarize_pilot import summarize


def test_pilot_summary_recomputes_counts_and_projection(tmp_path: Path) -> None:
    records = []
    for index in range(2):
        records.append(
            {
                "generation_index": index,
                "generation_contract_reason": None,
                "sample": {
                    "id": f"syn_{index:020x}",
                    "style": "massive_like",
                    "provenance": {"recipe": "paraphrase"},
                },
            }
        )
    input_path = tmp_path / "pilot.jsonl"
    input_path.write_text(
        "".join(json.dumps(row) + "\n" for row in records),
        encoding="utf-8",
    )
    relative = input_path.resolve()
    cost_path = tmp_path / "cost.json"
    cost_path.write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "output": str(relative),
                        "complete_records": 2,
                        "wall_seconds": 4.0,
                        "prompt_tokens": 10,
                        "output_tokens": 20,
                        "api_cost_usd": 0.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    payload = summarize(input_path, cost_path)
    assert payload["records"] == 2
    assert payload["seconds_per_record"] == 2.0
    assert payload["max_records_under_five_hours"] == 9000
