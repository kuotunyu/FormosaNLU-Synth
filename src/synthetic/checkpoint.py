"""Append-only JSONL checkpoint with deterministic plan-drift detection."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class CheckpointError(RuntimeError):
    """The checkpoint is corrupt, duplicated, or belongs to another plan."""


class JsonlCheckpoint:
    """Crash-resistant records keyed by generation_index."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[int, dict[str, Any]]:
        if not self.path.exists():
            return {}
        records: dict[int, dict[str, Any]] = {}
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    index = int(record["generation_index"])
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    raise CheckpointError(f"Invalid checkpoint line {line_number}: {exc}") from exc
                if index in records:
                    raise CheckpointError(f"Duplicate generation_index {index}")
                records[index] = record
        return records

    def append(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())

    def compact(self) -> None:
        records = self.load()
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for index in sorted(records):
                handle.write(
                    json.dumps(
                        records[index],
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(self.path)
