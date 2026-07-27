"""Plan and safely execute adapter evaluations for the six M9 primary runs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.training.train import DEFAULT_CONFIG, REPO_ROOT, load_train_config

DEFAULT_EVAL_BATCH_REPORT = REPO_ROOT / "results" / "m9_eval_batch_report.json"


@dataclass(frozen=True)
class EvalSpec:
    group: str
    seed: int
    adapter_dir: Path
    output: Path
    report_json: Path
    report_markdown: Path


def build_eval_plan(config_path: Path = DEFAULT_CONFIG) -> list[EvalSpec]:
    config = load_train_config(config_path)
    seed = int(config["training"]["seed"])
    return [
        EvalSpec(
            group=group,
            seed=seed,
            adapter_dir=REPO_ROOT / "runs" / group / f"seed_{seed}" / "adapter",
            output=REPO_ROOT / "results" / "m9" / f"{group}_seed_{seed}.jsonl",
            report_json=REPO_ROOT / "reports" / "m9" / f"{group}_seed_{seed}.json",
            report_markdown=REPO_ROOT / "reports" / "m9" / f"{group}_seed_{seed}.md",
        )
        for group in config["groups"]
    ]


def evaluation_command(
    spec: EvalSpec,
    *,
    config_path: Path,
    python_executable: str = sys.executable,
    report_only: bool = False,
) -> list[str]:
    command = [
        python_executable,
        "-m",
        "src.evaluation.run_adapter",
        "--group",
        spec.group,
        "--seed",
        str(spec.seed),
        "--adapter-dir",
        str(spec.adapter_dir),
        "--output",
        str(spec.output),
        "--report-json",
        str(spec.report_json),
        "--report-markdown",
        str(spec.report_markdown),
        "--config",
        str(config_path),
    ]
    if report_only:
        command.append("--report-only")
    return command


def evaluation_is_complete(spec: EvalSpec) -> bool:
    if not spec.report_json.exists():
        return False
    try:
        report = json.loads(spec.report_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return (
        report.get("evaluation_mode") == "trained_adapter"
        and report.get("group") == spec.group
        and report.get("seed") == spec.seed
        and report.get("completed") == report.get("target")
    )


def _write_batch_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def execute_evaluations(
    specs: list[EvalSpec],
    *,
    config_path: Path = DEFAULT_CONFIG,
    batch_report: Path = DEFAULT_EVAL_BATCH_REPORT,
    python_executable: str = sys.executable,
    report_only: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "status": "running",
        "runs": [],
    }
    _write_batch_report(batch_report, payload)
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    for spec in specs:
        row: dict[str, Any] = {
            "group": spec.group,
            "seed": spec.seed,
            "status": "pending",
            "returncode": None,
        }
        payload["runs"].append(row)
        if evaluation_is_complete(spec):
            row["status"] = "skipped_complete"
            _write_batch_report(batch_report, payload)
            continue
        if not report_only and not spec.adapter_dir.is_dir():
            row["status"] = "missing_adapter"
            _write_batch_report(batch_report, payload)
            continue
        row["status"] = "running"
        row["started_at"] = datetime.now(timezone.utc).isoformat()
        _write_batch_report(batch_report, payload)
        completed = subprocess.run(
            evaluation_command(
                spec,
                config_path=config_path,
                python_executable=python_executable,
                report_only=report_only,
            ),
            cwd=REPO_ROOT,
            check=False,
            env=environment,
        )
        row["finished_at"] = datetime.now(timezone.utc).isoformat()
        row["returncode"] = completed.returncode
        row["status"] = "completed" if evaluation_is_complete(spec) else "failed"
        _write_batch_report(batch_report, payload)
    failures = [
        row
        for row in payload["runs"]
        if row["status"] in {"failed", "missing_adapter"}
    ]
    payload["finished_at"] = datetime.now(timezone.utc).isoformat()
    payload["status"] = "complete" if not failures else "complete_with_failures"
    _write_batch_report(batch_report, payload)
    return payload
