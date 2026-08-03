"""Build the deterministic, allowlisted v1.2.1 GitHub Release evidence bundle."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from scripts.hf_release import REPO_ROOT

DEFAULT_OUTPUT = REPO_ROOT / "dist" / "v1.2.1"
ASSET_SOURCES: dict[Path, str] = {
    Path("reports/m19_ablation.json"): "m19_ablation.json",
    Path("reports/m19_ablation.md"): "m19_ablation.md",
    Path("reports/m19_runtime_audit.json"): "m19_runtime_audit.json",
    Path("reports/m12_resource_ledger.json"): "m12_resource_ledger.json",
    Path("reports/m13_publication.json"): "m13_publication.json",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_output(output_dir: Path, repo_root: Path) -> Path:
    output = output_dir.resolve()
    expected = (repo_root.resolve() / "dist" / "v1.2.1").resolve()
    if output != expected:
        raise ValueError(f"Release output must be the exact dist/v1.2.1 path: {expected}")
    return output


def build_assets(
    output_dir: Path = DEFAULT_OUTPUT,
    repo_root: Path = REPO_ROOT,
) -> dict[str, str]:
    """Copy the fixed public allowlist and return its SHA-256 manifest."""
    root = repo_root.resolve()
    output = _validated_output(output_dir, root)
    sources = {root / source: filename for source, filename in ASSET_SOURCES.items()}
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Release source files are missing: {', '.join(missing)}")

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    manifest: dict[str, str] = {}
    for source, filename in sorted(sources.items(), key=lambda item: item[1]):
        target = output / filename
        shutil.copyfile(source, target)
        manifest[filename] = _sha256(target)

    manifest_text = "".join(
        f"{manifest[filename]}  {filename}\n" for filename in sorted(manifest)
    )
    (output / "SHA256SUMS.txt").write_text(
        manifest_text,
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main() -> int:
    manifest = build_assets()
    payload = {
        "output": DEFAULT_OUTPUT.relative_to(REPO_ROOT).as_posix(),
        "files": sorted([*manifest, "SHA256SUMS.txt"]),
        "sha256": manifest,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
