from __future__ import annotations

from pathlib import Path

import src.training.overnight as overnight
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


def _pipeline_paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "training_batch_report": tmp_path / "training.json",
        "evaluation_batch_report": tmp_path / "evaluation.json",
        "pipeline_report": tmp_path / "pipeline.json",
        "m10_json": tmp_path / "m10.json",
        "m10_markdown": tmp_path / "m10.md",
    }


def test_pipeline_runs_training_evaluation_and_report(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        overnight,
        "execute_primary_runs",
        lambda **kwargs: {"status": "complete"},
    )
    monkeypatch.setattr(overnight, "build_eval_plan", lambda config: ["six-runs"])
    monkeypatch.setattr(
        overnight,
        "execute_evaluations",
        lambda specs, **kwargs: {"status": "complete", "specs": specs},
    )
    monkeypatch.setattr(
        overnight,
        "build_results",
        lambda **kwargs: {
            "status": "complete",
            "missing_groups": [],
        },
    )
    monkeypatch.setattr(overnight, "render_markdown", lambda payload: "# complete\n")

    result = overnight.execute_overnight_pipeline(**_pipeline_paths(tmp_path))

    assert result["status"] == "complete"
    assert result["evaluation"]["specs"] == ["six-runs"]
    assert (tmp_path / "m10.md").read_text(encoding="utf-8") == "# complete\n"


def test_pipeline_stops_after_training_failure(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        overnight,
        "execute_primary_runs",
        lambda **kwargs: {"status": "complete_with_failures"},
    )
    monkeypatch.setattr(
        overnight,
        "execute_evaluations",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("evaluation must not start")
        ),
    )

    result = overnight.execute_overnight_pipeline(**_pipeline_paths(tmp_path))

    assert result["status"] == "training_failed"
    assert result["evaluation"] is None


def test_pipeline_stops_after_evaluation_failure(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        overnight,
        "execute_primary_runs",
        lambda **kwargs: {"status": "complete"},
    )
    monkeypatch.setattr(overnight, "build_eval_plan", lambda config: ["six-runs"])
    monkeypatch.setattr(
        overnight,
        "execute_evaluations",
        lambda specs, **kwargs: {"status": "complete_with_failures"},
    )
    monkeypatch.setattr(
        overnight,
        "build_results",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("M10 report must not be built")
        ),
    )

    result = overnight.execute_overnight_pipeline(**_pipeline_paths(tmp_path))

    assert result["status"] == "evaluation_failed"
    assert result["m10"] is None
