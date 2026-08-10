from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch
from safetensors.torch import save_file

from scripts.phi_hf_release import (
    BASE_MODEL_ID,
    BASE_MODEL_REVISION,
    PHI_MODEL_FILES,
    build_phi_bundle,
    sanitize_phi_adapter_config,
    verify_phi_bundle,
)


def _write_fake_adapter(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "adapter_config.json").write_text(
        json.dumps(
            {
                "base_model_name_or_path": r"C:\Users\example\Phi-4-mini-instruct",
                "peft_type": "LORA",
                "task_type": "CAUSAL_LM",
                "r": 16,
                "lora_alpha": 32,
                "target_modules": ["qkv_proj"],
            }
        ),
        encoding="utf-8",
    )
    save_file({"adapter.layer.weight": torch.ones(2, 2)}, root / "adapter_model.safetensors")
    (root / "chat_template.jinja").write_text("{{ messages }}\n", encoding="utf-8")
    (root / "tokenizer.json").write_text('{"version":"1.0"}\n', encoding="utf-8")
    (root / "tokenizer_config.json").write_text("{}\n", encoding="utf-8")
    (root / "training_args.bin").write_bytes(b"must not ship")
    return root


def test_sanitize_phi_adapter_config_removes_local_path_and_pins_revision() -> None:
    original = {
        "base_model_name_or_path": r"C:\Users\example\Phi-4-mini-instruct",
        "revision": None,
        "peft_type": "LORA",
    }

    sanitized = sanitize_phi_adapter_config(original)

    assert sanitized["base_model_name_or_path"] == BASE_MODEL_ID
    assert sanitized["revision"] == BASE_MODEL_REVISION
    assert sanitized["peft_type"] == "LORA"
    assert original["base_model_name_or_path"].startswith("C:")


def test_build_phi_bundle_copies_only_public_allowlist_and_records_hashes(
    tmp_path: Path,
) -> None:
    source = _write_fake_adapter(tmp_path / "source")
    card = tmp_path / "README.md"
    card.write_text(
        "---\nlicense: mit\nbase_model: microsoft/Phi-4-mini-instruct\n---\n", encoding="utf-8"
    )
    output = tmp_path / "outputs" / "phi"

    report = build_phi_bundle(
        source_dir=source,
        card_path=card,
        output_dir=output,
        allowed_output_root=tmp_path / "outputs",
        source_commit="a" * 40,
        expected_tensor_count=1,
    )

    assert {path.name for path in output.iterdir()} == PHI_MODEL_FILES
    assert "training_args.bin" not in PHI_MODEL_FILES
    assert (
        report["adapter_sha256"]
        == json.loads((output / "release_manifest.json").read_text(encoding="utf-8"))[
            "adapter_sha256"
        ]
    )
    assert r"C:\Users" not in (output / "adapter_config.json").read_text(encoding="utf-8")


def test_verify_phi_bundle_rejects_unexpected_file(tmp_path: Path) -> None:
    source = _write_fake_adapter(tmp_path / "source")
    card = tmp_path / "README.md"
    card.write_text("---\nlicense: mit\n---\n", encoding="utf-8")
    output = tmp_path / "outputs" / "phi"
    build_phi_bundle(
        source_dir=source,
        card_path=card,
        output_dir=output,
        allowed_output_root=tmp_path / "outputs",
        source_commit="b" * 40,
        expected_tensor_count=1,
    )
    (output / "checkpoint.bin").write_bytes(b"optimizer state")

    with pytest.raises(ValueError, match="Unexpected Phi bundle files"):
        verify_phi_bundle(output, expected_tensor_count=1)


def test_build_phi_bundle_refuses_to_reset_outside_allowlisted_output_root(
    tmp_path: Path,
) -> None:
    source = _write_fake_adapter(tmp_path / "source")
    card = tmp_path / "README.md"
    card.write_text("---\nlicense: mit\n---\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside the allowed outputs directory"):
        build_phi_bundle(
            source_dir=source,
            card_path=card,
            output_dir=tmp_path / "elsewhere",
            allowed_output_root=tmp_path / "outputs",
            source_commit="c" * 40,
            expected_tensor_count=1,
        )
