"""Resumable, unconstrained zero-shot evaluation on real MASSIVE Test."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from src.data.load_massive import decode_example, load_massive_split
from src.data.normalize import parse_annotated_utterance
from src.evaluation.metrics import (
    aggregate_metrics,
    conditional_valid_diagnostics,
    diagnostic_counts,
    per_intent_accuracy,
)
from src.synthetic.checkpoint import JsonlCheckpoint
from src.training.model import load_quantized_causal_model
from src.training.prompt_template import TEMPLATE_VERSION, build_prompt_messages

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "train.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "results" / "m8_zeroshot_predictions.jsonl"
DEFAULT_REPORT_JSON = REPO_ROOT / "reports" / "m8_zeroshot_baseline.json"
DEFAULT_REPORT_MD = REPO_ROOT / "reports" / "m8_zeroshot_baseline.md"


def _gpu_used_mib() -> float | None:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=memory.used",
            "--format=csv,noheader,nounits",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    try:
        return float(completed.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return None


def _expected(example: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_annotated_utterance(example["annot_utt"])
    return {
        "id": example["id"],
        "utt": example["utt"],
        "intent": example["intent"],
        "slots": [{"type": slot_type, "value": value} for slot_type, value in parsed.slots],
    }


def _write_report(
    records: list[dict[str, Any]],
    *,
    target_count: int,
    max_new_tokens: int,
    report_json: Path,
    report_markdown: Path,
    evaluation_name: str = "M8 Zero-shot Baseline",
    evaluation_mode: str = "zero_shot",
    label_catalog_included: bool = True,
    adapter_dir: Path | None = None,
    group: str | None = None,
    seed: int | None = None,
    model_id: str = "google/gemma-4-E4B-it",
    text_only_class: str = "Gemma4ForCausalLM",
) -> None:
    metrics = aggregate_metrics(
        [record["raw_prediction"] for record in records],
        [record["expected"] for record in records],
    )
    raw_predictions = [record["raw_prediction"] for record in records]
    expected_rows = [record["expected"] for record in records]
    conditional_valid = conditional_valid_diagnostics(raw_predictions, expected_rows)
    wall_seconds = sum(record["wall_seconds"] for record in records)
    output_tokens = sum(record["output_tokens"] for record in records)
    sorted_token_counts = sorted(record["output_tokens"] for record in records)

    def percentile(fraction: float) -> int:
        index = round(fraction * (len(sorted_token_counts) - 1))
        return sorted_token_counts[index]

    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model_id,
        "text_only_class": text_only_class,
        "quantization": "NF4 double-quant, bf16 compute",
        "prompt_template_version": TEMPLATE_VERSION,
        "evaluation_mode": evaluation_mode,
        "label_catalog_included": label_catalog_included,
        "zero_shot_prompt_includes_label_catalog": (
            label_catalog_included if evaluation_mode == "zero_shot" else False
        ),
        "adapter_dir": str(adapter_dir) if adapter_dir is not None else None,
        "group": group,
        "seed": seed,
        "constrained_decoding": False,
        "completed": len(records),
        "target": target_count,
        "wall_seconds": wall_seconds,
        "timing_basis": "sum of model.generate batch elapsed; excludes model loading",
        "output_tokens": output_tokens,
        "output_tokens_per_second": output_tokens / wall_seconds if wall_seconds else 0.0,
        "output_token_distribution": {
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
            "maximum": sorted_token_counts[-1],
            "max_new_tokens": max_new_tokens,
            "at_generation_limit": sum(count >= max_new_tokens for count in sorted_token_counts),
        },
        "peak_device_wide_gpu_memory_mib": max(
            (
                record["gpu_memory_mib"]
                for record in records
                if record["gpu_memory_mib"] is not None
            ),
            default=None,
        ),
        "gpu_memory_measurement": (
            "nvidia-smi device-wide memory; concurrent project workloads may contribute"
        ),
        "metrics": metrics,
        "parser_outcomes": diagnostic_counts(raw_predictions),
        "conditional_on_strict_valid_json": conditional_valid,
        "per_intent": per_intent_accuracy(raw_predictions, expected_rows),
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_markdown.write_text(
        "\n".join(
            [
                f"# {evaluation_name}",
                "",
                f"- Completed: {len(records)}/{target_count}",
                f"- Model: `{model_id}` via text-only `{text_only_class}`",
                (
                    f"- Adapter: `{adapter_dir}` (group `{group}`, seed `{seed}`)"
                    if adapter_dir is not None
                    else "- Adapter: none (zero-shot baseline)"
                ),
                "- Quantization: NF4 + double quant, bf16 compute",
                f"- Prompt template: `{TEMPLATE_VERSION}`; "
                f"label catalog {'included' if label_catalog_included else 'not included'}",
                "- Constrained decoding: **disabled**",
                f"- JSON-valid: {metrics['json_valid_rate']:.2%}",
                f"- Intent accuracy: {metrics['intent_accuracy']:.2%}",
                f"- Intent macro-F1: {metrics['intent_macro_f1']:.2%}",
                f"- Slot micro-F1: {metrics['slot_micro_f1']:.2%}",
                f"- Exact match: {metrics['exact_match']:.2%}",
                f"- Parser outcomes: {diagnostic_counts(raw_predictions)}",
                "- Diagnostic intent accuracy among strict-valid rows only: "
                f"{conditional_valid['intent_accuracy']:.2%} "
                f"({conditional_valid['intent_correct']}/{conditional_valid['valid_rows']}); "
                "this is not a primary metric",
                "- Output tokens: "
                f"P50 {percentile(0.50)}, P95 {percentile(0.95)}, "
                f"P99 {percentile(0.99)}, max {sorted_token_counts[-1]}; "
                f"{sum(count >= max_new_tokens for count in sorted_token_counts)} "
                "rows reached the generation limit",
                f"- Summed generation time (model load excluded): {wall_seconds:.2f} s",
                "",
                "> JSON-invalid rows remain in every denominator.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> None:
    """Import torch/Transformers lazily; the current Windows blocker stays isolated."""
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    dataset = load_massive_split("test", download=False)
    target_count = len(dataset) if args.limit is None else min(args.limit, len(dataset))
    checkpoint = JsonlCheckpoint(args.output)
    existing = checkpoint.load()
    missing = [index for index in range(target_count) if index not in existing]
    if args.report_only:
        if missing:
            raise RuntimeError(
                f"Cannot report incomplete checkpoint: {len(existing)}/{target_count}"
            )
        records = [existing[index] for index in range(target_count)]
        _write_report(
            records,
            target_count=target_count,
            max_new_tokens=int(config["inference"]["max_new_tokens"]),
            report_json=args.report_json,
            report_markdown=args.report_markdown,
            model_id=config["model"]["hub_id"],
            text_only_class=config["model"]["class"],
        )
        return

    import torch
    from transformers import AutoTokenizer, BitsAndBytesConfig

    model_path = REPO_ROOT / config["model"]["local_path"]
    quant = config["quantization"]
    inference = config["inference"]

    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        local_files_only=True,
        trust_remote_code=False,
    )
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=quant["load_in_4bit"],
        bnb_4bit_quant_type=quant["quant_type"],
        bnb_4bit_use_double_quant=quant["double_quant"],
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = load_quantized_causal_model(
        model_path,
        model_class=config["model"]["class"],
        quantization_config=quantization_config,
        dtype=torch.bfloat16,
    )
    model.eval()

    tokenizer.padding_side = "left"
    batch_size = int(inference["batch_size"])
    gpu_memory_mib: float | None = None
    for batch_number, batch_start in enumerate(range(0, len(missing), batch_size)):
        indices = missing[batch_start : batch_start + batch_size]
        expected_batch = [_expected(decode_example(dataset, index)) for index in indices]
        conversations = [
            build_prompt_messages(expected["utt"], zero_shot=True) for expected in expected_batch
        ]
        inputs = tokenizer.apply_chat_template(
            conversations,
            tokenize=True,
            padding=True,
            add_generation_prompt=True,
            enable_thinking=False,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device)
        input_length = inputs["input_ids"].shape[-1]
        started = time.perf_counter()
        with torch.inference_mode():
            outputs = model.generate(
                **inputs,
                max_new_tokens=inference["max_new_tokens"],
                do_sample=False,
            )
        elapsed = time.perf_counter() - started
        if gpu_memory_mib is None or batch_number % 25 == 0:
            gpu_memory_mib = _gpu_used_mib()
        per_record_elapsed = elapsed / len(indices)
        for index, expected, output in zip(indices, expected_batch, outputs, strict=True):
            generated = output[input_length:]
            raw_prediction = tokenizer.decode(generated, skip_special_tokens=True)
            output_tokens = int(generated.ne(tokenizer.pad_token_id).sum().detach().cpu())
            checkpoint.append(
                {
                    "generation_index": index,
                    "expected": expected,
                    "raw_prediction": raw_prediction,
                    "wall_seconds": per_record_elapsed,
                    "output_tokens": output_tokens,
                    "gpu_memory_mib": gpu_memory_mib,
                }
            )
        completed_count = len(existing) + batch_start + len(indices)
        if completed_count % 50 == 0 or completed_count == target_count:
            print(f"checkpointed {completed_count}/{target_count}")
    checkpoint.compact()
    records = [checkpoint.load()[index] for index in range(target_count)]
    _write_report(
        records,
        target_count=target_count,
        max_new_tokens=int(inference["max_new_tokens"]),
        report_json=args.report_json,
        report_markdown=args.report_markdown,
        model_id=config["model"]["hub_id"],
        text_only_class=config["model"]["class"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-markdown", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
