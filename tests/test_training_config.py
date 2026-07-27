from __future__ import annotations

import json
from pathlib import Path

from src.training.train import latest_checkpoint, load_train_config, write_metrics_jsonl
from src.training.train_all import build_run_plan, run_is_complete, training_command


def test_training_contract_is_compute_matched_and_qlora() -> None:
    config = load_train_config()
    training = config["training"]
    assert training["effective_batch_size"] == (
        training["per_device_train_batch_size"] * training["gradient_accumulation_steps"]
    )
    assert config["quantization"] == {
        "load_in_4bit": True,
        "quant_type": "nf4",
        "double_quant": True,
        "compute_dtype": "bfloat16",
    }
    assert config["lora"]["target_modules"] == "all-linear"
    assert training["warmup_steps"] == 15
    assert len(config["groups"]) == 6


def test_all_run_specs_share_one_config_digest() -> None:
    plans = build_run_plan()
    assert len(plans) == 6
    assert len({plan.shared_config_sha256 for plan in plans}) == 1
    assert len({plan.output_dir for plan in plans}) == 6


def test_latest_checkpoint_selects_highest_numeric_step(tmp_path: Path) -> None:
    (tmp_path / "checkpoint-2").mkdir()
    (tmp_path / "checkpoint-10").mkdir()
    (tmp_path / "checkpoint-bad").mkdir()
    assert latest_checkpoint(tmp_path) == tmp_path / "checkpoint-10"


def test_metrics_jsonl_preserves_trainer_history(tmp_path: Path) -> None:
    history = [{"loss": 1.2, "step": 1}, {"eval_loss": 0.8, "step": 2}]
    write_metrics_jsonl(tmp_path, history)
    rows = [
        json.loads(line)
        for line in (tmp_path / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert rows == history


def test_run_completion_requires_report_and_adapter(tmp_path: Path) -> None:
    (tmp_path / "run_report.json").write_text(
        json.dumps({"status": "completed"}),
        encoding="utf-8",
    )
    assert not run_is_complete(tmp_path)
    (tmp_path / "adapter").mkdir()
    assert run_is_complete(tmp_path)


def test_training_command_is_resumable_and_seeded() -> None:
    plan = build_run_plan()[0]
    command = training_command(
        plan,
        config_path=Path("configs/train.yaml"),
        python_executable="python",
    )
    assert command[:3] == ["python", "-m", "src.training.train"]
    assert "--resume" in command
    assert command[command.index("--seed") + 1] == str(plan.seed)
