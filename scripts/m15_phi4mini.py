"""Inspect, smoke-test, or execute the guarded M15 Phi replication."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.gpu_safety import assert_safe_gpu_launch, safety_status
from src.training.cross_model import CONFIG_PATH, execute_pipeline
from src.training.cross_model import status as experiment_status
from src.training.train import REPO_ROOT, latest_checkpoint

SMOKE_CONFIRMATION = "M15-PHI4MINI-SMOKE-4090"
EXECUTE_CONFIRMATION = "M15-PHI4MINI-6RUNS-4090"
ARTIFACT_REPORT = REPO_ROOT / "reports" / "m15_phi4mini_artifacts.json"
SMOKE_REPORT = REPO_ROOT / "reports" / "m15_phi4mini_smoke.json"
SMOKE_ROOT = REPO_ROOT / "runs" / "m15" / "phi4mini_smoke" / "seed_42"
SMOKE_PREDICTIONS = (
    REPO_ROOT / "results" / "m15" / "phi4mini_smoke_seed_42.jsonl"
)
SMOKE_EVALUATION = (
    REPO_ROOT / "reports" / "m15" / "phi4mini_smoke_seed_42.json"
)
SMOKE_EVALUATION_MD = (
    REPO_ROOT / "reports" / "m15" / "phi4mini_smoke_seed_42.md"
)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def artifact_ready() -> tuple[bool, str]:
    payload = _read_json(ARTIFACT_REPORT)
    if payload is None or payload.get("status") != "complete":
        return False, "artifact audit report missing or incomplete"
    local_dir = REPO_ROOT / payload["local_dir"]
    for name, row in payload["local"]["files"].items():
        path = local_dir / name
        if not path.is_file() or path.stat().st_size != row["bytes"]:
            return False, f"artifact size mismatch: {name}"
    return True, f"{payload['model']['revision']}; {payload['model']['download_bytes']} bytes"


def smoke_ready() -> tuple[bool, str]:
    payload = _read_json(SMOKE_REPORT)
    if payload is None:
        return False, "smoke report missing"
    passed = (
        payload.get("status") == "passed"
        and payload.get("final_global_step") == 2
        and payload.get("evaluation_completed") == 32
        and payload.get("json_valid_rate", 0.0) >= 0.25
        and payload.get("peak_gpu_reserved_mib", 99_999) <= 24_564
    )
    return passed, (
        f"status={payload.get('status')}; step={payload.get('final_global_step')}; "
        f"json_valid={payload.get('json_valid_rate')}; "
        f"peak_reserved={payload.get('peak_gpu_reserved_mib')}"
    )


def _worktree_clean() -> tuple[bool, str]:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    rows = [row for row in completed.stdout.splitlines() if row.strip()]
    return not rows, "clean" if not rows else "; ".join(rows)


def _contributors_ok() -> tuple[bool, str]:
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "verify_contributors.py")],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    output = (completed.stdout or completed.stderr).strip()
    return completed.returncode == 0, output


def preflight() -> dict[str, Any]:
    artifact_ok, artifact_observed = artifact_ready()
    smoke_ok, smoke_observed = smoke_ready()
    worktree_ok, worktree_observed = _worktree_clean()
    contributor_ok, contributor_observed = _contributors_ok()
    contract: dict[str, Any] | None = None
    contract_error: str | None = None
    try:
        contract = experiment_status(CONFIG_PATH)
    except Exception as exc:
        contract_error = f"{type(exc).__name__}: {exc}"
    gpu = safety_status()
    checks = {
        "artifact": artifact_ok,
        "smoke": smoke_ok,
        "contract": contract_error is None,
        "worktree": worktree_ok,
        "contributors": contributor_ok,
        "gpu": gpu["safe"],
    }
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ready": all(checks.values()),
        "checks": checks,
        "artifact": artifact_observed,
        "smoke": smoke_observed,
        "contract_error": contract_error,
        "experiment": contract,
        "worktree": worktree_observed,
        "contributors": contributor_observed,
        "gpu_safety": gpu,
        "confirmation": EXECUTE_CONFIRMATION,
    }


def _run_command(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed with {completed.returncode}: {' '.join(command)}"
        )


def run_smoke() -> dict[str, Any]:
    artifact_ok, artifact_observed = artifact_ready()
    if not artifact_ok:
        raise RuntimeError(f"Phi artifact gate failed: {artifact_observed}")
    assert_safe_gpu_launch()
    common = [
        sys.executable,
        "-m",
        "src.training.train",
        "--group",
        "real_only",
        "--config",
        str(CONFIG_PATH),
        "--output-dir",
        str(SMOKE_ROOT),
        "--seed",
        "42",
        "--smoke-test",
        "--resume",
    ]
    checkpoint = latest_checkpoint(SMOKE_ROOT)
    if checkpoint is None:
        _run_command([*common, "--max-steps-override", "1"])
        checkpoint = latest_checkpoint(SMOKE_ROOT)
    if checkpoint is None or checkpoint.name not in {"checkpoint-1", "checkpoint-2"}:
        raise RuntimeError(f"Unexpected smoke checkpoint: {checkpoint}")
    checkpoint_one = SMOKE_ROOT / "checkpoint-1"
    if checkpoint.name == "checkpoint-1":
        _run_command([*common, "--max-steps-override", "2"])
    checkpoint_two = latest_checkpoint(SMOKE_ROOT)
    if checkpoint_two is None or checkpoint_two.name != "checkpoint-2":
        raise RuntimeError(f"Expected checkpoint-2, got {checkpoint_two}")
    _run_command(
        [
            sys.executable,
            "-m",
            "src.evaluation.run_adapter",
            "--group",
            "real_only",
            "--seed",
            "42",
            "--adapter-dir",
            str(SMOKE_ROOT / "adapter"),
            "--output",
            str(SMOKE_PREDICTIONS),
            "--report-json",
            str(SMOKE_EVALUATION),
            "--report-markdown",
            str(SMOKE_EVALUATION_MD),
            "--config",
            str(CONFIG_PATH),
            "--limit",
            "32",
        ]
    )
    run_report = _read_json(SMOKE_ROOT / "run_report.json") or {}
    evaluation = _read_json(SMOKE_EVALUATION) or {}
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "model": "microsoft/Phi-4-mini-instruct",
        "revision": "cfbefacb99257ffa30c83adab238a50856ac3083",
        "first_checkpoint": checkpoint_one.name,
        "resumed_from": str(run_report.get("resumed_from")),
        "final_global_step": run_report.get("global_step"),
        "final_checkpoint": checkpoint_two.name,
        "peak_gpu_allocated_mib": run_report.get("peak_gpu_allocated_mib"),
        "peak_gpu_reserved_mib": run_report.get("peak_gpu_reserved_mib"),
        "evaluation_completed": evaluation.get("completed"),
        "json_valid_rate": evaluation.get("metrics", {}).get("json_valid_rate"),
        "intent_accuracy": evaluation.get("metrics", {}).get("intent_accuracy"),
    }
    passed, _ = _validate_smoke_payload(payload)
    payload["status"] = "passed" if passed else "failed"
    SMOKE_REPORT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def _validate_smoke_payload(payload: dict[str, Any]) -> tuple[bool, str]:
    passed = (
        payload.get("final_global_step") == 2
        and payload.get("evaluation_completed") == 32
        and payload.get("json_valid_rate", 0.0) >= 0.25
        and payload.get("peak_gpu_reserved_mib", 99_999) <= 24_564
    )
    return passed, json.dumps(payload, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm")
    args = parser.parse_args()

    if args.smoke:
        if args.confirm != SMOKE_CONFIRMATION:
            raise RuntimeError(
                f"M15 smoke requires exact --confirm {SMOKE_CONFIRMATION}"
            )
        print(json.dumps(run_smoke(), ensure_ascii=False, indent=2))
        return 0
    if args.execute:
        if args.confirm != EXECUTE_CONFIRMATION:
            raise RuntimeError(
                f"M15 execution requires exact --confirm {EXECUTE_CONFIRMATION}"
            )
        readiness = preflight()
        print(json.dumps(readiness, ensure_ascii=False, indent=2))
        if not readiness["ready"]:
            raise RuntimeError("M15 preflight failed; six-run pipeline not started")
        result = execute_pipeline(config_path=CONFIG_PATH)
        return 0 if result["status"] == "complete" else 1
    print(json.dumps(preflight(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
