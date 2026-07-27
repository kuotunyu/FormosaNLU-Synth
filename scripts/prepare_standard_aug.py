"""Create the deterministic slot-safe Standard Aug corpus for M9."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

from src.synthetic.planning import load_seed_pool
from src.training.augmentation import (
    generate_standard_augmentations,
    translate_non_slot_segments,
)
from src.training.backtranslation import MarianRoundTrip

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "augmentation.yaml"
DEFAULT_FILTERED = REPO_ROOT / "data" / "filtered" / "full_f1_f6.jsonl"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "training" / "standard_aug.jsonl"
DEFAULT_REPORT = REPO_ROOT / "reports" / "m9_standard_aug.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(bool(line.strip()) for line in handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--filtered", type=Path, default=DEFAULT_FILTERED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    target_count = _line_count(args.filtered)
    seeds = list(load_seed_pool().flat)
    method_config = config["methods"]["backtranslation"]
    translator = MarianRoundTrip(
        zh_en_path=REPO_ROOT / method_config["source"]["local_path"],
        en_zh_path=REPO_ROOT / method_config["target"]["local_path"],
        device=args.device,
        batch_size=int(method_config["batch_size"]),
        max_length=int(method_config["max_length"]),
    )
    started = time.perf_counter()
    backtranslated = translate_non_slot_segments(seeds, translator.translate)
    translated_at = time.perf_counter()
    rows = generate_standard_augmentations(
        seeds,
        target_count=target_count,
        seed=int(config["seed"]),
        backtranslated=backtranslated,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    finished = time.perf_counter()
    methods = Counter(row["augmentation"]["method"] for row in rows)
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "seed": int(config["seed"]),
        "target_filtered_synthetic_count": target_count,
        "frozen_real_seed_count": len(seeds),
        "augmentation_count": len(rows),
        "training_group_count": len(seeds) + len(rows),
        "method_counts": dict(sorted(methods.items())),
        "backtranslation_grounded_candidates": len(backtranslated),
        "filtered_source_sha256": _sha256(args.filtered),
        "output": str(args.output.relative_to(REPO_ROOT)),
        "output_sha256": _sha256(args.output),
        "timing_seconds": {
            "backtranslation": translated_at - started,
            "eda_noise_and_write": finished - translated_at,
            "total": finished - started,
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} deterministic Standard Aug rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
