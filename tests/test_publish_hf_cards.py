from __future__ import annotations

from dataclasses import replace

import pytest

from scripts.publish_hf_cards import (
    RemoteSnapshot,
    assert_safe_delta,
    validate_confirmation,
)

DATA_SHA = "c65d7209d953e144299625f6a9224b98557b2677d55258a463a2992e5acf4665"
ADAPTER_SHA = "f70f423814dcd47943c92c0beb8b08a4e7f65e60a44355d3dcd95bed9f0bd60a"


def snapshot(
    *,
    dataset_sha: str = DATA_SHA,
    adapter_sha: str = ADAPTER_SHA,
    adapter_bytes: int = 155_609_536,
) -> RemoteSnapshot:
    return RemoteSnapshot(
        files=frozenset({"README.md", "immutable.bin"}),
        revision="before",
        dataset_sha256=dataset_sha,
        adapter_sha256=adapter_sha,
        adapter_bytes=adapter_bytes,
    )


def test_card_only_delta_preserves_file_set_and_artifacts() -> None:
    before = snapshot()
    after = replace(before, revision="new-card-commit")

    assert_safe_delta(before, after)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("files", frozenset({"README.md"})),
        ("dataset_sha256", "changed"),
        ("adapter_sha256", "changed"),
        ("adapter_bytes", 1),
    ],
)
def test_rejects_dataset_adapter_or_file_set_mutation(field: str, value: object) -> None:
    before = snapshot()

    with pytest.raises(ValueError, match="immutable"):
        assert_safe_delta(before, replace(before, **{field: value}))


def test_execute_requires_exact_confirmation() -> None:
    assert validate_confirmation("HF-CARDS-V1.2.1") is None
    with pytest.raises(ValueError):
        validate_confirmation("yes")
