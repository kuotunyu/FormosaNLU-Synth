from __future__ import annotations

import json

import pytest

from src.inference.demo import MockComparisonRuntime, compare_utterance


def test_mock_demo_exposes_base_vs_adapted_minimal_pair() -> None:
    result = compare_utterance(
        "搜尋周杰倫的歌",
        runtime=MockComparisonRuntime(),
    )
    base_status, base_slots, base_raw, tuned_status, tuned_slots, tuned_raw = result

    assert "play_music" in base_status
    assert "music_query" in tuned_status
    assert base_slots == [["artist_name", "周杰倫"]]
    assert tuned_slots == [["artist_name", "周杰倫"]]
    assert json.loads(base_raw)["intent"] == "play_music"
    assert json.loads(tuned_raw)["intent"] == "music_query"


def test_demo_rejects_empty_utterance() -> None:
    with pytest.raises(ValueError, match="請輸入"):
        compare_utterance("  ", runtime=MockComparisonRuntime())
