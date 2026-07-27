from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.training.data as training_data


def _row(sample_id: str, utterance: str | None = None) -> dict:
    return {
        "sample": {
            "id": sample_id,
            "utt": utterance or sample_id,
            "intent": "play_music",
            "slots": [],
        }
    }


def _write_synthetic(path: Path, ids: list[str]) -> None:
    path.write_text(
        "".join(json.dumps(_row(sample_id)) + "\n" for sample_id in ids),
        encoding="utf-8",
    )


def _write_aug(path: Path, ids: list[str]) -> None:
    path.write_text(
        "".join(
            json.dumps(
                {
                    "id": sample_id,
                    "utt": sample_id,
                    "intent": "play_music",
                    "slots": [],
                    "augmentation": {"method": "test"},
                }
            )
            + "\n"
            for sample_id in ids
        ),
        encoding="utf-8",
    )


def test_synthetic_groups_are_deterministic_and_equal_n(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = [{"id": "real", "utt": "播放音樂", "intent": "play_music", "slots": []}]
    monkeypatch.setattr(training_data, "real_only_examples", lambda: real)
    unfiltered = tmp_path / "unfiltered.jsonl"
    filtered = tmp_path / "filtered.jsonl"
    augmented = tmp_path / "aug.jsonl"
    _write_synthetic(unfiltered, [f"syn-{index}" for index in range(8)])
    _write_synthetic(filtered, ["syn-0", "syn-2", "syn-4"])
    _write_aug(augmented, ["aug-0", "aug-1", "aug-2"])

    kwargs = {
        "unfiltered_path": unfiltered,
        "filtered_path": filtered,
        "standard_aug_path": augmented,
    }
    filtered_group = training_data.group_examples("real_syn_filtered", **kwargs)
    equal_n_first = training_data.group_examples("real_syn_unfiltered_eqn", **kwargs)
    equal_n_second = training_data.group_examples("real_syn_unfiltered_eqn", **kwargs)
    standard_group = training_data.group_examples("real_std_aug", **kwargs)

    assert len(filtered_group) == len(equal_n_first) == len(standard_group) == 4
    assert equal_n_first == equal_n_second
    assert equal_n_first[0]["id"] == "real"
    assert len({row["id"] for row in equal_n_first}) == len(equal_n_first)


def test_standard_aug_count_must_match_filtered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        training_data,
        "real_only_examples",
        lambda: [{"id": "real", "utt": "播放音樂", "intent": "play_music", "slots": []}],
    )
    unfiltered = tmp_path / "unfiltered.jsonl"
    filtered = tmp_path / "filtered.jsonl"
    augmented = tmp_path / "aug.jsonl"
    _write_synthetic(unfiltered, ["syn-0", "syn-1"])
    _write_synthetic(filtered, ["syn-0", "syn-1"])
    _write_aug(augmented, ["aug-0"])
    with pytest.raises(ValueError, match="must equal"):
        training_data.group_examples(
            "real_std_aug",
            unfiltered_path=unfiltered,
            filtered_path=filtered,
            standard_aug_path=augmented,
        )
