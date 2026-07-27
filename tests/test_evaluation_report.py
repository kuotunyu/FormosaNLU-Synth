import json
from pathlib import Path

import pytest

from src.evaluation.report import GROUPS, METRICS, build_results, gap_closed


def _metrics(value: float) -> dict[str, float]:
    return {metric: value for metric in METRICS}


def _per_intent(value: float) -> dict:
    return {"alarm_set": {"correct": 1, "total": 2, "accuracy": value}}


def test_gap_closed_marks_small_denominator_unreliable() -> None:
    result = gap_closed(0.51, real_only=0.50, full_real=0.505)
    assert result["gap_closed_percent"] is None
    assert result["reliable"] is False


def test_build_results_is_pending_without_trained_reports(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "m8_zeroshot_baseline.json").write_text(
        json.dumps(
            {
                "metrics": _metrics(0.1),
                "per_intent": _per_intent(0.1),
                "completed": 10,
                "wall_seconds": 5,
            }
        ),
        encoding="utf-8",
    )
    payload = build_results(repo_root=tmp_path)
    assert payload["status"] == "pending"
    assert payload["missing_groups"] == list(GROUPS[1:])


def test_build_results_computes_gaps_and_intent_movement(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    (reports / "m9").mkdir(parents=True)
    (reports / "m8_zeroshot_baseline.json").write_text(
        json.dumps(
            {
                "metrics": _metrics(0.1),
                "per_intent": _per_intent(0.1),
                "completed": 10,
                "wall_seconds": 5,
            }
        ),
        encoding="utf-8",
    )
    values = {
        "real_only": 0.2,
        "real_std_aug": 0.3,
        "real_syn_unfiltered_full": 0.35,
        "real_syn_unfiltered_eqn": 0.4,
        "real_syn_filtered": 0.5,
        "full_real": 0.6,
    }
    for group, value in values.items():
        (reports / "m9" / f"{group}_seed_42.json").write_text(
            json.dumps(
                {
                    "metrics": _metrics(value),
                    "per_intent": _per_intent(value),
                    "completed": 10,
                    "wall_seconds": 5,
                }
            ),
            encoding="utf-8",
        )
        run_dir = tmp_path / "runs" / group / "seed_42"
        run_dir.mkdir(parents=True)
        train_examples = 11514 if group == "full_real" else 4936
        if group == "real_only":
            train_examples = 1176
        (run_dir / "run_report.json").write_text(
            json.dumps(
                {
                    "effective_batch_size": 16,
                    "train_examples": train_examples,
                    "best_model_checkpoint": str(run_dir / "checkpoint-100"),
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "metrics.jsonl").write_text(
            json.dumps({"step": 100, "eval_loss": 1.0, "epoch": 2.0}) + "\n",
            encoding="utf-8",
        )
    payload = build_results(repo_root=tmp_path)
    assert payload["status"] == "complete"
    assert payload["gap_closed"]["real_syn_filtered"]["exact_match"][
        "gap_closed_percent"
    ] == pytest.approx(75.0)
    assert payload["per_intent_movement"][0]["absolute_delta"] == pytest.approx(0.3)
