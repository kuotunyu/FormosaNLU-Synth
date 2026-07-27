"""Download the two pinned Marian checkpoints required by Standard Aug."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from huggingface_hub import snapshot_download

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "augmentation.yaml"
DEFAULT_REPORT = REPO_ROOT / "reports" / "m9_translation_models.json"
ALLOW_PATTERNS = (
    "README.md",
    "config.json",
    "generation_config.json",
    "metadata.json",
    "pytorch_model.bin",
    "source.spm",
    "target.spm",
    "tokenizer_config.json",
    "vocab.json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _download(spec: dict[str, Any]) -> dict[str, Any]:
    target = REPO_ROOT / spec["local_path"]
    snapshot_download(
        repo_id=spec["repo_id"],
        revision=spec["revision"],
        local_dir=target,
        allow_patterns=list(ALLOW_PATTERNS),
    )
    weight = target / "pytorch_model.bin"
    if not weight.exists():
        raise FileNotFoundError(f"Marian PyTorch weight was not downloaded: {weight}")
    files = [
        {
            "path": str(path.relative_to(REPO_ROOT)),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(target.iterdir())
        if path.is_file()
    ]
    return {
        "repo_id": spec["repo_id"],
        "revision": spec["revision"],
        "license": spec["license"],
        "local_path": spec["local_path"],
        "downloaded_bytes": sum(item["bytes"] for item in files),
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    backtranslation = config["methods"]["backtranslation"]
    models = [
        _download(backtranslation["source"]),
        _download(backtranslation["target"]),
    ]
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "models": models,
        "total_downloaded_bytes": sum(model["downloaded_bytes"] for model in models),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"verified {len(models)} Marian models ({payload['total_downloaded_bytes']} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
