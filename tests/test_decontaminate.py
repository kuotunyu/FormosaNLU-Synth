from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.filtering.decontaminate import write_exclusion_log


def test_decontamination_log_is_auditable(tmp_path: Path) -> None:
    output = tmp_path / "excluded.jsonl"
    write_exclusion_log(
        [
            {
                "sample_id": "syn_1",
                "similarity": 0.98,
                "matched_eval_id": "test_42",
                "split": "test",
            }
        ],
        output,
    )
    row = json.loads(output.read_text(encoding="utf-8"))
    assert row["sample_id"] == "syn_1"
    assert row["matched_eval_id"] == "test_42"


def test_decontamination_log_rejects_unknown_split(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write_exclusion_log(
            [
                {
                    "sample_id": "syn_1",
                    "similarity": 0.98,
                    "matched_eval_id": "train_42",
                    "split": "train",
                }
            ],
            tmp_path / "excluded.jsonl",
        )

