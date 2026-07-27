"""Build a deterministic, model-free Colab training bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "outputs" / "formosanlu_colab_bundle.zip"
DEFAULT_REPORT = REPO_ROOT / "reports" / "m9_colab_bundle.json"
REQUIRED_ARTIFACTS = (
    Path("data/raw/massive/zh-TW/train/0000.parquet"),
    Path("data/raw/massive/zh-TW/validation/0000.parquet"),
    Path("data/raw/massive/zh-TW/test/0000.parquet"),
    Path("data/generated/full_unfiltered.jsonl"),
    Path("data/filtered/full_f1_f6.jsonl"),
    Path("data/training/standard_aug.jsonl"),
)
TRACKED_ROOTS = (
    Path("src"),
    Path("configs"),
)
TRACKED_FILES = (
    Path("pyproject.toml"),
    Path("uv.lock"),
    Path("requirements.txt"),
    Path("splits/manifest.json"),
    Path("LICENSE"),
    Path("README.md"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _git_is_dirty() -> bool:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return bool(completed.stdout.strip())


def bundle_files(repo_root: Path = REPO_ROOT) -> list[Path]:
    paths: list[Path] = []
    for root in TRACKED_ROOTS:
        paths.extend(
            path.relative_to(repo_root)
            for path in (repo_root / root).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    paths.extend(TRACKED_FILES)
    paths.extend(REQUIRED_ARTIFACTS)
    unique = sorted(set(paths), key=lambda path: path.as_posix())
    missing = [path for path in unique if not (repo_root / path).is_file()]
    if missing:
        raise FileNotFoundError(f"Colab bundle inputs missing: {missing}")
    return unique


def build_bundle(
    *,
    output: Path,
    repo_root: Path = REPO_ROOT,
    allow_dirty: bool = False,
) -> dict[str, Any]:
    if repo_root == REPO_ROOT and _git_is_dirty() and not allow_dirty:
        raise RuntimeError(
            "Refusing to build a provenance bundle from a dirty worktree. "
            "Commit verified source changes first, then rerun."
        )
    files = bundle_files(repo_root)
    commit = _git_commit()
    manifest = {
        "schema_version": 1,
        "source_commit": commit,
        "model_included": False,
        "model_hub_id": "google/gemma-4-E4B-it",
        "files": [
            {
                "path": path.as_posix(),
                "bytes": (repo_root / path).stat().st_size,
                "sha256": _sha256(repo_root / path),
            }
            for path in files
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for relative in files:
            data = (repo_root / relative).read_bytes()
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        info = zipfile.ZipInfo(
            "COLAB_BUNDLE_MANIFEST.json",
            date_time=(1980, 1, 1, 0, 0, 0),
        )
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(
            info,
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "ready",
        "output": str(output.relative_to(repo_root)),
        "bytes": output.stat().st_size,
        "sha256": _sha256(output),
        "source_commit": commit,
        "file_count": len(files) + 1,
        "model_included": False,
        "required_gpu_memory_mib": 22434,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    report = build_bundle(output=args.output, allow_dirty=args.allow_dirty)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"built {report['output']} ({report['bytes']} bytes), "
        f"sha256={report['sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
