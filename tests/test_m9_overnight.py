from __future__ import annotations

from src.training.overnight import build_checks, parse_gpu_snapshot


def _observations() -> dict[str, object]:
    return {
        "contributor_ok": True,
        "contributor_observed": "kuotunyu only",
        "unexpected_changes": [],
        "model_ok": True,
        "model_observed": "matched",
        "data_ok": True,
        "data_observed": "six groups matched",
        "resume_ok": True,
        "resume_observed": "passed at step 2",
        "gpu": {
            "name": "NVIDIA GeForce RTX 4090",
            "memory_total_mib": 24564,
            "memory_used_mib": 1400,
            "utilization_percent": 2,
            "temperature_c": 42,
        },
        "disk_free_gib": 100.0,
    }


def test_parse_gpu_snapshot() -> None:
    payload = parse_gpu_snapshot("NVIDIA GeForce RTX 4090, 24564, 1333, 18, 44\n")
    assert payload["memory_total_mib"] == 24564
    assert payload["memory_used_mib"] == 1333
    assert payload["temperature_c"] == 44


def test_overnight_checks_pass_for_ready_machine() -> None:
    checks = build_checks(**_observations())  # type: ignore[arg-type]
    assert all(check.passed for check in checks)


def test_overnight_checks_block_busy_gpu_and_unexpected_changes() -> None:
    observations = _observations()
    observations["unexpected_changes"] = [" M src/training/train.py"]
    observations["gpu"] = {
        **observations["gpu"],  # type: ignore[arg-type]
        "memory_used_mib": 18_000,
    }
    checks = build_checks(**observations)  # type: ignore[arg-type]
    failures = {check.name for check in checks if not check.passed}
    assert failures == {"worktree", "gpu_available"}
