"""Preflight, inspect, or launch the guarded M9 overnight training batch."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from src.training.overnight import (
    CONFIRMATION,
    DEFAULT_STATUS_REPORT,
    collect_status,
    write_status,
)
from src.training.train import DEFAULT_CONFIG
from src.training.train_all import DEFAULT_BATCH_REPORT, execute_primary_runs


def _print_status(payload: dict[str, Any]) -> None:
    print(f"M9 overnight ready={payload['ready']}")
    for check in payload["checks"]:
        marker = "PASS" if check["passed"] else "FAIL"
        print(f"[{marker}] {check['name']}: {check['observed']}")
    for row in payload["runs"]:
        print(
            f"{row['group']}: train={row['training_status']} "
            f"checkpoint={row['latest_checkpoint']} eval={row['evaluation_status']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", help=f"Required with --execute: {CONFIRMATION}")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--batch-report", type=Path, default=DEFAULT_BATCH_REPORT)
    parser.add_argument("--status-report", type=Path, default=DEFAULT_STATUS_REPORT)
    args = parser.parse_args()

    status = collect_status(args.config)
    write_status(status, args.status_report)
    _print_status(status)
    if not args.execute:
        return 0 if status["ready"] else 1
    if args.confirm != CONFIRMATION:
        raise RuntimeError(
            f"M9 overnight execution requires exact --confirm {CONFIRMATION}"
        )
    if not status["ready"]:
        raise RuntimeError("M9 overnight preflight failed; training was not started")

    result = execute_primary_runs(
        config_path=args.config,
        batch_report=args.batch_report,
    )
    final_status = collect_status(args.config)
    final_status["batch_result"] = result
    write_status(final_status, args.status_report)
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
