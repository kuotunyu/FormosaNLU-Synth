"""Frozen six-run Phi-4-mini replication plan for M15."""

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
from src.training.data import group_examples
from src.training.train import REPO_ROOT, load_train_config
from src.training.train_all import (
    RunSpec,
    run_is_complete,
    shared_config_digest,
    training_command,
)

CONFIG_PATH = REPO_ROOT / "configs" / "train_phi4mini.yaml"
PRIMARY_CONFIG_PATH = REPO_ROOT / "configs" / "train.yaml"
GROUPS = ("real_only", "real_syn_filtered")
SEEDS = (42, 43, 44)
RUN_ROOT = REPO_ROOT / "runs" / "m15" / "phi4mini"
RESULT_ROOT = REPO_ROOT / "results" / "m15" / "phi4mini"
REPORT_ROOT = REPO_ROOT / "reports" / "m15" / "phi4mini"
TRAINING_REPORT = RUN_ROOT / "training_batch.json"
EVALUATION_REPORT = RESULT_ROOT / "evaluation_batch.json"
PIPELINE_REPORT = RUN_ROOT / "pipeline.json"
FROZEN_DATA_REPORT = REPO_ROOT / "reports" / "m9_data_preflight.json"


def _digest_rows(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            json.dumps(
                row,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def validate_contract(
    config_path: Path = CONFIG_PATH,
    primary_config_path: Path = PRIMARY_CONFIG_PATH,
) -> dict[str, Any]:
    """Prove M15 changes the model family, output paths, and seeds only."""
    config = load_train_config(config_path)
    primary = load_train_config(primary_config_path)
    for section in ("quantization", "lora", "training", "inference"):
        if config[section] != primary[section]:
            raise AssertionError(f"M15 drifted from primary {section} contract")
    if tuple(config["groups"]) != GROUPS:
        raise AssertionError(f"M15 groups must be exactly {GROUPS}")
    if config["model"]["prompt_template_version"] != primary["model"][
        "prompt_template_version"
    ]:
        raise AssertionError("M15 prompt template drifted from the Gemma contract")

    frozen = json.loads(FROZEN_DATA_REPORT.read_text(encoding="utf-8"))
    groups: dict[str, Any] = {}
    for group in GROUPS:
        expected = frozen["groups"][group]
        seed_rows: dict[str, Any] = {}
        for seed in SEEDS:
            rows = group_examples(group, seed=seed)
            observed = {
                "rows": len(rows),
                "unique_ids": len({str(row["id"]) for row in rows}),
                "sha256": _digest_rows(rows),
            }
            if observed["rows"] != expected["rows"]:
                raise AssertionError(f"{group} seed {seed} row count drifted")
            if observed["unique_ids"] != expected["unique_ids"]:
                raise AssertionError(f"{group} seed {seed} unique IDs drifted")
            if observed["sha256"] != expected["sha256"]:
                raise AssertionError(f"{group} seed {seed} data SHA-256 drifted")
            seed_rows[str(seed)] = observed
        groups[group] = {
            "frozen_sha256": expected["sha256"],
            "seeds": seed_rows,
        }
    return {
        "schema_version": 1,
        "status": "validated",
        "model": config["model"],
        "shared_config_sha256": shared_config_digest(config),
        "groups": groups,
        "seeds": list(SEEDS),
    }


def build_run_plan(config_path: Path = CONFIG_PATH) -> list[RunSpec]:
    config = load_train_config(config_path)
    digest = shared_config_digest(config)
    return [
        RunSpec(
            group=group,
            seed=seed,
            output_dir=RUN_ROOT / group / f"seed_{seed}",
            shared_config_sha256=digest,
        )
        for group in GROUPS
        for seed in SEEDS
    ]


def build_eval_plan(config_path: Path = CONFIG_PATH) -> list[EvalSpec]:
    _ = load_train_config(config_path)
    return [
        EvalSpec(
            group=spec.group,
            seed=spec.seed,
            adapter_dir=spec.output_dir / "adapter",
            output=RESULT_ROOT / f"{spec.group}_seed_{spec.seed}.jsonl",
            report_json=REPORT_ROOT / f"{spec.group}_seed_{spec.seed}.json",
            report_markdown=REPORT_ROOT / f"{spec.group}_seed_{spec.seed}.md",
        )
        for spec in build_run_plan(config_path)
    ]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def status(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    validation = validate_contract(config_path)
    eval_by_key = {
        (spec.group, spec.seed): spec for spec in build_eval_plan(config_path)
    }
    rows = []
    for spec in build_run_plan(config_path):
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


def execute_pipeline(
    *,
    config_path: Path = CONFIG_PATH,
    python_executable: str = sys.executable,
) -> dict[str, Any]:
    validation = validate_contract(config_path)
    plans = build_run_plan(config_path)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "status": "training",
        "validation": validation,
        "training_report": str(TRAINING_REPORT),
        "evaluation_report": str(EVALUATION_REPORT),
    }
    _write_json(PIPELINE_REPORT, payload)
    training: dict[str, Any] = {
        "schema_version": 1,
        "status": "running",
        "runs": [],
    }
    _write_json(TRAINING_REPORT, training)
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
        training["runs"].append(row)
        if run_is_complete(spec.output_dir):
            row["status"] = "skipped_complete"
            _write_json(TRAINING_REPORT, training)
            continue
        row["status"] = "running"
        row["started_at"] = datetime.now(timezone.utc).isoformat()
        _write_json(TRAINING_REPORT, training)
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
        row["returncode"] = completed.returncode
        row["finished_at"] = datetime.now(timezone.utc).isoformat()
        row["status"] = "completed" if run_is_complete(spec.output_dir) else "failed"
        _write_json(TRAINING_REPORT, training)
        if row["status"] == "failed":
            training["status"] = "failed"
            payload["status"] = "training_failed"
            payload["finished_at"] = datetime.now(timezone.utc).isoformat()
            _write_json(TRAINING_REPORT, training)
            _write_json(PIPELINE_REPORT, payload)
            return payload

    training["status"] = "complete"
    _write_json(TRAINING_REPORT, training)
    payload["status"] = "evaluation"
    _write_json(PIPELINE_REPORT, payload)
    evaluation = execute_evaluations(
        build_eval_plan(config_path),
        config_path=config_path,
        batch_report=EVALUATION_REPORT,
        python_executable=python_executable,
    )
    payload["evaluation_status"] = evaluation["status"]
    if evaluation["status"] != "complete":
        payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        payload["status"] = "evaluation_failed"
        _write_json(PIPELINE_REPORT, payload)
        return payload

    payload["status"] = "statistics"
    _write_json(PIPELINE_REPORT, payload)
    for module in (
        "scripts.m15_phi_statistics",
        "scripts.m15_cross_model_report",
    ):
        completed = subprocess.run(
            [python_executable, "-m", module],
            cwd=REPO_ROOT,
            check=False,
            env=environment,
        )
        if completed.returncode != 0:
            payload["status"] = "statistics_failed"
            payload["failed_module"] = module
            payload["finished_at"] = datetime.now(timezone.utc).isoformat()
            _write_json(PIPELINE_REPORT, payload)
            return payload
    payload["status"] = "complete"
    payload["finished_at"] = datetime.now(timezone.utc).isoformat()
    payload["paired_statistics"] = str(
        REPO_ROOT / "reports" / "m15_phi4mini_paired_statistics.json"
    )
    payload["cross_model_report"] = str(
        REPO_ROOT / "reports" / "m15_cross_model_replication.json"
    )
    _write_json(PIPELINE_REPORT, payload)
    return payload
