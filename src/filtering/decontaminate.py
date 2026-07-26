"""Auditable F6 exclusion log helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def write_exclusion_log(
    rows: list[dict[str, Any]],
    output: Path,
) -> None:
    """Write exclusions only; this function never mutates its input dataset."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            required = {"sample_id", "similarity", "matched_eval_id", "split"}
            if set(row) != required:
                raise ValueError(f"Decontamination log fields must be {sorted(required)}")
            if row["split"] not in {"validation", "test"}:
                raise ValueError("Decontamination matches must be validation or test")
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and rewrite an existing F6 exclusion JSON array as JSONL."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Input must be a JSON array")
    write_exclusion_log(rows, args.output)
    print(f"wrote {len(rows)} auditable exclusions to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

