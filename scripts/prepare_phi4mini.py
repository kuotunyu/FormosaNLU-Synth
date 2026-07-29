"""Inspect or download the frozen Phi-4-mini snapshot for M15."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi, snapshot_download

from src.training.train import REPO_ROOT

MODEL_ID = "microsoft/Phi-4-mini-instruct"
REVISION = "cfbefacb99257ffa30c83adab238a50856ac3083"
CONFIRMATION = "M15-PHI4MINI-7.7GB"
LOCAL_DIR = REPO_ROOT / "data" / "models" / "Phi-4-mini-instruct"
REPORT_PATH = REPO_ROOT / "reports" / "m15_phi4mini_artifacts.json"
MIN_FREE_AFTER_DOWNLOAD_GIB = 100.0
ALLOW_PATTERNS = (
    "*.json",
    "*.safetensors",
    "*.jinja",
    "*.model",
    "LICENSE*",
    "NOTICE*",
)


def _selected(filename: str) -> bool:
    path = Path(filename)
    if path.suffix in {".json", ".safetensors", ".jinja", ".model"}:
        return True
    return path.name.startswith(("LICENSE", "NOTICE"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_remote() -> dict[str, Any]:
    info = HfApi().model_info(
        MODEL_ID,
        revision=REVISION,
        files_metadata=True,
    )
    if info.sha != REVISION:
        raise RuntimeError(f"Resolved revision drifted: {info.sha} != {REVISION}")
    files = {
        item.rfilename: int(item.size or 0)
        for item in info.siblings
        if _selected(item.rfilename)
    }
    if not files or not any(name.endswith(".safetensors") for name in files):
        raise RuntimeError("Frozen Phi snapshot does not contain expected weights")
    return {
        "model_id": MODEL_ID,
        "revision": info.sha,
        "license": str(getattr(info.card_data, "license", None) or "unknown"),
        "files": files,
        "download_bytes": sum(files.values()),
    }


def _disk_gate(download_bytes: int) -> dict[str, float]:
    free_bytes = shutil.disk_usage(REPO_ROOT).free
    projected = free_bytes - download_bytes
    payload = {
        "free_gib": free_bytes / (1024**3),
        "projected_free_gib": projected / (1024**3),
        "minimum_free_gib": MIN_FREE_AFTER_DOWNLOAD_GIB,
    }
    if payload["projected_free_gib"] < MIN_FREE_AFTER_DOWNLOAD_GIB:
        raise RuntimeError(f"Disk guard failed: {payload}")
    return payload


def audit_local(remote: dict[str, Any]) -> dict[str, Any]:
    local_files: dict[str, Any] = {}
    mismatches = []
    for name, expected_size in remote["files"].items():
        path = LOCAL_DIR / name
        actual_size = path.stat().st_size if path.is_file() else None
        if actual_size != expected_size:
            mismatches.append(f"{name}:{actual_size}!={expected_size}")
            continue
        row: dict[str, Any] = {"bytes": actual_size}
        if name.endswith(".safetensors"):
            row["sha256"] = _sha256(path)
        local_files[name] = row
    return {
        "complete": not mismatches,
        "mismatches": mismatches,
        "files": local_files,
    }


def build_report(
    *,
    remote: dict[str, Any],
    disk: dict[str, float],
    local: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if local["complete"] else "download_required",
        "model": remote,
        "local_dir": str(LOCAL_DIR.relative_to(REPO_ROOT)).replace("\\", "/"),
        "local": local,
        "disk_gate": disk,
        "confirmation": CONFIRMATION,
    }


def _write_report(payload: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", help=f"Required with --execute: {CONFIRMATION}")
    args = parser.parse_args()

    remote = inspect_remote()
    disk = _disk_gate(remote["download_bytes"])
    local = audit_local(remote) if LOCAL_DIR.is_dir() else {
        "complete": False,
        "mismatches": ["local snapshot absent"],
        "files": {},
    }
    report = build_report(remote=remote, disk=disk, local=local)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.execute:
        return 0 if local["complete"] else 2
    if args.confirm != CONFIRMATION:
        raise RuntimeError(
            f"Phi download requires exact --confirm {CONFIRMATION}"
        )
    if not local["complete"]:
        snapshot_download(
            repo_id=MODEL_ID,
            revision=REVISION,
            local_dir=LOCAL_DIR,
            allow_patterns=list(ALLOW_PATTERNS),
        )
        local = audit_local(remote)
        report = build_report(remote=remote, disk=disk, local=local)
    _write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if local["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
