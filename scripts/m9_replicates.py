"""Inspect or execute the four guarded M9 extra-seed uncertainty runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.gpu_safety import assert_safe_gpu_launch, safety_status
from src.training.overnight import collect_status
from src.training.replicates import (
    DEFAULT_EVALUATION_REPORT,
    DEFAULT_PIPELINE_REPORT,
    DEFAULT_TRAINING_REPORT,
    execute_replicate_pipeline,
    replicate_status,
)
from src.training.train import DEFAULT_CONFIG

CONFIRMATION = "M9-REPLICATES-43-44-4090"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", help=f"Required with --execute: {CONFIRMATION}")
    parser.add_argument("--training-report", type=Path, default=DEFAULT_TRAINING_REPORT)
    parser.add_argument(
        "--evaluation-report",
        type=Path,
        default=DEFAULT_EVALUATION_REPORT,
    )
    parser.add_argument("--pipeline-report", type=Path, default=DEFAULT_PIPELINE_REPORT)
    args = parser.parse_args()

    status = replicate_status(args.config)
    status["gpu_safety"] = safety_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    if not args.execute:
        return 0
    if args.confirm != CONFIRMATION:
        raise RuntimeError(
            f"M9 replicate execution requires exact --confirm {CONFIRMATION}"
        )
    assert_safe_gpu_launch()
    readiness = collect_status(args.config)
    if not readiness["ready"]:
        failed = [
            check["name"] for check in readiness["checks"] if not check["passed"]
        ]
        raise RuntimeError(f"M9 replicate preflight failed: {failed}")
    result = execute_replicate_pipeline(
        config_path=args.config,
        training_report=args.training_report,
        evaluation_report=args.evaluation_report,
        pipeline_report=args.pipeline_report,
        python_executable=sys.executable,
    )
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
