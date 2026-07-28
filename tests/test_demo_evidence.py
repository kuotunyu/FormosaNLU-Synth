from __future__ import annotations

from scripts.capture_demo_evidence import build_report, capture
from src.inference.demo import MockComparisonRuntime


def test_mock_capture_preserves_base_and_adapted_outputs(tmp_path) -> None:
    rows = capture(MockComparisonRuntime(), ("搜尋周杰倫的歌",))
    assert rows[0]["base"]["intent"] == "play_music"
    assert rows[0]["adapted"]["intent"] == "music_query"
    report = build_report(
        rows=rows,
        adapter_dir=tmp_path,
        runtime_mode="mock",
        gpu=None,
    )
    assert report["status"] == "mock_validation"
    assert report["unconstrained_decoding"] is True
