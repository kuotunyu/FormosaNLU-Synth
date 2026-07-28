"""Read-only GPU and sibling-process gates for long FormosaNLU workloads."""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from src.training.train import REPO_ROOT

SIBLING_MARKERS = ("1_DefectForge", "2_SafeSynth")
MAX_IDLE_GPU_USED_MIB = 3_000
MAX_IDLE_GPU_UTILIZATION = 10
MIN_GPU_TOTAL_MIB = 24_000


def gpu_snapshot() -> dict[str, Any]:
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
    rows = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if len(rows) != 1:
        raise RuntimeError(f"Expected one GPU, observed {len(rows)}")
    fields = [field.strip() for field in rows[0].split(",")]
    if len(fields) != 5:
        raise RuntimeError(f"Unexpected nvidia-smi row: {rows[0]}")
    return {
        "name": fields[0],
        "memory_total_mib": int(fields[1]),
        "memory_used_mib": int(fields[2]),
        "utilization_percent": int(fields[3]),
        "temperature_c": int(fields[4]),
    }


def _windows_processes() -> list[dict[str, Any]]:
    command = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "process inventory failed")
    decoded = json.loads(completed.stdout)
    return decoded if isinstance(decoded, list) else [decoded]


def sibling_processes() -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    matches = []
    for process in _windows_processes():
        command_line = str(process.get("CommandLine") or "")
        marker = next(
            (candidate for candidate in SIBLING_MARKERS if candidate in command_line),
            None,
        )
        if marker is None:
            continue
        matches.append(
            {
                "pid": int(process["ProcessId"]),
                "name": process.get("Name"),
                "project": marker,
                "command_line": command_line,
            }
        )
    return matches


def safety_status() -> dict[str, Any]:
    gpu = gpu_snapshot()
    siblings = sibling_processes()
    checks = {
        "gpu_capacity": gpu["memory_total_mib"] >= MIN_GPU_TOTAL_MIB,
        "gpu_memory_idle": gpu["memory_used_mib"] <= MAX_IDLE_GPU_USED_MIB,
        "gpu_utilization_idle": (
            gpu["utilization_percent"] <= MAX_IDLE_GPU_UTILIZATION
        ),
        "siblings_absent": not siblings,
    }
    return {
        "safe": all(checks.values()),
        "gpu": gpu,
        "sibling_processes": siblings,
        "checks": checks,
    }


def assert_safe_gpu_launch() -> dict[str, Any]:
    status = safety_status()
    if not status["safe"]:
        failed = [name for name, passed in status["checks"].items() if not passed]
        raise RuntimeError(f"GPU launch safety gate failed: {failed}")
    return status
