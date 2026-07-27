"""Measure BGE-M3 pilot similarity distributions without choosing thresholds."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.data.load_massive import decode_example, load_massive_split
from src.filtering.bge_m3 import BgeM3Backend
from src.filtering.similarity import (
    nearest_nonself_distribution,
    nearest_similarity_distribution,
)
from src.synthetic.planning import load_seed_pool

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PILOT = REPO_ROOT / "data" / "filtered" / "pilot_f1_f4.jsonl"
DEFAULT_MODEL = REPO_ROOT / "data" / "models" / "bge-m3"
DEFAULT_EMBEDDINGS = REPO_ROOT / "data" / "embeddings" / "m5_pilot_bge_m3.npz"
DEFAULT_REPORT = REPO_ROOT / "reports" / "m5_similarity_calibration.json"
DEFAULT_FIGURE = REPO_ROOT / "assets" / "m5_similarity_distributions.png"
QUANTILES = (0, 1, 5, 25, 50, 75, 90, 95, 99, 100)


def _load_pilot(path: Path) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    texts: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            sample = json.loads(line)["sample"]
            ids.append(sample["id"])
            texts.append(sample["utt"])
    return ids, texts


def _load_eval() -> tuple[list[str], list[str]]:
    ids: list[str] = []
    texts: list[str] = []
    for split in ("validation", "test"):
        dataset = load_massive_split(split, download=False)
        for index in range(len(dataset)):
            example = decode_example(dataset, index)
            ids.append(f"{split}:{example['id']}")
            texts.append(example["utt"])
    return ids, texts


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def _summary(values: np.ndarray) -> dict[str, float]:
    measured = np.percentile(values, QUANTILES)
    return {
        f"p{quantile}": float(value) for quantile, value in zip(QUANTILES, measured, strict=True)
    }


def _plot(distributions: dict[str, np.ndarray], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharex=True)
    labels = {
        "nearest_other_synthetic": "Pilot → nearest other pilot",
        "nearest_seed": "Pilot → nearest train seed",
        "nearest_eval": "Pilot → nearest Val/Test",
    }
    for axis, (name, values) in zip(axes, distributions.items(), strict=True):
        axis.hist(values, bins=35, color="#376996", alpha=0.85)
        axis.axvline(
            np.percentile(values, 95),
            color="#d1495b",
            linestyle="--",
            label="p95 reference (not threshold)",
        )
        axis.set_title(labels[name])
        axis.set_xlabel("Cosine similarity")
        axis.set_ylabel("Samples")
        axis.grid(alpha=0.2)
        axis.legend(loc="upper left", fontsize=8)
    figure.suptitle("BGE-M3 dense similarity distributions (F1–F4 pilot)")
    figure.tight_layout()
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)


def run(args: argparse.Namespace) -> None:
    if not args.model.exists():
        raise FileNotFoundError(f"BGE-M3 model is missing: {args.model}")
    pilot_ids, pilot_texts = _load_pilot(args.pilot)
    seeds = list(load_seed_pool().flat)
    seed_ids = [seed["id"] for seed in seeds]
    seed_texts = [seed["utt"] for seed in seeds]
    eval_ids, eval_texts = _load_eval()

    import torch

    if args.device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    backend = BgeM3Backend(
        model_path=args.model,
        device=args.device,
        batch_size=args.batch_size,
    )
    loaded_at = time.perf_counter()
    pilot_embeddings = backend.encode(pilot_texts)
    pilot_encoded_at = time.perf_counter()
    seed_embeddings = backend.encode(seed_texts)
    seeds_encoded_at = time.perf_counter()
    eval_embeddings = backend.encode(eval_texts)
    eval_encoded_at = time.perf_counter()
    distributions = {
        "nearest_other_synthetic": nearest_nonself_distribution(pilot_embeddings),
        "nearest_seed": nearest_similarity_distribution(pilot_embeddings, seed_embeddings),
        "nearest_eval": nearest_similarity_distribution(pilot_embeddings, eval_embeddings),
    }
    args.embeddings.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.embeddings,
        pilot_ids=np.asarray(pilot_ids),
        seed_ids=np.asarray(seed_ids),
        eval_ids=np.asarray(eval_ids),
        pilot_embeddings=pilot_embeddings,
        seed_embeddings=seed_embeddings,
        eval_embeddings=eval_embeddings,
        **distributions,
    )
    _plot(distributions, args.figure)
    weight_path = args.model / "pytorch_model.bin"
    weight_sha256 = _digest(weight_path)
    finished_at = time.perf_counter()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "measured_thresholds_pending_visual_review",
        "model": BgeM3Backend.model_name,
        "model_path": str(args.model.relative_to(REPO_ROOT)),
        "weight_bytes": weight_path.stat().st_size,
        "weight_sha256": weight_sha256,
        "device": args.device,
        "counts": {
            "pilot_f1_f4": len(pilot_texts),
            "train_seeds": len(seed_texts),
            "validation_and_test": len(eval_texts),
        },
        "timing_seconds": {
            "model_load": loaded_at - started,
            "pilot_encode": pilot_encoded_at - loaded_at,
            "seed_encode": seeds_encoded_at - pilot_encoded_at,
            "eval_encode": eval_encoded_at - seeds_encoded_at,
            "distribution_and_report": finished_at - eval_encoded_at,
            "total": finished_at - started,
        },
        "peak_gpu_allocated_mib": (
            torch.cuda.max_memory_allocated() / (1024**2) if args.device == "cuda" else None
        ),
        "peak_gpu_reserved_mib": (
            torch.cuda.max_memory_reserved() / (1024**2) if args.device == "cuda" else None
        ),
        "distributions": {name: _summary(values) for name, values in distributions.items()},
        "thresholds": {
            "synthetic_duplicate_max": None,
            "seed_too_close_max": None,
            "seed_outlier_min": None,
            "contamination_max": None,
        },
        "figure": str(args.figure.relative_to(REPO_ROOT)),
        "embeddings": str(args.embeddings.relative_to(REPO_ROOT)),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"measured BGE-M3 distributions for {len(pilot_texts)} pilot rows; report={args.report}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--embeddings", type=Path, default=DEFAULT_EMBEDDINGS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--figure", type=Path, default=DEFAULT_FIGURE)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
