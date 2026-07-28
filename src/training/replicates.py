"""Guarded M9 uncertainty reruns for the two preregistered comparison groups."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.evaluation.eval_all import (
    EvalSpec,
    evaluation_is_complete,
    execute_evaluations,
)
from src.evaluation.replicate_report import (
    build_replicate_summary,
    write_replicate_summary,
)
from src.training.data import group_examples
from src.training.train import DEFAULT_CONFIG, REPO_ROOT, load_train_config
from src.training.train_all import (
    RunSpec,
    run_is_complete,
    shared_config_digest,
    training_command,
)

REPLICATE_GROUPS = ("real_only", "real_syn_filtered")
REPLICATE_SEEDS = (43, 44)
DEFAULT_TRAINING_REPORT = REPO_ROOT / "runs" / "m9_replicates_batch_report.json"
DEFAULT_EVALUATION_REPORT = (
    REPO_ROOT / "results" / "m9_replicates_eval_batch_report.json"
)
DEFAULT_PIPELINE_REPORT = REPO_ROOT / "runs" / "m9_replicates_pipeline.json"


def build_replicate_run_plan(
    config_path: Path = DEFAULT_CONFIG,
) -> list[RunSpec]:
    config = load_train_config(config_path)
    missing = sorted(set(REPLICATE_GROUPS) - set(config["groups"]))
    if missing:
        raise ValueError(f"Replicate groups missing from frozen config: {missing}")
    digest = shared_config_digest(config)
    return [
        RunSpec(
            group=group,
            seed=seed,
            output_dir=REPO_ROOT / "runs" / group / f"seed_{seed}",
            shared_config_sha256=digest,
        )
        for group in REPLICATE_GROUPS
        for seed in REPLICATE_SEEDS
    ]


def build_replicate_eval_plan(
    config_path: Path = DEFAULT_CONFIG,
) -> list[EvalSpec]:
    _ = load_train_config(config_path)
    return [
        EvalSpec(
            group=spec.group,
            seed=spec.seed,
            adapter_dir=spec.output_dir / "adapter",
            output=(
                REPO_ROOT
                / "results"
                / "m9"
                / f"{spec.group}_seed_{spec.seed}.jsonl"
            ),
            report_json=(
                REPO_ROOT
                / "reports"
                / "m9"
                / f"{spec.group}_seed_{spec.seed}.json"
            ),
            report_markdown=(
                REPO_ROOT
                / "reports"
                / "m9"
                / f"{spec.group}_seed_{spec.seed}.md"
            ),
        )
        for spec in build_replicate_run_plan(config_path)
    ]


def _rows_digest(rows: list[dict[str, Any]]) -> str:
    normalized = sorted(rows, key=lambda row: str(row["id"]))
    encoded = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_replicate_inputs(
    config_path: Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Prove that the reruns change only training randomness, not training rows."""
    config = load_train_config(config_path)
    if int(config["training"]["seed"]) != 42:
        raise ValueError("Frozen primary training seed must remain 42")

    groups: dict[str, Any] = {}
    for group in REPLICATE_GROUPS:
        primary_rows = group_examples(group, seed=42)
        primary_digest = _rows_digest(primary_rows)
        seed_rows: dict[str, Any] = {}
        for seed in REPLICATE_SEEDS:
            rows = group_examples(group, seed=seed)
            digest = _rows_digest(rows)
            if digest != primary_digest:
                raise AssertionError(
                    f"{group} seed {seed} changes the frozen training examples"
                )
            seed_rows[str(seed)] = {"rows": len(rows), "sha256": digest}
        groups[group] = {
            "primary_seed": 42,
            "rows": len(primary_rows),
            "sha256": primary_digest,
            "replicates": seed_rows,
        }

    primary_batch = REPO_ROOT / "runs" / "m9_batch_report.json"
    primary_payload = json.loads(primary_batch.read_text(encoding="utf-8"))
    current_digest = shared_config_digest(config)
    if primary_payload.get("shared_config_sha256") != current_digest:
        raise AssertionError("Frozen config no longer matches the primary M9 batch")
    return {
        "schema_version": 1,
        "status": "validated",
        "shared_config_sha256": current_digest,
        "groups": groups,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def execute_replicate_training(
    *,
    config_path: Path = DEFAULT_CONFIG,
    batch_report: Path = DEFAULT_TRAINING_REPORT,
    python_executable: str = sys.executable,
) -> dict[str, Any]:
    validation = validate_replicate_inputs(config_path)
    plans = build_replicate_run_plan(config_path)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "status": "running",
        "shared_config_sha256": validation["shared_config_sha256"],
        "input_validation": validation,
        "runs": [],
    }
    _write_json(batch_report, payload)
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
            _write_json(batch_report, payload)
            continue
        row["status"] = "running"
        row["started_at"] = datetime.now(timezone.utc).isoformat()
        _write_json(batch_report, payload)
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
        _write_json(batch_report, payload)
        if row["status"] == "failed":
            break

    failures = [row for row in payload["runs"] if row["status"] == "failed"]
    payload["finished_at"] = datetime.now(timezone.utc).isoformat()
    payload["status"] = "complete" if not failures else "failed"
    _write_json(batch_report, payload)
    return payload


def execute_replicate_pipeline(
    *,
    config_path: Path = DEFAULT_CONFIG,
    training_report: Path = DEFAULT_TRAINING_REPORT,
    evaluation_report: Path = DEFAULT_EVALUATION_REPORT,
    pipeline_report: Path = DEFAULT_PIPELINE_REPORT,
    python_executable: str = sys.executable,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "status": "training",
        "training_report": str(training_report),
        "evaluation_report": str(evaluation_report),
    }
    _write_json(pipeline_report, payload)
    training = execute_replicate_training(
        config_path=config_path,
        batch_report=training_report,
        python_executable=python_executable,
    )
    payload["training_status"] = training["status"]
    if training["status"] != "complete":
        payload["status"] = "training_failed"
        payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_json(pipeline_report, payload)
        return payload

    payload["status"] = "evaluation"
    _write_json(pipeline_report, payload)
    evaluation = execute_evaluations(
        build_replicate_eval_plan(config_path),
        config_path=config_path,
        batch_report=evaluation_report,
        python_executable=python_executable,
    )
    payload["evaluation_status"] = evaluation["status"]
    payload["finished_at"] = datetime.now(timezone.utc).isoformat()
    payload["status"] = (
        "complete" if evaluation["status"] == "complete" else "evaluation_failed"
    )
    if payload["status"] == "complete":
        summary = build_replicate_summary()
        write_replicate_summary(summary)
        if summary["status"] != "complete":
            payload["status"] = "summary_failed"
        payload["summary_status"] = summary["status"]
    _write_json(pipeline_report, payload)
    return payload


def replicate_status(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    validation = validate_replicate_inputs(config_path)
    eval_by_key = {
        (spec.group, spec.seed): spec for spec in build_replicate_eval_plan(config_path)
    }
    rows = []
    for spec in build_replicate_run_plan(config_path):
        eval_spec = eval_by_key[(spec.group, spec.seed)]
        rows.append(
            {
                "group": spec.group,
                "seed": spec.seed,
                "training_complete": run_is_complete(spec.output_dir),
                "evaluation_complete": evaluation_is_complete(eval_spec),
                "output_dir": str(spec.output_dir),
            }
        )
    return {"validation": validation, "runs": rows}
