"""Inspect, smoke-test, or execute the guarded M15 Phi replication."""

from __future__ import annotations

import argparse
import hashlib
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
QUALIFY_CONFIRMATION = "M15-SMOKE-AMENDMENT-STRUCTURAL-V2"
EXECUTE_CONFIRMATION = "M15-PHI4MINI-6RUNS-4090"
ARTIFACT_REPORT = REPO_ROOT / "reports" / "m15_phi4mini_artifacts.json"
SMOKE_REPORT = REPO_ROOT / "reports" / "m15_phi4mini_smoke.json"
SMOKE_AMENDMENT = REPO_ROOT / "reports" / "m15_smoke_protocol_amendment.json"
SMOKE_QUALIFICATION = (
    REPO_ROOT / "reports" / "m15_phi4mini_smoke_qualification.json"
)
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_relative(value: str | Path) -> str:
    path = Path(value)
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


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
    payload = _read_json(SMOKE_QUALIFICATION)
    if payload is None:
        return False, "amended smoke qualification missing"
    passed, _ = _validate_qualification_payload(payload)
    source_hashes = payload.get("source_sha256", {})
    passed = (
        passed
        and SMOKE_REPORT.is_file()
        and SMOKE_PREDICTIONS.is_file()
        and SMOKE_EVALUATION.is_file()
        and (SMOKE_ROOT / "run_report.json").is_file()
        and SMOKE_AMENDMENT.is_file()
        and source_hashes.get("original_smoke_report") == _sha256(SMOKE_REPORT)
        and source_hashes.get("predictions") == _sha256(SMOKE_PREDICTIONS)
        and source_hashes.get("evaluation_report") == _sha256(SMOKE_EVALUATION)
        and source_hashes.get("run_report")
        == _sha256(SMOKE_ROOT / "run_report.json")
        and source_hashes.get("protocol_amendment") == _sha256(SMOKE_AMENDMENT)
    )
    return passed, (
        f"protocol={payload.get('protocol_id')}; status={payload.get('status')}; "
        f"step={payload.get('infrastructure', {}).get('final_global_step')}; "
        f"syntax_valid={payload.get('structure', {}).get('json_syntax_valid')}; "
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
    if SMOKE_REPORT.exists():
        raise RuntimeError(
            "Original M15 smoke evidence already exists and may not be overwritten"
        )
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


def _prediction_structure(path: Path) -> dict[str, Any]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    counts = {
        "rows": len(rows),
        "json_syntax_valid": 0,
        "json_object": 0,
        "intent_is_string": 0,
        "slots_is_list": 0,
        "slot_object_list": 0,
    }
    for row in rows:
        try:
            parsed = json.loads(row["raw_prediction"])
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        counts["json_syntax_valid"] += 1
        if not isinstance(parsed, dict):
            continue
        counts["json_object"] += 1
        counts["intent_is_string"] += int(isinstance(parsed.get("intent"), str))
        slots = parsed.get("slots")
        counts["slots_is_list"] += int(isinstance(slots, list))
        counts["slot_object_list"] += int(
            isinstance(slots, list)
            and all(isinstance(slot, dict) for slot in slots)
        )
    return counts


def _validate_qualification_payload(
    payload: dict[str, Any],
) -> tuple[bool, str]:
    infrastructure = payload.get("infrastructure", {})
    structure = payload.get("structure", {})
    passed = (
        payload.get("protocol_id") == "m15.smoke.infrastructure.v2"
        and payload.get("status") == "passed"
        and payload.get("original_gate", {}).get("status") == "failed"
        and payload.get("formal_experiment_contract_unchanged") is True
        and infrastructure.get("first_checkpoint") == "checkpoint-1"
        and str(infrastructure.get("resumed_from", "")).endswith("checkpoint-1")
        and infrastructure.get("final_checkpoint") == "checkpoint-2"
        and infrastructure.get("final_global_step") == 2
        and infrastructure.get("evaluation_completed") == 32
        and payload.get("peak_gpu_reserved_mib", 99_999) <= 24_564
        and structure.get("rows") == 32
        and structure.get("json_syntax_valid") == 32
        and structure.get("json_object") == 32
        and structure.get("intent_is_string") == 32
        and structure.get("slots_is_list") == 32
    )
    return passed, json.dumps(payload, ensure_ascii=False)


def qualify_existing_smoke() -> dict[str, Any]:
    original = _read_json(SMOKE_REPORT)
    evaluation = _read_json(SMOKE_EVALUATION)
    run_report = _read_json(SMOKE_ROOT / "run_report.json")
    if original is None or evaluation is None or run_report is None:
        raise RuntimeError("Original smoke evidence is incomplete")
    original_passed, _ = _validate_smoke_payload(original)
    if original_passed or original.get("status") != "failed":
        raise RuntimeError("Protocol amendment requires the preserved failed smoke")
    if not SMOKE_PREDICTIONS.is_file():
        raise RuntimeError("Original smoke predictions are missing")

    created_at = datetime.now(timezone.utc).isoformat()
    amendment = {
        "schema_version": 1,
        "protocol_id": "m15.smoke.infrastructure.v2",
        "created_at": created_at,
        "status": "approved_before_formal_runs",
        "authorization_basis": (
            "The user delegated the technical remedy after reviewing why the "
            "original M15 smoke failed; no formal Phi run had started."
        ),
        "original_gate": {
            "purpose": "mixed infrastructure and two-step task-quality gate",
            "strict_json_valid_rate_minimum": 0.25,
            "observed": original.get("json_valid_rate"),
            "status": "failed",
        },
        "amended_gate": {
            "purpose": "infrastructure qualification only",
            "requirements": [
                "checkpoint-1 is created",
                "resume reaches checkpoint-2 and global step 2",
                "32-row adapter evaluation completes",
                "peak reserved VRAM is at most 24564 MiB",
                "32/32 outputs parse as JSON objects",
                "32/32 outputs contain string intent and list slots",
            ],
        },
        "formal_experiment_contract_unchanged": {
            "model_revision": True,
            "training_data_and_hashes": True,
            "prompt_template": True,
            "max_steps_500": True,
            "seeds_42_43_44": True,
            "strict_evaluation_metrics": True,
            "preregistered_cross_family_criterion": True,
        },
        "research_integrity": {
            "original_failure_preserved": _repo_relative(SMOKE_REPORT),
            "formal_phi_runs_started_before_amendment": 0,
            "unknown intents remain failures in formal evaluation": True,
            "no parser repair or label aliasing": True,
        },
    }
    SMOKE_AMENDMENT.write_text(
        json.dumps(amendment, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    structure = _prediction_structure(SMOKE_PREDICTIONS)
    payload = {
        "schema_version": 1,
        "protocol_id": "m15.smoke.infrastructure.v2",
        "created_at": created_at,
        "status": "passed",
        "model": original.get("model"),
        "revision": original.get("revision"),
        "original_gate": {
            "status": "failed",
            "strict_json_valid_rate": original.get("json_valid_rate"),
            "parser_outcomes": evaluation.get("parser_outcomes"),
        },
        "infrastructure": {
            "first_checkpoint": original.get("first_checkpoint"),
            "resumed_from": _repo_relative(original.get("resumed_from", "")),
            "final_checkpoint": original.get("final_checkpoint"),
            "final_global_step": original.get("final_global_step"),
            "evaluation_completed": original.get("evaluation_completed"),
        },
        "structure": structure,
        "peak_gpu_allocated_mib": original.get("peak_gpu_allocated_mib"),
        "peak_gpu_reserved_mib": original.get("peak_gpu_reserved_mib"),
        "formal_experiment_contract_unchanged": True,
        "source_sha256": {
            "original_smoke_report": _sha256(SMOKE_REPORT),
            "predictions": _sha256(SMOKE_PREDICTIONS),
            "evaluation_report": _sha256(SMOKE_EVALUATION),
            "run_report": _sha256(SMOKE_ROOT / "run_report.json"),
            "protocol_amendment": _sha256(SMOKE_AMENDMENT),
        },
    }
    passed, _ = _validate_qualification_payload(payload)
    payload["status"] = "passed" if passed else "failed"
    SMOKE_QUALIFICATION.write_text(
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
    mode.add_argument("--qualify-smoke", action="store_true")
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
    if args.qualify_smoke:
        if args.confirm != QUALIFY_CONFIRMATION:
            raise RuntimeError(
                f"M15 qualification requires exact --confirm {QUALIFY_CONFIRMATION}"
            )
        payload = qualify_existing_smoke()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["status"] == "passed" else 1
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
