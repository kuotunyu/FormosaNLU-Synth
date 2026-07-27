"""Inspect or execute the resumable six-group primary M9 batch."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.training.train import DEFAULT_CONFIG
from src.training.train_all import (
    DEFAULT_BATCH_REPORT,
    build_run_plan,
    execute_primary_runs,
    validate_primary_inputs,
)

CONFIRMATION = "M9-LOCAL-4090"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the six primary groups sequentially with resume enabled.",
    )
    parser.add_argument("--confirm", help=f"Required with --execute: {CONFIRMATION}")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--batch-report", type=Path, default=DEFAULT_BATCH_REPORT)
    parser.add_argument("--validate-inputs", action="store_true")
    args = parser.parse_args()
    plans = build_run_plan(args.config)
    for plan in plans:
        print(
            f"{plan.group}: seed={plan.seed} output={plan.output_dir} "
            f"shared={plan.shared_config_sha256[:12]}"
        )
    if args.validate_inputs or args.execute:
        counts = validate_primary_inputs(args.config)
        print(f"input counts: {counts}")
    if args.execute:
        if args.confirm != CONFIRMATION:
            raise RuntimeError(
                f"M9 execution requires explicit --confirm {CONFIRMATION}"
            )
        result = execute_primary_runs(
            config_path=args.config,
            batch_report=args.batch_report,
        )
        if result["status"] != "complete":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
