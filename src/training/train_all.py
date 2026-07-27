"""Plan and safely execute the six compute-matched primary M9 runs."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.training.data import group_examples
from src.training.train import DEFAULT_CONFIG, REPO_ROOT, load_train_config

DEFAULT_BATCH_REPORT = REPO_ROOT / "runs" / "m9_batch_report.json"


@dataclass(frozen=True)
class RunSpec:
    group: str
    seed: int
    output_dir: Path
    shared_config_sha256: str


def shared_config_digest(config: dict[str, Any]) -> str:
    shared = {key: value for key, value in config.items() if key != "groups"}
    encoded = json.dumps(
        shared,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_run_plan(config_path: Path = DEFAULT_CONFIG) -> list[RunSpec]:
    config = load_train_config(config_path)
    digest = shared_config_digest(config)
    seed = int(config["training"]["seed"])
    return [
        RunSpec(
            group=group,
            seed=seed,
            output_dir=REPO_ROOT / "runs" / group / f"seed_{seed}",
            shared_config_sha256=digest,
        )
        for group in config["groups"]
    ]


def run_is_complete(output_dir: Path) -> bool:
    report = output_dir / "run_report.json"
    if not report.exists():
        return False
    try:
        payload = json.loads(report.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return payload.get("status") == "completed" and (output_dir / "adapter").is_dir()


def validate_primary_inputs(
    config_path: Path = DEFAULT_CONFIG,
) -> dict[str, int]:
    config = load_train_config(config_path)
    seed = int(config["training"]["seed"])
    counts = {group: len(group_examples(group, seed=seed)) for group in config["groups"]}
    if set(counts) != set(config["groups"]):
        raise AssertionError("M9 group validation did not cover the frozen group list")
    return counts


def training_command(
    spec: RunSpec,
    *,
    config_path: Path,
    python_executable: str = sys.executable,
) -> list[str]:
    return [
        python_executable,
        "-m",
        "src.training.train",
        "--group",
        spec.group,
        "--config",
        str(config_path),
        "--output-dir",
        str(spec.output_dir),
        "--seed",
        str(spec.seed),
        "--resume",
    ]


def _write_batch_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def execute_primary_runs(
    *,
    config_path: Path = DEFAULT_CONFIG,
    batch_report: Path = DEFAULT_BATCH_REPORT,
    python_executable: str = sys.executable,
) -> dict[str, Any]:
    """Run every primary group sequentially; record failures and keep going."""
    plans = build_run_plan(config_path)
    counts = validate_primary_inputs(config_path)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "status": "running",
        "config": str(config_path),
        "shared_config_sha256": plans[0].shared_config_sha256,
        "input_counts": counts,
        "runs": [],
    }
    _write_batch_report(batch_report, payload)
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    for spec in plans:
        row: dict[str, Any] = {
            "group": spec.group,
            "seed": spec.seed,
            "output_dir": str(spec.output_dir),
            "status": "pending",
            "returncode": None,
        }
        payload["runs"].append(row)
        if run_is_complete(spec.output_dir):
            row["status"] = "skipped_complete"
            _write_batch_report(batch_report, payload)
            continue
        row["status"] = "running"
        row["started_at"] = datetime.now(timezone.utc).isoformat()
        _write_batch_report(batch_report, payload)
        completed = subprocess.run(
            training_command(
                spec,
                config_path=config_path,
                python_executable=python_executable,
            ),
            cwd=REPO_ROOT,
            check=False,
            env=environment,
        )
        row["finished_at"] = datetime.now(timezone.utc).isoformat()
        row["returncode"] = completed.returncode
        row["status"] = "completed" if run_is_complete(spec.output_dir) else "failed"
        _write_batch_report(batch_report, payload)
    failed = [row for row in payload["runs"] if row["status"] == "failed"]
    payload["finished_at"] = datetime.now(timezone.utc).isoformat()
    payload["status"] = "complete" if not failed else "complete_with_failures"
    _write_batch_report(batch_report, payload)
    return payload
