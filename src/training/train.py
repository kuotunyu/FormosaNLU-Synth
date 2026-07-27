"""Single-group Gemma 4 QLoRA training entry point."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import yaml

from src.training.data import (
    group_examples,
    prompt_completion_rows,
    validation_examples,
)
from src.training.model import load_quantized_text_model

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "train.yaml"


def load_train_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def latest_checkpoint(output_dir: Path) -> Path | None:
    checkpoints = []
    if output_dir.exists():
        for path in output_dir.glob("checkpoint-*"):
            try:
                step = int(path.name.removeprefix("checkpoint-"))
            except ValueError:
                continue
            checkpoints.append((step, path))
    return max(checkpoints, default=(0, None))[1]


def _git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode == 0:
        return completed.stdout.strip()
    return os.environ.get("FORMOSANLU_SOURCE_COMMIT", "unknown")


def _package_versions() -> dict[str, str]:
    packages = (
        "torch",
        "transformers",
        "accelerate",
        "peft",
        "trl",
        "bitsandbytes",
    )
    resolved: dict[str, str] = {}
    for package in packages:
        try:
            resolved[package] = version(package)
        except PackageNotFoundError:
            resolved[package] = "missing"
    return resolved


def _gpu_environment() -> str:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total",
            "--format=csv,noheader,nounits",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def _write_run_metadata(
    output_dir: Path,
    config: dict[str, Any],
    group: str,
    seed: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = {**config, "run": {"group": group, "seed": seed}}
    (output_dir / "config.snapshot.yaml").write_text(
        yaml.safe_dump(snapshot, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    environment = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "commit": _git_commit(),
        "packages": _package_versions(),
        "gpu": _gpu_environment(),
    }
    (output_dir / "env.json").write_text(
        json.dumps(environment, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_metrics_jsonl(output_dir: Path, log_history: list[dict[str, Any]]) -> None:
    """Persist Trainer history as the machine-readable metric source of truth."""
    with (output_dir / "metrics.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for entry in log_history:
            handle.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")


def train_group(
    *,
    group: str,
    config_path: Path,
    output_dir: Path,
    smoke_test: bool,
    resume: bool,
    seed: int | None = None,
    max_steps_override: int | None = None,
) -> None:
    """Load heavy ML libraries lazily so CPU-only validation can still run."""
    import torch
    from datasets import Dataset
    from peft import LoraConfig, prepare_model_for_kbit_training
    from transformers import AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    config = load_train_config(config_path)
    model_config = config["model"]
    training = config["training"]
    quantization = config["quantization"]
    lora = config["lora"]
    if group not in config["groups"]:
        raise ValueError(f"Unknown training group: {group}")
    run_seed = int(training["seed"] if seed is None else seed)
    if max_steps_override is not None and not smoke_test:
        raise ValueError("max_steps_override is restricted to smoke tests")
    if max_steps_override is not None and max_steps_override <= 0:
        raise ValueError("max_steps_override must be positive")
    model_path = REPO_ROOT / model_config["local_path"]
    if not model_path.exists():
        raise FileNotFoundError(f"Local model is missing: {model_path}")
    _write_run_metadata(output_dir, config, group, run_seed)

    train_examples = group_examples(group, seed=run_seed)
    eval_examples = validation_examples(limit=8 if smoke_test else None)
    if smoke_test:
        train_examples = train_examples[:8]
    train_dataset = Dataset.from_list(prompt_completion_rows(train_examples))
    eval_dataset = Dataset.from_list(prompt_completion_rows(eval_examples))

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    tokenizer.padding_side = "right"
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=quantization["load_in_4bit"],
        bnb_4bit_quant_type=quantization["quant_type"],
        bnb_4bit_use_double_quant=quantization["double_quant"],
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    torch.cuda.reset_peak_memory_stats()
    model = load_quantized_text_model(
        model_path,
        quantization_config=quantization_config,
        dtype=torch.bfloat16,
    )
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=training["gradient_checkpointing"],
    )
    peft_config = LoraConfig(
        r=lora["rank"],
        lora_alpha=lora["alpha"],
        lora_dropout=lora["dropout"],
        target_modules=lora["target_modules"],
        bias=lora["bias"],
        task_type="CAUSAL_LM",
    )
    max_steps = (
        max_steps_override
        if max_steps_override is not None
        else 1
        if smoke_test
        else training["max_steps"]
    )
    sft_config = SFTConfig(
        output_dir=str(output_dir),
        max_steps=max_steps,
        per_device_train_batch_size=training["per_device_train_batch_size"],
        gradient_accumulation_steps=training["gradient_accumulation_steps"],
        learning_rate=training["learning_rate"],
        lr_scheduler_type=training["scheduler"],
        warmup_steps=training["warmup_steps"],
        max_length=training["max_length"],
        bf16=training["bf16"],
        optim=training["optimizer"],
        gradient_checkpointing=training["gradient_checkpointing"],
        completion_only_loss=training["completion_only_loss"],
        eval_strategy="steps",
        eval_steps=1 if smoke_test else training["eval_steps"],
        save_strategy="steps",
        save_steps=1 if smoke_test else training["save_steps"],
        logging_steps=1 if smoke_test else training["logging_steps"],
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        seed=run_seed,
        data_seed=run_seed,
        report_to="none",
    )
    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    checkpoint = latest_checkpoint(output_dir) if resume else None
    trainable_parameters = sum(
        parameter.numel() for parameter in trainer.model.parameters() if parameter.requires_grad
    )
    total_parameters = sum(parameter.numel() for parameter in trainer.model.parameters())
    training_result = trainer.train(resume_from_checkpoint=str(checkpoint) if checkpoint else None)
    adapter_dir = output_dir / "adapter"
    trainer.save_model(adapter_dir)
    trainer.save_state()
    write_metrics_jsonl(output_dir, trainer.state.log_history)
    torch.cuda.synchronize()
    run_report = {
        "schema_version": 1,
        "status": "completed",
        "smoke_test": smoke_test,
        "group": group,
        "seed": run_seed,
        "train_examples": len(train_examples),
        "eval_examples": len(eval_examples),
        "effective_batch_size": training["effective_batch_size"],
        "max_steps": max_steps,
        "trainable_parameters": trainable_parameters,
        "total_parameters": total_parameters,
        "trainable_percent": 100 * trainable_parameters / total_parameters,
        "peak_gpu_allocated_mib": torch.cuda.max_memory_allocated() / (1024**2),
        "peak_gpu_reserved_mib": torch.cuda.max_memory_reserved() / (1024**2),
        "resumed_from": str(checkpoint) if checkpoint else None,
        "best_model_checkpoint": trainer.state.best_model_checkpoint,
        "global_step": trainer.state.global_step,
        "adapter_dir": str(adapter_dir),
        "metrics": training_result.metrics,
    }
    (output_dir / "run_report.json").write_text(
        json.dumps(run_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--max-steps-override", type=int)
    args = parser.parse_args()
    output_dir = args.output_dir or (
        REPO_ROOT / "runs" / ("smoke" if args.smoke_test else args.group) / "seed_42"
    )
    train_group(
        group=args.group,
        config_path=args.config,
        output_dir=output_dir,
        smoke_test=args.smoke_test,
        resume=args.resume,
        seed=args.seed,
        max_steps_override=args.max_steps_override,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
