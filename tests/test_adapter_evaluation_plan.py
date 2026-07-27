import json
from pathlib import Path

from src.evaluation.eval_all import (
    EvalSpec,
    build_eval_plan,
    evaluation_command,
    evaluation_is_complete,
)
from src.training.train import DEFAULT_CONFIG


def test_eval_plan_covers_all_primary_groups() -> None:
    plan = build_eval_plan()
    assert [spec.group for spec in plan] == [
        "real_only",
        "real_std_aug",
        "real_syn_unfiltered_full",
        "real_syn_unfiltered_eqn",
        "real_syn_filtered",
        "full_real",
    ]
    assert all(spec.seed == 42 for spec in plan)


def test_evaluation_command_uses_adapter_and_checkpoint_output(tmp_path: Path) -> None:
    spec = EvalSpec(
        group="real_only",
        seed=42,
        adapter_dir=tmp_path / "adapter",
        output=tmp_path / "predictions.jsonl",
        report_json=tmp_path / "report.json",
        report_markdown=tmp_path / "report.md",
    )
    command = evaluation_command(
        spec,
        config_path=DEFAULT_CONFIG,
        python_executable="python",
        report_only=True,
    )
    assert command[:3] == ["python", "-m", "src.evaluation.run_adapter"]
    assert str(spec.adapter_dir) in command
    assert str(spec.output) in command
    assert command[-1] == "--report-only"


def test_evaluation_completion_requires_matching_full_report(tmp_path: Path) -> None:
    spec = EvalSpec(
        group="real_only",
        seed=42,
        adapter_dir=tmp_path / "adapter",
        output=tmp_path / "predictions.jsonl",
        report_json=tmp_path / "report.json",
        report_markdown=tmp_path / "report.md",
    )
    spec.report_json.write_text(
        json.dumps(
            {
                "evaluation_mode": "trained_adapter",
                "group": "real_only",
                "seed": 42,
                "completed": 2974,
                "target": 2974,
            }
        ),
        encoding="utf-8",
    )
    assert evaluation_is_complete(spec)
