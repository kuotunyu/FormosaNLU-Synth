from __future__ import annotations

import pytest

from scripts.verify_publication import validate_phi_evidence


def _valid() -> dict[str, object]:
    return {
        "files": {
            ".gitattributes",
            "LICENSE",
            "README.md",
            "adapter_config.json",
            "adapter_model.safetensors",
            "chat_template.jinja",
            "release_manifest.json",
            "tokenizer.json",
            "tokenizer_config.json",
        },
        "private": False,
        "license_id": "mit",
        "base_model": "microsoft/Phi-4-mini-instruct",
        "base_model_revision": "cfbefacb99257ffa30c83adab238a50856ac3083",
        "adapter_sha256": (
            "e9e4c77d79eb12da8cba64a7a484d260f753d000396752f51159e3c0f4e34376"
        ),
        "adapter_bytes": 92_309_112,
        "adapter_tensor_count": 256,
    }


def test_validate_phi_evidence_accepts_exact_public_artifact() -> None:
    evidence = validate_phi_evidence(**_valid())

    assert evidence["visibility"] == "public"
    assert evidence["license"] == "mit"
    assert evidence["adapter_bytes"] == 92_309_112
    assert evidence["adapter_tensor_count"] == 256


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("private", True, "public"),
        ("license_id", "apache-2.0", "license"),
        ("base_model", "wrong/model", "base model"),
        ("base_model_revision", "main", "revision"),
        ("adapter_sha256", "0" * 64, "SHA-256"),
        ("adapter_bytes", 1, "byte"),
        ("adapter_tensor_count", 1, "tensor"),
        ("files", {"README.md"}, "files"),
    ],
)
def test_validate_phi_evidence_rejects_publication_drift(
    field: str,
    value: object,
    message: str,
) -> None:
    payload = _valid()
    payload[field] = value

    with pytest.raises(ValueError, match=message):
        validate_phi_evidence(**payload)
