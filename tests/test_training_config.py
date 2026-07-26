from __future__ import annotations

from pathlib import Path

from src.training.train import latest_checkpoint, load_train_config
from src.training.train_all import build_run_plan


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
