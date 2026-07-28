"""Resumable trained-adapter inference on the frozen 8,922-row robustness probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from src.evaluation.metrics import aggregate_metrics, diagnostic_counts
from src.evaluation.run_zeroshot import _gpu_used_mib
from src.synthetic.checkpoint import JsonlCheckpoint
from src.training.model import load_quantized_text_model
from src.training.prompt_template import build_prompt_messages
from src.training.train import DEFAULT_CONFIG, REPO_ROOT

DEFAULT_INPUT = REPO_ROOT / "data" / "evaluation" / "robustness_probe.jsonl"
DEFAULT_MANIFEST = REPO_ROOT / "reports" / "m10_probe_manifest.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_probe_rows(
    input_path: Path,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> list[dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "ready_not_evaluated":
        raise ValueError("Robustness manifest is not in the frozen ready state")
    if _sha256(input_path) != manifest["output_sha256"]:
        raise AssertionError("Robustness probe SHA-256 does not match its manifest")
    rows = [
        json.loads(line)
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != manifest["probe_count"]:
        raise AssertionError(
            f"Probe row count {len(rows)} != {manifest['probe_count']}"
        )
    if any(not row.get("evaluation_only") for row in rows):
        raise AssertionError("Every robustness row must be evaluation-only")
    return rows


def _expected(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "utt": row["utt"],
        "intent": row["intent"],
        "slots": row["slots"],
        "probe_kind": row["probe_kind"],
        "source_test_id": row["source_test_id"],
    }


def build_probe_report(
    *,
    records: list[dict[str, Any]],
    group: str,
    seed: int,
    adapter_dir: Path,
    primary_report: dict[str, Any],
) -> dict[str, Any]:
    expected = [record["expected"] for record in records]
    predictions = [record["raw_prediction"] for record in records]
    kinds = sorted({row["probe_kind"] for row in expected})
    by_kind: dict[str, Any] = {}
    delta_by_kind: dict[str, Any] = {}
    for kind in kinds:
        indices = [
            index for index, row in enumerate(expected) if row["probe_kind"] == kind
        ]
        metrics = aggregate_metrics(
            [predictions[index] for index in indices],
            [expected[index] for index in indices],
        )
        by_kind[kind] = metrics
        delta_by_kind[kind] = {
            metric: metrics[metric] - float(primary_report["metrics"][metric])
            for metric in metrics
            if metric != "samples"
        }
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "evaluation_mode": "trained_adapter_robustness_probe",
        "group": group,
        "seed": seed,
        "adapter_dir": str(adapter_dir),
        "target": len(records),
        "completed": len(records),
        "probe_kind_counts": dict(
            sorted(Counter(row["probe_kind"] for row in expected).items())
        ),
        "metrics": aggregate_metrics(predictions, expected),
        "metrics_by_probe_kind": by_kind,
        "primary_test_metrics": primary_report["metrics"],
        "delta_vs_primary_by_probe_kind": delta_by_kind,
        "diagnostics": diagnostic_counts(predictions),
        "performance": {
            "wall_seconds_sum": sum(float(row["wall_seconds"]) for row in records),
            "output_tokens": sum(int(row["output_tokens"]) for row in records),
            "peak_observed_gpu_memory_mib": max(
                (
                    float(row["gpu_memory_mib"])
                    for row in records
                    if row.get("gpu_memory_mib") is not None
                ),
                default=None,
            ),
        },
        "evaluation_only": True,
    }


def _write_report(
    payload: dict[str, Any],
    *,
    report_json: Path,
    report_markdown: Path,
) -> None:
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_markdown.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# M10 robustness — {payload['group']} seed {payload['seed']}",
        "",
        f"Status: **{payload['status']}**; rows: {payload['completed']:,}",
        "",
        "| Probe | Intent acc | Slot F1 | Exact match | JSON valid |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for kind, metrics in payload["metrics_by_probe_kind"].items():
        lines.append(
            f"| `{kind}` | {metrics['intent_accuracy']:.2%} | "
            f"{metrics['slot_micro_f1']:.2%} | {metrics['exact_match']:.2%} | "
            f"{metrics['json_valid_rate']:.2%} |"
        )
    lines.extend(
        [
            "",
            "Deltas are computed against the same adapter on untouched real Test.",
            "",
        ]
    )
    report_markdown.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    probe_rows = load_probe_rows(args.input, args.manifest)
    target_count = (
        len(probe_rows) if args.limit is None else min(args.limit, len(probe_rows))
    )
    probe_rows = probe_rows[:target_count]
    checkpoint = JsonlCheckpoint(args.output)
    existing = checkpoint.load()
    missing = [index for index in range(target_count) if index not in existing]
    primary_report = json.loads(args.primary_report.read_text(encoding="utf-8"))
    if (
        primary_report.get("group") != args.group
        or primary_report.get("seed") != args.seed
        or primary_report.get("completed") != primary_report.get("target")
    ):
        raise ValueError("Primary Test report does not match the requested adapter")
    if args.report_only:
        if missing:
            raise RuntimeError(
                f"Cannot report incomplete probe: {len(existing)}/{target_count}"
            )
        payload = build_probe_report(
            records=[existing[index] for index in range(target_count)],
            group=args.group,
            seed=args.seed,
            adapter_dir=args.adapter_dir,
            primary_report=primary_report,
        )
        _write_report(
            payload,
            report_json=args.report_json,
            report_markdown=args.report_markdown,
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
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    tokenizer.padding_side = "left"
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=quant["load_in_4bit"],
        bnb_4bit_quant_type=quant["quant_type"],
        bnb_4bit_use_double_quant=quant["double_quant"],
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    base_model = load_quantized_text_model(
        model_path,
        quantization_config=quantization_config,
        dtype=torch.bfloat16,
    )
    model = PeftModel.from_pretrained(base_model, args.adapter_dir, is_trainable=False)
    model.eval()

    batch_size = int(inference["batch_size"])
    gpu_memory_mib: float | None = None
    for batch_number, batch_start in enumerate(range(0, len(missing), batch_size)):
        indices = missing[batch_start : batch_start + batch_size]
        expected_batch = [_expected(probe_rows[index]) for index in indices]
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
                    "wall_seconds": elapsed / len(indices),
                    "output_tokens": int(
                        generated.ne(tokenizer.pad_token_id).sum().detach().cpu()
                    ),
                    "gpu_memory_mib": gpu_memory_mib,
                }
            )
        completed_count = len(existing) + batch_start + len(indices)
        if completed_count % 100 == 0 or completed_count == target_count:
            print(f"checkpointed {completed_count}/{target_count}", flush=True)
    checkpoint.compact()
    completed = checkpoint.load()
    payload = build_probe_report(
        records=[completed[index] for index in range(target_count)],
        group=args.group,
        seed=args.seed,
        adapter_dir=args.adapter_dir,
        primary_report=primary_report,
    )
    _write_report(
        payload,
        report_json=args.report_json,
        report_markdown=args.report_markdown,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--adapter-dir", required=True, type=Path)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--primary-report", required=True, type=Path)
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
