"""Recompute auditable M4 generation metrics from JSONL and the cost ledger."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "data" / "generated" / "pilot.jsonl"
DEFAULT_COST = REPO_ROOT / "logs" / "cost.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "m4_pilot_generation.json"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def summarize(input_path: Path, cost_path: Path) -> dict[str, Any]:
    records = _load_jsonl(input_path)
    indices = [record["generation_index"] for record in records]
    sample_ids = [record["sample"]["id"] for record in records if record["sample"] is not None]
    if sorted(indices) != list(range(len(records))):
        raise ValueError("Pilot generation indices are not contiguous from zero")
    if len(indices) != len(set(indices)):
        raise ValueError("Pilot contains duplicate generation indices")
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("Pilot contains duplicate synthetic sample ids")

    cost = json.loads(cost_path.read_text(encoding="utf-8"))
    try:
        relative_input = str(input_path.relative_to(REPO_ROOT))
    except ValueError:
        relative_input = str(input_path.resolve())
    session = next(
        (
            item
            for item in reversed(cost["sessions"])
            if Path(item["output"]) == Path(relative_input)
            and item["complete_records"] == len(records)
        ),
        None,
    )
    if session is None:
        raise ValueError("No matching completed cost session")
    wall_seconds = float(session["wall_seconds"])
    max_under_five_hours = math.floor(5 * 3600 / (wall_seconds / len(records)))
    return {
        "schema_version": 1,
        "input": relative_input,
        "records": len(records),
        "contiguous_indices": True,
        "unique_sample_ids": len(sample_ids),
        "json_valid": len(sample_ids),
        "recipe_counts": dict(
            sorted(
                Counter(
                    record["sample"]["provenance"]["recipe"]
                    for record in records
                    if record["sample"] is not None
                ).items()
            )
        ),
        "style_counts": dict(
            sorted(
                Counter(
                    record["sample"]["style"] for record in records if record["sample"] is not None
                ).items()
            )
        ),
        "generation_contract_reasons": dict(
            sorted(
                Counter(
                    record["generation_contract_reason"] or "PASS" for record in records
                ).items()
            )
        ),
        "prompt_tokens": session["prompt_tokens"],
        "output_tokens": session["output_tokens"],
        "wall_seconds": wall_seconds,
        "requests_per_second": len(records) / wall_seconds,
        "output_tokens_per_second": session["output_tokens"] / wall_seconds,
        "seconds_per_record": wall_seconds / len(records),
        "projected_18k_hours": wall_seconds / len(records) * 18_000 / 3600,
        "max_records_under_five_hours": max_under_five_hours,
        "minimum_f1_f6_acceptance_for_8k": 8_000 / max_under_five_hours,
        "api_cost_usd": session["api_cost_usd"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--cost", type=Path, default=DEFAULT_COST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = summarize(args.input, args.cost)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"verified {payload['records']} records; "
        f"{payload['projected_18k_hours']:.2f}h projected for 18k",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
