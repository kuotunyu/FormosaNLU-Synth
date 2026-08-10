from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from scripts.build_v122_release_assets import ASSET_SOURCES, build_assets


EXPECTED_ASSETS = {
    "formosanlu_synth_v1.2.2.pdf",
    "m15_cross_model_replication.json",
    "m15_cross_model_replication.md",
    "m15_phi4mini_paired_statistics.json",
    "m20_phi_adapter_publication.json",
    "m12_resource_ledger.json",
    "SHA256SUMS.txt",
}


def _fake_repo(tmp_path: Path) -> tuple[Path, Path]:
    for source in ASSET_SOURCES:
        path = tmp_path / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"{source.as_posix()}\n".encode())
    return tmp_path, tmp_path / "dist" / "v1.2.2"


def test_build_v122_assets_copies_only_the_evidence_allowlist(tmp_path: Path) -> None:
    repo_root, output = _fake_repo(tmp_path)

    manifest = build_assets(output, repo_root=repo_root)

    assert {path.name for path in output.iterdir()} == EXPECTED_ASSETS
    assert set(manifest) == EXPECTED_ASSETS - {"SHA256SUMS.txt"}
    for filename, digest in manifest.items():
        assert sha256((output / filename).read_bytes()).hexdigest() == digest


def test_build_v122_assets_rejects_nonversioned_output(tmp_path: Path) -> None:
    repo_root, _ = _fake_repo(tmp_path)

    with pytest.raises(ValueError, match="dist/v1.2.2"):
        build_assets(tmp_path / "dist" / "wrong", repo_root=repo_root)
