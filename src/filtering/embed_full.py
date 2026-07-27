"""Embed the full F1-F4 corpus with frozen BGE-M3 references for M6."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from src.filtering.bge_m3 import BgeM3Backend

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "data" / "filtered" / "full_f1_f4.jsonl"
DEFAULT_MODEL = REPO_ROOT / "data" / "models" / "bge-m3"
DEFAULT_REFERENCES = REPO_ROOT / "data" / "embeddings" / "m5_pilot_bge_m3.npz"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "embeddings" / "m6_full_bge_m3.npz"
DEFAULT_REPORT = REPO_ROOT / "reports" / "m6_embedding_report.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_corpus(path: Path) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    texts: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            sample = record.get("sample")
            if not isinstance(sample, dict):
                raise ValueError(f"Missing sample object at {path}:{line_number}")
            sample_id = sample.get("id")
            utterance = sample.get("utt")
            if not isinstance(sample_id, str) or not sample_id:
                raise ValueError(f"Missing sample id at {path}:{line_number}")
            if not isinstance(utterance, str) or not utterance.strip():
                raise ValueError(f"Missing utterance at {path}:{line_number}")
            ids.append(sample_id)
            texts.append(utterance)
    if len(ids) != len(set(ids)):
        raise ValueError("Full F1-F4 corpus contains duplicate sample ids")
    return ids, texts


def load_frozen_references(
    path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    with np.load(path) as archive:
        required = {"seed_ids", "eval_ids", "seed_embeddings", "eval_embeddings"}
        missing = required.difference(archive.files)
        if missing:
            raise ValueError(f"Frozen reference archive is missing {sorted(missing)}")
        seed_ids = np.asarray(archive["seed_ids"])
        eval_ids = np.asarray(archive["eval_ids"])
        seed_embeddings = np.asarray(archive["seed_embeddings"], dtype=np.float32)
        eval_embeddings = np.asarray(archive["eval_embeddings"], dtype=np.float32)
    if len(seed_ids) != len(seed_embeddings):
        raise ValueError("Frozen seed ids and embeddings do not align")
    if len(eval_ids) != len(eval_embeddings):
        raise ValueError("Frozen eval ids and embeddings do not align")
    return seed_ids, eval_ids, seed_embeddings, eval_embeddings


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.model.exists():
        raise FileNotFoundError(f"BGE-M3 model is missing: {args.model}")
    if not args.references.exists():
        raise FileNotFoundError(f"Frozen M5 references are missing: {args.references}")
    sample_ids, texts = load_corpus(args.input)
    seed_ids, eval_ids, seed_embeddings, eval_embeddings = load_frozen_references(
        args.references
    )

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
    synthetic_embeddings = backend.encode(texts)
    encoded_at = time.perf_counter()
    if len(synthetic_embeddings) != len(sample_ids):
        raise ValueError("BGE-M3 output count differs from input count")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        pilot_ids=np.asarray(sample_ids),
        seed_ids=seed_ids,
        eval_ids=eval_ids,
        pilot_embeddings=np.asarray(synthetic_embeddings, dtype=np.float32),
        seed_embeddings=seed_embeddings,
        eval_embeddings=eval_embeddings,
    )
    finished_at = time.perf_counter()
    weight_path = args.model / "pytorch_model.bin"
    payload: dict[str, Any] = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "model": BgeM3Backend.model_name,
        "model_path": str(args.model.relative_to(REPO_ROOT)),
        "model_weight_bytes": weight_path.stat().st_size,
        "model_weight_sha256": _sha256(weight_path),
        "input": str(args.input.relative_to(REPO_ROOT)),
        "input_sha256": _sha256(args.input),
        "frozen_references": str(args.references.relative_to(REPO_ROOT)),
        "frozen_references_sha256": _sha256(args.references),
        "output": str(args.output.relative_to(REPO_ROOT)),
        "output_sha256": _sha256(args.output),
        "device": args.device,
        "batch_size": args.batch_size,
        "counts": {
            "synthetic_f1_f4": len(sample_ids),
            "train_seeds": len(seed_ids),
            "validation_and_test": len(eval_ids),
        },
        "timing_seconds": {
            "model_load": loaded_at - started,
            "synthetic_encode": encoded_at - loaded_at,
            "archive_write_and_hash": finished_at - encoded_at,
            "total": finished_at - started,
        },
        "peak_gpu_allocated_mib": (
            torch.cuda.max_memory_allocated() / (1024**2) if args.device == "cuda" else None
        ),
        "peak_gpu_reserved_mib": (
            torch.cuda.max_memory_reserved() / (1024**2) if args.device == "cuda" else None
        ),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"embedded {len(sample_ids)} full-corpus rows; output={args.output}", flush=True)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--references", type=Path, default=DEFAULT_REFERENCES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
