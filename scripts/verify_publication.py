"""Verify the public GitHub and Hugging Face release without credentials."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from huggingface_hub import HfApi, hf_hub_download

from scripts.hf_release import (
    BASE_MODEL_ID,
    DATASET_FILES,
    DATASET_REPO_ID,
    MODEL_FILES,
    MODEL_REPO_ID,
    REPO_ROOT,
)

DEFAULT_REPORT = REPO_ROOT / "reports" / "m13_publication.json"
GITHUB_API = "https://api.github.com/repos/kuotunyu/FormosaNLU-Synth"
GITHUB_CONTRIBUTORS_API = f"{GITHUB_API}/contributors?per_page=100"
GITHUB_URL = "https://github.com/kuotunyu/FormosaNLU-Synth"
DATASET_URL = f"https://huggingface.co/datasets/{DATASET_REPO_ID}"
MODEL_URL = f"https://huggingface.co/{MODEL_REPO_ID}"
EXPECTED_ADAPTER_SHA256 = "f70f423814dcd47943c92c0beb8b08a4e7f65e60a44355d3dcd95bed9f0bd60a"
EXPECTED_DATASET_SHA256 = "c65d7209d953e144299625f6a9224b98557b2677d55258a463a2992e5acf4665"


def _get_json(url: str) -> Any:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def verify_publication() -> dict[str, Any]:
    """Return traceable public-release evidence or raise on any mismatch."""
    github = _get_json(GITHUB_API)
    contributors = _get_json(GITHUB_CONTRIBUTORS_API)
    contributor_logins = [str(item["login"]) for item in contributors]
    if github["private"] is not False or github["visibility"] != "public":
        raise ValueError("GitHub repository is not public")
    if contributor_logins != ["kuotunyu"]:
        raise ValueError(f"Unexpected GitHub contributors: {contributor_logins}")

    api = HfApi(token=False)
    dataset = api.dataset_info(DATASET_REPO_ID, files_metadata=True)
    model = api.model_info(MODEL_REPO_ID, files_metadata=True)
    if dataset.private is not False or model.private is not False:
        raise ValueError("One or more Hugging Face repositories are not public")

    dataset_files = {item.rfilename for item in dataset.siblings}
    model_files = {item.rfilename for item in model.siblings}
    if dataset_files != DATASET_FILES | {".gitattributes"}:
        raise ValueError(f"Unexpected public dataset files: {dataset_files}")
    if model_files != MODEL_FILES | {".gitattributes"}:
        raise ValueError(f"Unexpected public model files: {model_files}")

    dataset_card = dataset.card_data.to_dict()
    model_card = model.card_data.to_dict()
    if dataset_card.get("license") != "cc-by-4.0":
        raise ValueError("Public dataset license metadata mismatch")
    if model_card.get("license") != "apache-2.0":
        raise ValueError("Public model license metadata mismatch")
    if model_card.get("base_model") != BASE_MODEL_ID:
        raise ValueError("Public model base_model metadata mismatch")

    manifest_path = Path(
        hf_hub_download(
            DATASET_REPO_ID,
            "release_manifest.json",
            repo_type="dataset",
            token=False,
        )
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if int(manifest["rows"]) != 3754:
        raise ValueError("Public dataset row count metadata mismatch")
    if manifest["train_sha256"] != EXPECTED_DATASET_SHA256:
        raise ValueError("Public dataset SHA-256 metadata mismatch")

    config_path = Path(hf_hub_download(MODEL_REPO_ID, "adapter_config.json", token=False))
    adapter_config = json.loads(config_path.read_text(encoding="utf-8"))
    if adapter_config["base_model_name_or_path"] != BASE_MODEL_ID:
        raise ValueError("Public adapter config base model mismatch")
    adapter_entry = next(
        item for item in model.siblings if item.rfilename == "adapter_model.safetensors"
    )
    if adapter_entry.lfs is None or adapter_entry.lfs.sha256 != EXPECTED_ADAPTER_SHA256:
        raise ValueError("Public adapter LFS SHA-256 mismatch")
    if int(adapter_entry.size or 0) != 155_609_536:
        raise ValueError("Public adapter byte size mismatch")

    viewer_response = requests.get(
        "https://datasets-server.huggingface.co/first-rows",
        params={
            "dataset": DATASET_REPO_ID,
            "config": "default",
            "split": "train",
        },
        timeout=60,
    )
    if viewer_response.status_code != 200:
        raise ValueError(
            f"Dataset Viewer is not ready: HTTP {viewer_response.status_code} "
            f"{viewer_response.text[:200]}"
        )
    viewer = viewer_response.json()
    if len(viewer.get("rows", [])) == 0:
        raise ValueError("Dataset Viewer returned no rows")

    return {
        "schema_version": 1,
        "status": "public_verified",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "anonymous_verification": True,
        "github": {
            "url": GITHUB_URL,
            "visibility": github["visibility"],
            "default_branch": github["default_branch"],
            "contributors": contributor_logins,
            "contributors_only_kuotunyu": contributor_logins == ["kuotunyu"],
        },
        "dataset": {
            "url": DATASET_URL,
            "repo_id": DATASET_REPO_ID,
            "visibility": "public",
            "hub_commit": dataset.sha,
            "files": sorted(dataset_files),
            "rows": int(manifest["rows"]),
            "train_sha256": manifest["train_sha256"],
            "license": dataset_card["license"],
            "viewer_status": "ready",
        },
        "model": {
            "url": MODEL_URL,
            "repo_id": MODEL_REPO_ID,
            "visibility": "public",
            "hub_commit": model.sha,
            "files": sorted(model_files),
            "base_model": adapter_config["base_model_name_or_path"],
            "adapter_sha256": adapter_entry.lfs.sha256,
            "adapter_bytes": int(adapter_entry.size or 0),
            "license": model_card["license"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=f"Write the verified evidence to {DEFAULT_REPORT.relative_to(REPO_ROOT)}.",
    )
    args = parser.parse_args()
    report = verify_publication()
    if args.write_report:
        DEFAULT_REPORT.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
