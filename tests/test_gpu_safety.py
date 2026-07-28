from __future__ import annotations

from src import gpu_safety


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
