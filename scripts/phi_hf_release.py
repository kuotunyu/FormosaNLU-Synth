"""Build, verify, and publish the allowlisted Phi-4-mini LoRA adapter bundle.

The default command only prepares a local bundle.  Public upload requires an
explicit confirmation token and always stages the repository as private before
performing authenticated and anonymous verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi, hf_hub_download
from peft import PeftConfig
from safetensors import safe_open

from scripts.hf_release import REPO_ROOT, assert_safe_text

HF_ACCOUNT = "steven0226"
PHI_REPO_ID = f"{HF_ACCOUNT}/phi-4-mini-formosanlu-lora"
BASE_MODEL_ID = "microsoft/Phi-4-mini-instruct"
BASE_MODEL_REVISION = "cfbefacb99257ffa30c83adab238a50856ac3083"
CONFIRMATION_TOKEN = "HF-PHI-ADAPTER-V1.2.2"

SOURCE_ADAPTER = (
    REPO_ROOT / "runs" / "m15" / "phi4mini" / "real_syn_filtered" / "seed_42" / "adapter"
)
CARD_PATH = REPO_ROOT / "hf_cards" / "phi_model_README.md"
DEFAULT_OUTPUT = REPO_ROOT / "outputs" / "huggingface_release_phi"
DEFAULT_REPORT = REPO_ROOT / "reports" / "m20_phi_adapter_publication.json"
EXPECTED_TENSOR_COUNT = 256
EXPECTED_ADAPTER_SHA256 = "e9e4c77d79eb12da8cba64a7a484d260f753d000396752f51159e3c0f4e34376"

PHI_MODEL_FILES = {
    "LICENSE",
    "README.md",
    "adapter_config.json",
    "adapter_model.safetensors",
    "chat_template.jinja",
    "release_manifest.json",
    "tokenizer.json",
    "tokenizer_config.json",
}
SOURCE_FILES = PHI_MODEL_FILES - {"LICENSE", "README.md", "release_manifest.json"}
TEXT_SUFFIXES = {"", ".json", ".jinja", ".md", ".txt"}

ADAPTER_LICENSE = """MIT License

Copyright (c) 2026 kuotunyu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

This repository contains only a LoRA adapter. Use of the Microsoft
Phi-4-mini-instruct base model remains subject to its own license and notices.
"""


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_commit() -> str:
    """Return the commit that defines the publication metadata."""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
    ).strip()


def sanitize_phi_adapter_config(payload: dict[str, Any]) -> dict[str, Any]:
    """Replace the local base-model path and pin the preregistered revision."""
    sanitized = dict(payload)
    sanitized["base_model_name_or_path"] = BASE_MODEL_ID
    sanitized["revision"] = BASE_MODEL_REVISION
    return sanitized


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _file_set(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def _reset_output(output_dir: Path, allowed_output_root: Path) -> None:
    output = output_dir.resolve()
    allowed = allowed_output_root.resolve()
    if output == allowed or not output.is_relative_to(allowed):
        raise ValueError(
            f"Refusing to reset output outside the allowed outputs directory: {output}"
        )
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)


def verify_phi_bundle(
    output_dir: Path = DEFAULT_OUTPUT,
    *,
    expected_tensor_count: int = EXPECTED_TENSOR_COUNT,
) -> dict[str, Any]:
    """Verify file allowlist, provenance, hashes, and loadable PEFT metadata."""
    observed_files = _file_set(output_dir)
    if observed_files != PHI_MODEL_FILES:
        raise ValueError(f"Unexpected Phi bundle files: {sorted(observed_files ^ PHI_MODEL_FILES)}")

    for path in output_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            assert_safe_text(
                path.read_text(encoding="utf-8"),
                label=path.relative_to(output_dir).as_posix(),
            )

    config = json.loads((output_dir / "adapter_config.json").read_text(encoding="utf-8"))
    if config.get("base_model_name_or_path") != BASE_MODEL_ID:
        raise ValueError("Phi adapter does not point to the public base model")
    if config.get("revision") != BASE_MODEL_REVISION:
        raise ValueError("Phi adapter revision does not match the frozen M15 contract")

    with safe_open(output_dir / "adapter_model.safetensors", framework="pt") as handle:
        tensor_count = len(handle.keys())
    if tensor_count != expected_tensor_count:
        raise ValueError(
            f"Expected {expected_tensor_count} Phi adapter tensors, observed {tensor_count}"
        )
    PeftConfig.from_pretrained(output_dir)

    manifest = json.loads((output_dir / "release_manifest.json").read_text(encoding="utf-8"))
    observed_sha = sha256_file(output_dir / "adapter_model.safetensors")
    if manifest.get("adapter_sha256") != observed_sha:
        raise ValueError("Phi adapter hash does not match its release manifest")
    if manifest.get("adapter_tensor_count") != tensor_count:
        raise ValueError("Phi adapter tensor count does not match its release manifest")

    return {
        "status": "ready_for_private_upload",
        "repo_id": PHI_REPO_ID,
        "files": sorted(observed_files),
        "base_model": BASE_MODEL_ID,
        "base_model_revision": BASE_MODEL_REVISION,
        "adapter_sha256": observed_sha,
        "adapter_bytes": (output_dir / "adapter_model.safetensors").stat().st_size,
        "adapter_tensor_count": tensor_count,
        "source_commit": str(manifest["source_commit"]),
        "visibility": "private",
    }


def build_phi_bundle(
    *,
    source_dir: Path = SOURCE_ADAPTER,
    card_path: Path = CARD_PATH,
    output_dir: Path = DEFAULT_OUTPUT,
    allowed_output_root: Path = REPO_ROOT / "outputs",
    source_commit: str | None = None,
    expected_tensor_count: int = EXPECTED_TENSOR_COUNT,
) -> dict[str, Any]:
    """Create the deterministic public bundle from one frozen seed-42 adapter."""
    _reset_output(output_dir, allowed_output_root)
    missing = [name for name in SOURCE_FILES if not (source_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Phi adapter source files are missing: {sorted(missing)}")

    for name in sorted(SOURCE_FILES - {"adapter_config.json"}):
        shutil.copy2(source_dir / name, output_dir / name)
    config = json.loads((source_dir / "adapter_config.json").read_text(encoding="utf-8"))
    _write_json(output_dir / "adapter_config.json", sanitize_phi_adapter_config(config))

    card_text = card_path.read_text(encoding="utf-8")
    assert_safe_text(card_text, label=card_path.name)
    (output_dir / "README.md").write_text(card_text, encoding="utf-8", newline="\n")
    (output_dir / "LICENSE").write_text(ADAPTER_LICENSE, encoding="utf-8", newline="\n")

    with safe_open(output_dir / "adapter_model.safetensors", framework="pt") as handle:
        tensor_count = len(handle.keys())
    commit = source_commit or globals()["source_commit"]()
    manifest = {
        "schema_version": 1,
        "repo_id": PHI_REPO_ID,
        "source_commit": commit,
        "base_model": BASE_MODEL_ID,
        "base_model_revision": BASE_MODEL_REVISION,
        "adapter_sha256": sha256_file(output_dir / "adapter_model.safetensors"),
        "adapter_bytes": (output_dir / "adapter_model.safetensors").stat().st_size,
        "adapter_tensor_count": tensor_count,
        "license": "MIT",
        "training_group": "real_syn_filtered",
        "seed": 42,
        "training_report": "reports/m15/phi4mini/real_syn_filtered_seed_42.json",
        "paired_statistics": "reports/m15_phi4mini_paired_statistics.json",
        "cross_family_report": "reports/m15_cross_model_replication.json",
    }
    _write_json(output_dir / "release_manifest.json", manifest)
    return verify_phi_bundle(output_dir, expected_tensor_count=expected_tensor_count)


def _verify_hub_files(api: HfApi, *, revision: str | None = None) -> set[str]:
    info = api.model_info(PHI_REPO_ID, revision=revision)
    return {sibling.rfilename for sibling in info.siblings}


def publish_phi_bundle(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    """Upload privately, verify remotely, publish, then verify anonymously."""
    plan = verify_phi_bundle(output_dir)
    api = HfApi()
    identity = api.whoami()
    if identity.get("name") != HF_ACCOUNT:
        raise PermissionError(f"Expected Hugging Face account {HF_ACCOUNT!r}, got {identity!r}")

    api.create_repo(PHI_REPO_ID, repo_type="model", private=True, exist_ok=True)
    commit = api.upload_folder(
        repo_id=PHI_REPO_ID,
        repo_type="model",
        folder_path=output_dir,
        commit_message="Release: publish v1.2.2 Phi-4-mini FormosaNLU LoRA adapter",
    )
    hub_commit = commit.oid
    remote_files = _verify_hub_files(api, revision=hub_commit)
    unexpected = remote_files - (PHI_MODEL_FILES | {".gitattributes"})
    missing = PHI_MODEL_FILES - remote_files
    if unexpected or missing:
        raise ValueError(
            f"Remote Phi allowlist mismatch; missing={sorted(missing)}, extra={sorted(unexpected)}"
        )

    remote_adapter = Path(
        hf_hub_download(
            PHI_REPO_ID,
            "adapter_model.safetensors",
            revision=hub_commit,
            repo_type="model",
        )
    )
    if sha256_file(remote_adapter) != plan["adapter_sha256"]:
        raise ValueError("Authenticated remote Phi adapter hash mismatch")

    api.update_repo_settings(PHI_REPO_ID, private=False)
    anonymous = HfApi(token=False)
    public_info = anonymous.model_info(PHI_REPO_ID, revision=hub_commit)
    if public_info.private:
        raise ValueError("Phi adapter repository remained private after publication")
    public_files = {sibling.rfilename for sibling in public_info.siblings}
    if not PHI_MODEL_FILES.issubset(public_files):
        raise ValueError("Anonymous Phi repository file verification failed")

    return {
        **plan,
        "status": "public_verified",
        "url": f"https://huggingface.co/{PHI_REPO_ID}",
        "hub_commit": hub_commit,
        "visibility": "public",
        "anonymous_verification": True,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    if args.execute and args.confirm != CONFIRMATION_TOKEN:
        parser.error(f"--execute requires --confirm {CONFIRMATION_TOKEN}")

    if args.verify_only:
        result = verify_phi_bundle()
    else:
        result = build_phi_bundle()
        if args.execute:
            result = publish_phi_bundle()
            _write_json(args.report, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
