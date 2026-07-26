"""Resumable, unconstrained Gemma 4 zero-shot evaluation on real MASSIVE Test."""

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
from src.evaluation.metrics import aggregate_metrics
from src.synthetic.checkpoint import JsonlCheckpoint
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
    report_json: Path,
    report_markdown: Path,
) -> None:
    metrics = aggregate_metrics(
        [record["raw_prediction"] for record in records],
        [record["expected"] for record in records],
    )
    wall_seconds = sum(record["wall_seconds"] for record in records)
    output_tokens = sum(record["output_tokens"] for record in records)
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "google/gemma-4-E4B-it",
        "text_only_class": "Gemma4ForCausalLM",
        "quantization": "NF4 double-quant, bf16 compute",
        "prompt_template_version": TEMPLATE_VERSION,
        "zero_shot_prompt_includes_label_catalog": True,
        "constrained_decoding": False,
        "completed": len(records),
        "target": target_count,
        "wall_seconds": wall_seconds,
        "output_tokens": output_tokens,
        "output_tokens_per_second": output_tokens / wall_seconds if wall_seconds else 0.0,
        "peak_gpu_memory_mib": max(
            (
                record["gpu_memory_mib"]
                for record in records
                if record["gpu_memory_mib"] is not None
            ),
            default=None,
        ),
        "metrics": metrics,
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_markdown.write_text(
        "\n".join(
            [
                "# M8 Zero-shot Baseline",
                "",
                f"- Completed: {len(records)}/{target_count}",
                "- Model: `google/gemma-4-E4B-it` via text-only `Gemma4ForCausalLM`",
                "- Quantization: NF4 + double quant, bf16 compute",
                f"- Prompt template: `{TEMPLATE_VERSION}`; zero-shot label catalog included",
                "- Constrained decoding: **disabled**",
                f"- JSON-valid: {metrics['json_valid_rate']:.2%}",
                f"- Intent accuracy: {metrics['intent_accuracy']:.2%}",
                f"- Intent macro-F1: {metrics['intent_macro_f1']:.2%}",
                f"- Slot micro-F1: {metrics['slot_micro_f1']:.2%}",
                f"- Exact match: {metrics['exact_match']:.2%}",
                f"- Wall-clock: {wall_seconds:.2f} s",
                "",
                "> JSON-invalid rows remain in every denominator.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> None:
    """Import torch/Transformers lazily; the current Windows blocker stays isolated."""
    import torch
    from transformers import AutoTokenizer, BitsAndBytesConfig, Gemma4ForCausalLM

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    model_path = REPO_ROOT / config["model"]["local_path"]
    quant = config["quantization"]
    inference = config["inference"]
    dataset = load_massive_split("test", download=False)
    target_count = len(dataset) if args.limit is None else min(args.limit, len(dataset))
    checkpoint = JsonlCheckpoint(args.output)
    existing = checkpoint.load()
    missing = [index for index in range(target_count) if index not in existing]

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=quant["load_in_4bit"],
        bnb_4bit_quant_type=quant["quant_type"],
        bnb_4bit_use_double_quant=quant["double_quant"],
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = Gemma4ForCausalLM.from_pretrained(
        model_path,
        quantization_config=quantization_config,
        dtype=torch.bfloat16,
        device_map={"": 0},
    )
    model.eval()

    for completed_offset, index in enumerate(missing, start=1):
        expected = _expected(decode_example(dataset, index))
        messages = build_prompt_messages(expected["utt"], zero_shot=True)
        inputs = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
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
        generated = outputs[0][input_length:]
        raw_prediction = tokenizer.decode(generated, skip_special_tokens=True)
        checkpoint.append(
            {
                "generation_index": index,
                "expected": expected,
                "raw_prediction": raw_prediction,
                "wall_seconds": elapsed,
                "output_tokens": int(generated.shape[-1]),
                "gpu_memory_mib": _gpu_used_mib(),
            }
        )
        completed_count = len(existing) + completed_offset
        if completed_count % 50 == 0:
            print(f"checkpointed {completed_count}/{target_count}")
    checkpoint.compact()
    records = [checkpoint.load()[index] for index in range(target_count)]
    _write_report(
        records,
        target_count=target_count,
        report_json=args.report_json,
        report_markdown=args.report_markdown,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-markdown", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
