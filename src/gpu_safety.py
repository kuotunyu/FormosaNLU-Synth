"""Read-only GPU and sibling-process gates for long FormosaNLU workloads."""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from src.training.train import REPO_ROOT

SIBLING_MARKERS = ("1_DefectForge", "2_SafeSynth")
BLOCKING_PROCESS_NAMES = {
    "cmd.exe",
    "ollama.exe",
    "powershell.exe",
    "pwsh.exe",
    "python.exe",
    "pythonw.exe",
}
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
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine | "
        "ConvertTo-Json -Compress"
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


def _ancestor_pids(
    processes: list[dict[str, Any]],
    *,
    current_pid: int,
) -> set[int]:
    parent_by_pid = {
        int(process["ProcessId"]): int(process.get("ParentProcessId") or 0)
        for process in processes
        if process.get("ProcessId") is not None
    }
    ancestors: set[int] = set()
    candidate = parent_by_pid.get(current_pid, 0)
    while candidate and candidate not in ancestors:
        ancestors.add(candidate)
        candidate = parent_by_pid.get(candidate, 0)
    return ancestors


def _matching_sibling_processes(
    processes: list[dict[str, Any]],
    *,
    current_pid: int,
) -> list[dict[str, Any]]:
    ignored_pids = _ancestor_pids(processes, current_pid=current_pid) | {current_pid}
    matches = []
    for process in processes:
        pid = int(process["ProcessId"])
        process_name = str(process.get("Name") or "").lower()
        if pid in ignored_pids or process_name not in BLOCKING_PROCESS_NAMES:
            continue
        command_line = str(process.get("CommandLine") or "")
        marker = next(
            (candidate for candidate in SIBLING_MARKERS if candidate in command_line),
            None,
        )
        if marker is None:
            continue
        matches.append(
            {
                "pid": pid,
                "name": process.get("Name"),
                "project": marker,
                "command_line": command_line,
            }
        )
    return matches


def sibling_processes() -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    return _matching_sibling_processes(
        _windows_processes(),
        current_pid=os.getpid(),
    )


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
