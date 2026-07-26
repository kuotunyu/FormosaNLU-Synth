"""Record M8 package and Gemma 4 artifact metadata without importing torch."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = REPO_ROOT / "data" / "models" / "gemma-4-E4B-it"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "m8_artifacts.json"
MODEL_ID = "google/gemma-4-E4B-it"
PACKAGES = (
    "torch",
    "transformers",
    "accelerate",
    "peft",
    "trl",
    "bitsandbytes",
    "sentence-transformers",
)


def inspect(model_dir: Path) -> dict[str, Any]:
    config_path = model_dir / "config.json"
    weight_path = model_dir / "model.safetensors"
    if not config_path.exists() or not weight_path.exists():
        raise FileNotFoundError("Gemma 4 config or model.safetensors is missing")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    info = HfApi().model_info(MODEL_ID, files_metadata=True)
    remote_weight = next(
        sibling for sibling in info.siblings if sibling.rfilename == "model.safetensors"
    )
    local_files = {path.name: path.stat().st_size for path in model_dir.iterdir() if path.is_file()}
    total_bytes = sum(local_files.values())
    disk = shutil.disk_usage(REPO_ROOT)
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_id": MODEL_ID,
        "revision": info.sha,
        "license": info.card_data.get("license") if info.card_data else None,
        "local_dir": str(model_dir.relative_to(REPO_ROOT)),
        "local_files": local_files,
        "local_total_bytes": total_bytes,
        "local_total_gib": total_bytes / (1024**3),
        "remote_weight_bytes": remote_weight.size,
        "remote_weight_sha256": (remote_weight.lfs.get("sha256") if remote_weight.lfs else None),
        "weight_size_matches_remote": weight_path.stat().st_size == remote_weight.size,
        "config_transformers_version": config.get("transformers_version"),
        "architectures": config.get("architectures"),
        "model_type": config.get("model_type"),
        "text_model_type": config.get("text_config", {}).get("model_type"),
        "text_only_class": "Gemma4ForCausalLM",
        "multimodal_towers_loaded": False,
        "packages": {package: importlib.metadata.version(package) for package in PACKAGES},
        "disk_free_bytes": disk.free,
        "disk_free_gib": disk.free / (1024**3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = inspect(args.model_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"verified Gemma artifact {payload['local_total_gib']:.2f} GiB; "
        f"free disk {payload['disk_free_gib']:.1f} GiB",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
