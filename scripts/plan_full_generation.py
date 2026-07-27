"""Compute a conservative M6 generation count from the calibrated pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.synthetic.sizing import recommend_generation_size

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILTER_REPORT = REPO_ROOT / "reports" / "m5_full_filter_funnel.json"
DEFAULT_GENERATION_REPORT = REPO_ROOT / "reports" / "m4_pilot_generation.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "m6_generation_sizing.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filter-report", type=Path, default=DEFAULT_FILTER_REPORT)
    parser.add_argument("--generation-report", type=Path, default=DEFAULT_GENERATION_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    filtering = json.loads(args.filter_report.read_text(encoding="utf-8"))
    generation = json.loads(args.generation_report.read_text(encoding="utf-8"))
    sizing = recommend_generation_size(
        pilot_accepted=filtering["f1_f6_passed"],
        pilot_total=filtering["total"],
        seconds_per_record=generation["seconds_per_record"],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(sizing.as_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(sizing.as_dict(), ensure_ascii=False, indent=2))
    return 0 if sizing.gate_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
