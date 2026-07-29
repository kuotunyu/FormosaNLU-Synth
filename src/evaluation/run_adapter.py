"""Resumable evaluation of one trained adapter on real MASSIVE Test."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import yaml

from src.data.load_massive import decode_example, load_massive_split
from src.evaluation.run_zeroshot import _expected, _gpu_used_mib, _write_report
from src.synthetic.checkpoint import JsonlCheckpoint
from src.training.model import load_quantized_causal_model
from src.training.prompt_template import build_prompt_messages
from src.training.train import DEFAULT_CONFIG, REPO_ROOT


def run(args: argparse.Namespace) -> None:
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    dataset = load_massive_split("test", download=False)
    target_count = len(dataset) if args.limit is None else min(args.limit, len(dataset))
    checkpoint = JsonlCheckpoint(args.output)
    existing = checkpoint.load()
    missing = [index for index in range(target_count) if index not in existing]
    report_kwargs = {
        "target_count": target_count,
        "max_new_tokens": int(config["inference"]["max_new_tokens"]),
        "report_json": args.report_json,
        "report_markdown": args.report_markdown,
        "evaluation_name": f"M9 Adapter Evaluation — {args.group} seed {args.seed}",
        "evaluation_mode": "trained_adapter",
        "label_catalog_included": False,
        "adapter_dir": args.adapter_dir,
        "group": args.group,
        "seed": args.seed,
        "model_id": config["model"]["hub_id"],
        "text_only_class": config["model"]["class"],
    }
    if args.report_only:
        if missing:
            raise RuntimeError(
                f"Cannot report incomplete checkpoint: {len(existing)}/{target_count}"
            )
        _write_report(
            [existing[index] for index in range(target_count)],
            **report_kwargs,
        )
        return
    if not args.adapter_dir.is_dir():
        raise FileNotFoundError(f"Adapter directory not found: {args.adapter_dir}")

    import torch
    from peft import PeftModel
    from transformers import AutoTokenizer, BitsAndBytesConfig

    model_path = REPO_ROOT / config["model"]["local_path"]
    quant = config["quantization"]
    inference = config["inference"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        local_files_only=True,
        trust_remote_code=False,
    )
    tokenizer.padding_side = "left"
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=quant["load_in_4bit"],
        bnb_4bit_quant_type=quant["quant_type"],
        bnb_4bit_use_double_quant=quant["double_quant"],
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    base_model = load_quantized_causal_model(
        model_path,
        model_class=config["model"]["class"],
        quantization_config=quantization_config,
        dtype=torch.bfloat16,
    )
    model = PeftModel.from_pretrained(
        base_model,
        args.adapter_dir,
        is_trainable=False,
    )
    model.eval()

    batch_size = int(inference["batch_size"])
    gpu_memory_mib: float | None = None
    for batch_number, batch_start in enumerate(range(0, len(missing), batch_size)):
        indices = missing[batch_start : batch_start + batch_size]
        expected_batch = [_expected(decode_example(dataset, index)) for index in indices]
        conversations = [
            build_prompt_messages(expected["utt"], zero_shot=False)
            for expected in expected_batch
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
            checkpoint.append(
                {
                    "generation_index": index,
                    "expected": expected,
                    "raw_prediction": tokenizer.decode(
                        generated,
                        skip_special_tokens=True,
                    ),
                    "wall_seconds": per_record_elapsed,
                    "output_tokens": int(
                        generated.ne(tokenizer.pad_token_id).sum().detach().cpu()
                    ),
                    "gpu_memory_mib": gpu_memory_mib,
                }
            )
        completed_count = len(existing) + batch_start + len(indices)
        if completed_count % 50 == 0 or completed_count == target_count:
            print(f"checkpointed {completed_count}/{target_count}")
    checkpoint.compact()
    completed = checkpoint.load()
    _write_report(
        [completed[index] for index in range(target_count)],
        **report_kwargs,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--adapter-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report-json", required=True, type=Path)
    parser.add_argument("--report-markdown", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
