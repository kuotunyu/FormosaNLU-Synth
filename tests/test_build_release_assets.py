from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from scripts.build_release_assets import ASSET_SOURCES, build_assets

EXPECTED_ASSETS = {
    "m19_ablation.json",
    "m19_ablation.md",
    "m19_runtime_audit.json",
    "m12_resource_ledger.json",
    "m13_publication.json",
    "SHA256SUMS.txt",
}


def _fake_repo(tmp_path: Path) -> tuple[Path, Path]:
    reports = tmp_path / "reports"
    reports.mkdir()
    for source in ASSET_SOURCES:
        path = tmp_path / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"{source.as_posix()}\n".encode())
    output = tmp_path / "dist" / "v1.2.1"
    return tmp_path, output


def test_build_assets_copies_only_the_allowlist(tmp_path: Path) -> None:
    repo_root, output = _fake_repo(tmp_path)

    build_assets(output, repo_root=repo_root)

    assert {path.name for path in output.iterdir()} == EXPECTED_ASSETS


def test_manifest_recomputes_every_payload_hash(tmp_path: Path) -> None:
    repo_root, output = _fake_repo(tmp_path)

    manifest = build_assets(output, repo_root=repo_root)

    assert set(manifest) == EXPECTED_ASSETS - {"SHA256SUMS.txt"}
    for filename, digest in manifest.items():
        assert sha256((output / filename).read_bytes()).hexdigest() == digest
    rows = (output / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    assert rows == [f"{manifest[name]}  {name}" for name in sorted(manifest)]


def test_rebuild_removes_only_the_exact_version_directory(tmp_path: Path) -> None:
    repo_root, output = _fake_repo(tmp_path)
    sibling = repo_root / "dist" / "keep.txt"
    sibling.parent.mkdir(parents=True, exist_ok=True)
    sibling.write_text("keep\n", encoding="utf-8")
    output.mkdir(parents=True)
    (output / "stale.txt").write_text("stale\n", encoding="utf-8")

    build_assets(output, repo_root=repo_root)

    assert sibling.read_text(encoding="utf-8") == "keep\n"
    assert not (output / "stale.txt").exists()


def test_rejects_output_outside_repo_dist(tmp_path: Path) -> None:
    repo_root, _ = _fake_repo(tmp_path)

    with pytest.raises(ValueError, match="dist"):
        build_assets(tmp_path / "elsewhere", repo_root=repo_root)
