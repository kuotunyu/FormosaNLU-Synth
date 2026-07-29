from __future__ import annotations

from scripts.prepare_phi4mini import (
    MODEL_ID,
    REVISION,
    _selected,
    build_report,
)


def test_phi_revision_and_download_selection_are_frozen() -> None:
    assert MODEL_ID == "microsoft/Phi-4-mini-instruct"
    assert REVISION == "cfbefacb99257ffa30c83adab238a50856ac3083"
    assert _selected("model-00001-of-00002.safetensors")
    assert _selected("tokenizer.json")
    assert _selected("LICENSE")
    assert not _selected("README.md")


def test_phi_artifact_report_requires_complete_local_audit() -> None:
    common = {
        "remote": {
            "model_id": MODEL_ID,
            "revision": REVISION,
            "license": "mit",
            "files": {"config.json": 1},
            "download_bytes": 1,
        },
        "disk": {
            "free_gib": 130.0,
            "projected_free_gib": 122.0,
            "minimum_free_gib": 100.0,
        },
    }
    incomplete = build_report(
        **common,
        local={"complete": False, "mismatches": ["missing"], "files": {}},
    )
    complete = build_report(
        **common,
        local={"complete": True, "mismatches": [], "files": {"config.json": {}}},
    )
    assert incomplete["status"] == "download_required"
    assert complete["status"] == "complete"
