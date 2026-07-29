from __future__ import annotations

from src import gpu_safety


def test_sibling_matching_ignores_current_ancestors_and_gui_viewers() -> None:
    processes = [
        {
            "ProcessId": 100,
            "ParentProcessId": 0,
            "Name": "powershell.exe",
            "CommandLine": "inspect C:\\work\\1_DefectForge",
        },
        {
            "ProcessId": 200,
            "ParentProcessId": 100,
            "Name": "python.exe",
            "CommandLine": "python -m scripts.m15_phi4mini",
        },
        {
            "ProcessId": 300,
            "ParentProcessId": 0,
            "Name": "Photos.exe",
            "CommandLine": "Photos.exe C:\\work\\2_SafeSynth\\plot.png",
        },
    ]

    assert (
        gpu_safety._matching_sibling_processes(processes, current_pid=200) == []
    )


def test_sibling_matching_keeps_compute_processes_from_other_trees() -> None:
    processes = [
        {
            "ProcessId": 100,
            "ParentProcessId": 0,
            "Name": "powershell.exe",
            "CommandLine": "Codex wrapper",
        },
        {
            "ProcessId": 200,
            "ParentProcessId": 100,
            "Name": "python.exe",
            "CommandLine": "python -m scripts.m15_phi4mini",
        },
        {
            "ProcessId": 400,
            "ParentProcessId": 0,
            "Name": "python.exe",
            "CommandLine": "python C:\\work\\2_SafeSynth\\train.py",
        },
    ]

    assert gpu_safety._matching_sibling_processes(
        processes,
        current_pid=200,
    ) == [
        {
            "pid": 400,
            "name": "python.exe",
            "project": "2_SafeSynth",
            "command_line": "python C:\\work\\2_SafeSynth\\train.py",
        }
    ]


def test_safety_status_requires_idle_gpu_and_absent_siblings(monkeypatch) -> None:
    monkeypatch.setattr(
        gpu_safety,
        "gpu_snapshot",
        lambda: {
            "name": "RTX 4090",
            "memory_total_mib": 24_564,
            "memory_used_mib": 1_000,
            "utilization_percent": 2,
            "temperature_c": 40,
        },
    )
    monkeypatch.setattr(gpu_safety, "sibling_processes", lambda: [])
    assert gpu_safety.safety_status()["safe"] is True

    monkeypatch.setattr(
        gpu_safety,
        "sibling_processes",
        lambda: [{"pid": 1, "project": "1_DefectForge"}],
    )
    status = gpu_safety.safety_status()
    assert status["safe"] is False
    assert status["checks"]["siblings_absent"] is False
