"""Build and validate the guarded Hugging Face release bundles.

This module never uploads or changes repository visibility. It prepares two
allowlisted directories under ``outputs/huggingface_release`` so the caller can
upload exactly those directories, rather than a training run or the full data
tree by mistake.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from peft import PeftConfig
from safetensors import safe_open

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "outputs" / "huggingface_release"
SOURCE_DATA = REPO_ROOT / "data" / "filtered" / "full_f1_f7_release.jsonl"
F7_REPORT = REPO_ROOT / "reports" / "m6_f7_release.json"
ADAPTER_DIR = REPO_ROOT / "runs" / "real_syn_filtered" / "seed_42" / "adapter"
CARD_DIR = REPO_ROOT / "hf_cards"

HF_ACCOUNT = "steven0226"
DATASET_REPO_ID = f"{HF_ACCOUNT}/formosa-nlu-synth-v1"
MODEL_REPO_ID = f"{HF_ACCOUNT}/gemma-4-e4b-formosanlu-lora"
BASE_MODEL_ID = "google/gemma-4-E4B-it"

DATASET_FILES = {
    "LICENSE",
    "README.md",
    "data/train.jsonl",
    "release_manifest.json",
    "schema.json",
}
MODEL_FILES = {
    "LICENSE",
    "README.md",
    "adapter_config.json",
    "adapter_model.safetensors",
    "chat_template.jinja",
    "tokenizer.json",
    "tokenizer_config.json",
}
MODEL_SOURCE_FILES = MODEL_FILES - {"LICENSE", "README.md"}
TEXT_SUFFIXES = {"", ".json", ".jsonl", ".jinja", ".md", ".txt"}
SECRET_OR_LOCAL_PATH = re.compile(
    r"(?:[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/]"
    r"|(?:^|[\\/])3Hml(?:[\\/]|$)"
    r"|hf_[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|sk-[A-Za-z0-9_-]{20,})",
    re.IGNORECASE | re.MULTILINE,
)

DATASET_LICENSE = """FormosaNLU Synth is licensed under the
Creative Commons Attribution 4.0 International License (CC BY 4.0).

License text: https://creativecommons.org/licenses/by/4.0/legalcode

Required attribution:
FitzGerald et al., MASSIVE: A 1M-Example Multilingual Natural Language
Understanding Dataset with 51 Typologically-Diverse Languages,
https://github.com/alexa/massive

The released records are synthetic adaptations derived from MASSIVE zh-TW seed
examples. The dataset card identifies the modifications and generation process.
"""

MODEL_LICENSE = """FormosaNLU Gemma 4 E4B LoRA adapter

SPDX-License-Identifier: Apache-2.0

Copyright 2026 kuotunyu

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy at:

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied.
"""


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def source_commit() -> str:
    """Return the exact Git commit that describes this release."""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
    ).strip()


def flatten_release_row(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert the internal audit record into the public training schema."""
    sample = payload["sample"]
    provenance = sample["provenance"]
    row = {
        "id": sample["id"],
        "utt": sample["utt"],
        "intent": sample["intent"],
        "slots": sample["slots"],
        "style": sample["style"],
        "recipe": provenance["recipe"],
        "teacher_model": provenance["model"],
        "teacher_model_digest": provenance["model_digest"],
        "prompt_version": provenance["prompt_version"],
        "seed_sample_id": provenance["seed_sample_id"],
        "generation_params": provenance["gen_params"],
        "filter_scores": provenance["filter_score"],
    }
    required = ("id", "utt", "intent", "slots", "style", "recipe", "teacher_model")
    if any(row[key] in (None, "") for key in required):
        raise ValueError(f"Release row is missing a required field: {payload!r}")
    if not isinstance(row["slots"], list):
        raise TypeError("Release row slots must be a list")
    return row


def sanitize_adapter_config(payload: dict[str, Any]) -> dict[str, Any]:
    """Replace the machine-local base path with the public base model ID."""
    sanitized = dict(payload)
    sanitized["base_model_name_or_path"] = BASE_MODEL_ID
    return sanitized


def assert_safe_text(text: str, *, label: str) -> None:
    """Reject credentials and machine-local user paths before upload."""
    match = SECRET_OR_LOCAL_PATH.search(text)
    if match:
        raise ValueError(f"Unsafe content in {label}: {match.group(0)!r}")
    if "[More Information Needed]" in text or "<!-- FILL" in text:
        raise ValueError(f"Unresolved card placeholder in {label}")


def _safe_reset_output(output_root: Path) -> None:
    resolved = output_root.resolve()
    allowed_root = (REPO_ROOT / "outputs").resolve()
    if not resolved.is_relative_to(allowed_root) or resolved == allowed_root:
        raise ValueError(
            f"Refusing to reset output outside the project outputs directory: {resolved}"
        )
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def _relative_file_set(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def _copy_card(source_name: str, destination: Path) -> None:
    text = (CARD_DIR / source_name).read_text(encoding="utf-8")
    assert_safe_text(text, label=source_name)
    destination.write_text(text, encoding="utf-8", newline="\n")


def _build_dataset_bundle(dataset_root: Path) -> dict[str, Any]:
    report = _load_json(F7_REPORT)
    expected_rows = int(report["release_rows"])
    expected_source_sha = str(report["release_sha256"])
    observed_source_sha = sha256_file(SOURCE_DATA)
    if observed_source_sha != expected_source_sha:
        raise ValueError("F7 release source SHA-256 does not match the tracked report")

    data_dir = dataset_root / "data"
    data_dir.mkdir(parents=True)
    train_path = data_dir / "train.jsonl"
    ids: set[str] = set()
    intents: set[str] = set()
    rows = 0
    with (
        SOURCE_DATA.open("r", encoding="utf-8") as source,
        train_path.open("w", encoding="utf-8", newline="\n") as destination,
    ):
        for line in source:
            if not line.strip():
                continue
            row = flatten_release_row(json.loads(line))
            sample_id = str(row["id"])
            if sample_id in ids:
                raise ValueError(f"Duplicate sample ID in release corpus: {sample_id}")
            ids.add(sample_id)
            intents.add(str(row["intent"]))
            destination.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            )
            rows += 1
    if rows != expected_rows:
        raise ValueError(f"Expected {expected_rows} release rows, observed {rows}")
    if len(intents) != 60:
        raise ValueError(f"Expected 60 intents, observed {len(intents)}")

    _copy_card("dataset_README.md", dataset_root / "README.md")
    (dataset_root / "LICENSE").write_text(DATASET_LICENSE, encoding="utf-8", newline="\n")
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "FormosaNLU Synth training row",
        "type": "object",
        "required": ["id", "utt", "intent", "slots", "style", "recipe", "teacher_model"],
        "properties": {
            "id": {"type": "string"},
            "utt": {"type": "string"},
            "intent": {"type": "string"},
            "slots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type", "value"],
                    "properties": {
                        "type": {"type": "string"},
                        "value": {"type": "string"},
                    },
                },
            },
            "style": {"type": "string"},
            "recipe": {"type": "string"},
            "teacher_model": {"type": "string"},
            "teacher_model_digest": {"type": "string"},
            "prompt_version": {"type": "string"},
            "seed_sample_id": {"type": "string"},
            "generation_params": {"type": "object"},
            "filter_scores": {"type": "object"},
        },
    }
    _write_json(dataset_root / "schema.json", schema)
    manifest = {
        "schema_version": 1,
        "repo_id": DATASET_REPO_ID,
        "source_commit": source_commit(),
        "source_artifact": "data/filtered/full_f1_f7_release.jsonl",
        "source_artifact_sha256": observed_source_sha,
        "release_report": "reports/m6_f7_release.json",
        "rows": rows,
        "unique_ids": len(ids),
        "intent_count": len(intents),
        "train_sha256": sha256_file(train_path),
        "license": "CC-BY-4.0",
        "upstream": "AmazonScience/massive (zh-TW)",
        "teacher_model": "qwen3.6:27b",
        "filters": "F1-F7",
    }
    _write_json(dataset_root / "release_manifest.json", manifest)
    return manifest


def _build_model_bundle(model_root: Path) -> dict[str, Any]:
    model_root.mkdir(parents=True)
    for name in sorted(MODEL_SOURCE_FILES - {"adapter_config.json"}):
        shutil.copy2(ADAPTER_DIR / name, model_root / name)
    config = sanitize_adapter_config(_load_json(ADAPTER_DIR / "adapter_config.json"))
    _write_json(model_root / "adapter_config.json", config)
    _copy_card("model_README.md", model_root / "README.md")
    (model_root / "LICENSE").write_text(MODEL_LICENSE, encoding="utf-8", newline="\n")

    with safe_open(model_root / "adapter_model.safetensors", framework="pt") as handle:
        tensor_count = len(handle.keys())
    if tensor_count != 686:
        raise ValueError(f"Expected 686 adapter tensors, observed {tensor_count}")
    PeftConfig.from_pretrained(model_root)
    return {
        "schema_version": 1,
        "repo_id": MODEL_REPO_ID,
        "source_commit": source_commit(),
        "base_model": BASE_MODEL_ID,
        "adapter_sha256": sha256_file(model_root / "adapter_model.safetensors"),
        "adapter_bytes": (model_root / "adapter_model.safetensors").stat().st_size,
        "tensor_count": tensor_count,
        "license": "Apache-2.0",
        "training_group": "real_syn_filtered",
        "seed": 42,
    }


def verify_bundle(output_root: Path) -> dict[str, Any]:
    """Verify allowlists, hashes, cards, rows, and adapter metadata."""
    dataset_root = output_root / "dataset"
    model_root = output_root / "model"
    dataset_files = _relative_file_set(dataset_root)
    model_files = _relative_file_set(model_root)
    if dataset_files != DATASET_FILES:
        raise ValueError(
            f"Unexpected dataset bundle files: {sorted(dataset_files ^ DATASET_FILES)}"
        )
    if model_files != MODEL_FILES:
        raise ValueError(f"Unexpected model bundle files: {sorted(model_files ^ MODEL_FILES)}")

    for root in (dataset_root, model_root):
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                assert_safe_text(
                    path.read_text(encoding="utf-8"),
                    label=path.relative_to(output_root).as_posix(),
                )

    manifest = _load_json(dataset_root / "release_manifest.json")
    train_path = dataset_root / "data" / "train.jsonl"
    if sha256_file(train_path) != manifest["train_sha256"]:
        raise ValueError("Published train JSONL digest does not match the manifest")
    rows = 0
    ids: set[str] = set()
    with train_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            rows += 1
            ids.add(str(payload["id"]))
    if rows != int(manifest["rows"]) or len(ids) != rows:
        raise ValueError("Published train JSONL count or uniqueness check failed")

    config = _load_json(model_root / "adapter_config.json")
    if config.get("base_model_name_or_path") != BASE_MODEL_ID:
        raise ValueError("Adapter base model does not point to the public Gemma 4 repository")
    with safe_open(model_root / "adapter_model.safetensors", framework="pt") as handle:
        tensor_count = len(handle.keys())
    if tensor_count != 686:
        raise ValueError("Adapter safetensors tensor count changed")
    PeftConfig.from_pretrained(model_root)

    return {
        "status": "ready_for_private_upload",
        "dataset_repo_id": DATASET_REPO_ID,
        "model_repo_id": MODEL_REPO_ID,
        "dataset_rows": rows,
        "dataset_sha256": manifest["train_sha256"],
        "dataset_files": sorted(dataset_files),
        "model_files": sorted(model_files),
        "adapter_sha256": sha256_file(model_root / "adapter_model.safetensors"),
        "adapter_tensor_count": tensor_count,
        "source_commit": source_commit(),
        "visibility": "private",
    }


def prepare_release(output_root: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    """Build both bundles and return their verified upload plan."""
    _safe_reset_output(output_root)
    _build_dataset_bundle(output_root / "dataset")
    model_manifest = _build_model_bundle(output_root / "model")
    plan = verify_bundle(output_root)
    plan["adapter_bytes"] = model_manifest["adapter_bytes"]
    _write_json(output_root / "release_plan.json", plan)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Bundle root; must remain under this repository's outputs directory.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify an existing bundle without rebuilding it.",
    )
    args = parser.parse_args()
    plan = verify_bundle(args.output) if args.verify_only else prepare_release(args.output)
    print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
