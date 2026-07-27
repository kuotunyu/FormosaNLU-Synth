from __future__ import annotations

from pathlib import Path

import pytest

from src.synthetic.checkpoint import CheckpointError, JsonlCheckpoint


def test_checkpoint_append_load_and_compact(tmp_path: Path) -> None:
    checkpoint = JsonlCheckpoint(tmp_path / "records.jsonl")
    checkpoint.append({"generation_index": 2, "value": "c"})
    checkpoint.append({"generation_index": 0, "value": "a"})
    assert set(checkpoint.load()) == {0, 2}
    checkpoint.compact()
    lines = checkpoint.path.read_text(encoding="utf-8").splitlines()
    assert '"generation_index":0' in lines[0]
    assert '"generation_index":2' in lines[1]


def test_checkpoint_rejects_duplicate_index(tmp_path: Path) -> None:
    checkpoint = JsonlCheckpoint(tmp_path / "records.jsonl")
    checkpoint.append({"generation_index": 0})
    checkpoint.append({"generation_index": 0})
    with pytest.raises(CheckpointError, match="Duplicate"):
        checkpoint.load()


def test_checkpoint_rejects_malformed_line(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    path.write_text('{"generation_index":0}\nnot-json\n', encoding="utf-8")
    with pytest.raises(CheckpointError, match="line 2"):
        JsonlCheckpoint(path).load()
