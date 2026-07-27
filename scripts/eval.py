"""Inspect or execute resumable M9 adapter evaluations."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.evaluation.eval_all import (
    DEFAULT_EVAL_BATCH_REPORT,
    build_eval_plan,
    execute_evaluations,
)
from src.training.train import DEFAULT_CONFIG

CONFIRMATION = "M9-EVAL-LOCAL-4090"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", help="Evaluate one group; default is all six.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--confirm", help=f"Required with --execute: {CONFIRMATION}")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--batch-report", type=Path, default=DEFAULT_EVAL_BATCH_REPORT)
    args = parser.parse_args()
    plans = build_eval_plan(args.config)
    if args.group:
        plans = [plan for plan in plans if plan.group == args.group]
        if not plans:
            raise ValueError(f"Unknown M9 group: {args.group}")
    for plan in plans:
        print(
            f"{plan.group}: seed={plan.seed} adapter={plan.adapter_dir} "
            f"output={plan.output}"
        )
    if not args.execute:
        return 0
    if args.confirm != CONFIRMATION:
        raise RuntimeError(
            f"M9 evaluation requires explicit --confirm {CONFIRMATION}"
        )
    result = execute_evaluations(
        plans,
        config_path=args.config,
        batch_report=args.batch_report,
        report_only=args.report_only,
    )
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
