"""CPU-only readiness and status checks for the guarded M9 overnight batch."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from src.evaluation.eval_all import build_eval_plan, evaluation_is_complete
from src.training.train import DEFAULT_CONFIG, REPO_ROOT, latest_checkpoint
from src.training.train_all import (
    build_run_plan,
    run_is_complete,
    shared_config_digest,
    validate_primary_inputs,
)

MIN_GPU_TOTAL_MIB = 24_000
MAX_IDLE_GPU_USED_MIB = 3_000
MIN_DISK_FREE_GIB = 20.0
FILTERED_ADDITIONS = 3_760
CONFIRMATION = "M9-OVERNIGHT-3760-4090"
DEFAULT_STATUS_REPORT = REPO_ROOT / "runs" / "m9_overnight_status.json"

EXPECTED_RUNTIME_GIT_PATHS = (
    "reports/m9/",
    "reports/m10_main_results.json",
    "reports/m10_main_results.md",
)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    observed: str
    requirement: str


def parse_gpu_snapshot(raw: str) -> dict[str, Any]:
    """Parse the single-GPU CSV emitted by the guarded nvidia-smi query."""
    rows = [line.strip() for line in raw.splitlines() if line.strip()]
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one GPU row, got {len(rows)}")
    fields = [field.strip() for field in rows[0].split(",")]
    if len(fields) != 5:
        raise ValueError(f"Expected five GPU fields, got {len(fields)}")
    name, total, used, utilization, temperature = fields
    return {
        "name": name,
        "memory_total_mib": int(total),
        "memory_used_mib": int(used),
        "utilization_percent": int(utilization),
        "temperature_c": int(temperature),
    }


def _gpu_snapshot() -> dict[str, Any]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu",
            "--format=csv,noheader,nounits",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "nvidia-smi failed")
    return parse_gpu_snapshot(completed.stdout)


def _git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout


def _unexpected_worktree_changes() -> list[str]:
    changes = []
    for raw_line in _git_output("status", "--porcelain=v1").splitlines():
        path = raw_line[3:].replace("\\", "/").strip('"')
        if any(
            path == allowed or path.startswith(allowed)
            for allowed in EXPECTED_RUNTIME_GIT_PATHS
        ):
            continue
        changes.append(raw_line)
    return changes


def _contributor_audit() -> tuple[bool, str]:
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


def _model_artifacts_match() -> tuple[bool, str]:
    report_path = REPO_ROOT / "reports" / "m8_artifacts.json"
    if not report_path.exists():
        return False, "reports/m8_artifacts.json missing"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    model_dir = REPO_ROOT / report["local_dir"]
    mismatches = []
    for name, expected_size in report["local_files"].items():
        path = model_dir / name
        actual_size = path.stat().st_size if path.is_file() else None
        if actual_size != expected_size:
            mismatches.append(f"{name}:{actual_size}!={expected_size}")
    return not mismatches, "matched" if not mismatches else "; ".join(mismatches)


def _data_inputs_match(config_path: Path) -> tuple[bool, dict[str, int], str]:
    report_path = REPO_ROOT / "reports" / "m9_data_preflight.json"
    if not report_path.exists():
        return False, {}, "reports/m9_data_preflight.json missing"
    frozen = json.loads(report_path.read_text(encoding="utf-8"))
    counts = validate_primary_inputs(config_path)
    expected = {group: row["rows"] for group, row in frozen["groups"].items()}
    additions = counts["real_syn_filtered"] - counts["real_only"]
    passed = counts == expected and additions == FILTERED_ADDITIONS
    observed = (
        f"counts={counts}; filtered_additions={additions}; "
        f"frozen_match={counts == expected}"
    )
    return passed, counts, observed


def _resume_smoke_passed() -> tuple[bool, str]:
    report_path = REPO_ROOT / "reports" / "m9_preflight.json"
    if not report_path.exists():
        return False, "reports/m9_preflight.json missing"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    smoke = report["training"]["resume_smoke"]
    passed = (
        smoke.get("status") == "passed"
        and smoke.get("final_global_step") == 2
        and smoke.get("peak_gpu_reserved_mib", 0) <= MIN_GPU_TOTAL_MIB
    )
    return passed, (
        f"status={smoke.get('status')}; final_step={smoke.get('final_global_step')}; "
        f"peak_reserved_mib={smoke.get('peak_gpu_reserved_mib')}"
    )


def _run_rows(config_path: Path) -> list[dict[str, Any]]:
    eval_by_group = {spec.group: spec for spec in build_eval_plan(config_path)}
    rows = []
    for spec in build_run_plan(config_path):
        checkpoint = latest_checkpoint(spec.output_dir)
        checkpoint_valid = bool(
            checkpoint is not None and (checkpoint / "trainer_state.json").is_file()
        )
        rows.append(
            {
                "group": spec.group,
                "seed": spec.seed,
                "training_status": (
                    "complete"
                    if run_is_complete(spec.output_dir)
                    else "resumable"
                    if checkpoint_valid
                    else "pending"
                ),
                "latest_checkpoint": str(checkpoint) if checkpoint_valid else None,
                "evaluation_status": (
                    "complete"
                    if evaluation_is_complete(eval_by_group[spec.group])
                    else "pending"
                ),
            }
        )
    return rows


def build_checks(
    *,
    contributor_ok: bool,
    contributor_observed: str,
    unexpected_changes: list[str],
    model_ok: bool,
    model_observed: str,
    data_ok: bool,
    data_observed: str,
    resume_ok: bool,
    resume_observed: str,
    gpu: dict[str, Any],
    disk_free_gib: float,
) -> list[Check]:
    """Evaluate collected observations without performing any system calls."""
    return [
        Check(
            "contributors",
            contributor_ok,
            contributor_observed,
            "all commits and local Git identity are kuotunyu; no co-author trailers",
        ),
        Check(
            "worktree",
            not unexpected_changes,
            "clean" if not unexpected_changes else "; ".join(unexpected_changes),
            "no unexpected source or documentation changes",
        ),
        Check(
            "model_artifacts",
            model_ok,
            model_observed,
            "all locally audited Gemma files exist with frozen byte sizes",
        ),
        Check(
            "m9_inputs",
            data_ok,
            data_observed,
            "six frozen group counts match and filtered additions equal 3,760",
        ),
        Check(
            "resume_smoke",
            resume_ok,
            resume_observed,
            "cross-process checkpoint resume smoke passed",
        ),
        Check(
            "gpu_capacity",
            gpu["memory_total_mib"] >= MIN_GPU_TOTAL_MIB,
            f"{gpu['name']}; total={gpu['memory_total_mib']} MiB",
            f"at least {MIN_GPU_TOTAL_MIB} MiB",
        ),
        Check(
            "gpu_available",
            gpu["memory_used_mib"] <= MAX_IDLE_GPU_USED_MIB,
            (
                f"used={gpu['memory_used_mib']} MiB; "
                f"utilization={gpu['utilization_percent']}%; "
                f"temperature={gpu['temperature_c']} C"
            ),
            (
                f"no sibling model workload; baseline memory at most "
                f"{MAX_IDLE_GPU_USED_MIB} MiB"
            ),
        ),
        Check(
            "disk_free",
            disk_free_gib >= MIN_DISK_FREE_GIB,
            f"{disk_free_gib:.2f} GiB",
            f"at least {MIN_DISK_FREE_GIB:.0f} GiB",
        ),
    ]


def collect_status(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    contributor_ok, contributor_observed = _contributor_audit()
    model_ok, model_observed = _model_artifacts_match()
    data_ok, counts, data_observed = _data_inputs_match(config_path)
    resume_ok, resume_observed = _resume_smoke_passed()
    gpu = _gpu_snapshot()
    disk_free_gib = shutil.disk_usage(REPO_ROOT).free / (1024**3)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    checks = build_checks(
        contributor_ok=contributor_ok,
        contributor_observed=contributor_observed,
        unexpected_changes=_unexpected_worktree_changes(),
        model_ok=model_ok,
        model_observed=model_observed,
        data_ok=data_ok,
        data_observed=data_observed,
        resume_ok=resume_ok,
        resume_observed=resume_observed,
        gpu=gpu,
        disk_free_gib=disk_free_gib,
    )
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ready": all(check.passed for check in checks),
        "confirmation": CONFIRMATION,
        "source_commit": _git_output("rev-parse", "HEAD").strip(),
        "shared_config_sha256": shared_config_digest(config),
        "input_counts": counts,
        "gpu": gpu,
        "disk_free_gib": disk_free_gib,
        "checks": [asdict(check) for check in checks],
        "runs": _run_rows(config_path),
        "execution_scope": {
            "training": "six primary seed-42 runs, sequential and resumable",
            "evaluation": "not started automatically",
            "f7_judge": "not started automatically",
        },
    }


def write_status(
    payload: dict[str, Any],
    path: Path = DEFAULT_STATUS_REPORT,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
