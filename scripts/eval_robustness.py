"""Inspect or execute the two-group M10 robustness evaluation batch."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.gpu_safety import assert_safe_gpu_launch, safety_status
from src.training.train import DEFAULT_CONFIG, REPO_ROOT

GROUPS = ("real_only", "real_syn_filtered")
SEED = 42
CONFIRMATION = "M10-ROBUSTNESS-8922-4090"
DEFAULT_BATCH_REPORT = REPO_ROOT / "results" / "m10_robustness_batch.json"
DEFAULT_COMBINED_REPORT = REPO_ROOT / "reports" / "m10_robustness.json"


@dataclass(frozen=True)
class ProbeSpec:
    group: str
    seed: int
    adapter_dir: Path
    output: Path
    primary_report: Path
    report_json: Path
    report_markdown: Path


def build_plan() -> list[ProbeSpec]:
    return [
        ProbeSpec(
            group=group,
            seed=SEED,
            adapter_dir=REPO_ROOT / "runs" / group / f"seed_{SEED}" / "adapter",
            output=(
                REPO_ROOT
                / "results"
                / "robustness"
                / f"{group}_seed_{SEED}.jsonl"
            ),
            primary_report=(
                REPO_ROOT / "reports" / "m9" / f"{group}_seed_{SEED}.json"
            ),
            report_json=(
                REPO_ROOT
                / "reports"
                / "m10_robustness"
                / f"{group}_seed_{SEED}.json"
            ),
            report_markdown=(
                REPO_ROOT
                / "reports"
                / "m10_robustness"
                / f"{group}_seed_{SEED}.md"
            ),
        )
        for group in GROUPS
    ]


def _report_complete(spec: ProbeSpec) -> bool:
    if not spec.report_json.is_file():
        return False
    payload = json.loads(spec.report_json.read_text(encoding="utf-8"))
    return (
        payload.get("status") == "complete"
        and payload.get("group") == spec.group
        and payload.get("seed") == spec.seed
        and payload.get("completed") == 8_922
    )


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _command(spec: ProbeSpec, config: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "src.evaluation.run_probe",
        "--group",
        spec.group,
        "--seed",
        str(spec.seed),
        "--adapter-dir",
        str(spec.adapter_dir),
        "--output",
        str(spec.output),
        "--primary-report",
        str(spec.primary_report),
        "--report-json",
        str(spec.report_json),
        "--report-markdown",
        str(spec.report_markdown),
        "--config",
        str(config),
    ]


def _combined_report(specs: list[ProbeSpec]) -> dict[str, Any]:
    missing = [spec.group for spec in specs if not _report_complete(spec)]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending" if missing else "complete",
        "groups": {},
        "missing_groups": missing,
        "evaluation_only": True,
    }
    for spec in specs:
        if _report_complete(spec):
            payload["groups"][spec.group] = json.loads(
                spec.report_json.read_text(encoding="utf-8")
            )
    return payload


def execute(
    *,
    config: Path,
    batch_report: Path,
    combined_report: Path,
) -> dict[str, Any]:
    specs = build_plan()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "status": "running",
        "runs": [],
    }
    _write(batch_report, payload)
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    for spec in specs:
        row = {
            **asdict(spec),
            "adapter_dir": str(spec.adapter_dir),
            "output": str(spec.output),
            "primary_report": str(spec.primary_report),
            "report_json": str(spec.report_json),
            "report_markdown": str(spec.report_markdown),
            "status": "pending",
        }
        payload["runs"].append(row)
        if _report_complete(spec):
            row["status"] = "skipped_complete"
            _write(batch_report, payload)
            continue
        assert_safe_gpu_launch()
        row["status"] = "running"
        row["started_at"] = datetime.now(timezone.utc).isoformat()
        _write(batch_report, payload)
        completed = subprocess.run(
            _command(spec, config),
            cwd=REPO_ROOT,
            check=False,
            env=environment,
        )
        row["finished_at"] = datetime.now(timezone.utc).isoformat()
        row["returncode"] = completed.returncode
        row["status"] = "completed" if _report_complete(spec) else "failed"
        _write(batch_report, payload)
        if row["status"] == "failed":
            break
    combined = _combined_report(specs)
    _write(combined_report, combined)
    payload["finished_at"] = datetime.now(timezone.utc).isoformat()
    payload["status"] = "complete" if combined["status"] == "complete" else "failed"
    _write(batch_report, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--batch-report", type=Path, default=DEFAULT_BATCH_REPORT)
    parser.add_argument(
        "--combined-report",
        type=Path,
        default=DEFAULT_COMBINED_REPORT,
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", help=f"Required with --execute: {CONFIRMATION}")
    args = parser.parse_args()
    specs = build_plan()
    print(
        json.dumps(
            {
                "runs": [
                    {
                        "group": spec.group,
                        "seed": spec.seed,
                        "complete": _report_complete(spec),
                        "output": str(spec.output),
                    }
                    for spec in specs
                ],
                "gpu_safety": safety_status(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not args.execute:
        return 0
    if args.confirm != CONFIRMATION:
        raise RuntimeError(
            f"Robustness execution requires exact --confirm {CONFIRMATION}"
        )
    result = execute(
        config=args.config,
        batch_report=args.batch_report,
        combined_report=args.combined_report,
    )
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
