from src.evaluation.probe import PROBE_KINDS, build_probe_rows


def test_probe_builds_three_slot_safe_variants_per_test_row() -> None:
    examples = [
        {
            "id": "test-1",
            "utt": "請播放周杰倫的歌",
            "intent": "play_music",
            "slots": [{"type": "artist_name", "value": "周杰倫"}],
        },
        {
            "id": "test-2",
            "utt": "幫我設定明天的鬧鐘",
            "intent": "alarm_set",
            "slots": [{"type": "date", "value": "明天"}],
        },
    ]
    rows = build_probe_rows(examples, seed=42)
    assert len(rows) == len(examples) * len(PROBE_KINDS)
    assert len({row["id"] for row in rows}) == len(rows)
    assert {row["probe_kind"] for row in rows} == set(PROBE_KINDS)
    assert all(
        slot["value"] in row["utt"]
        for row in rows
        for slot in row["slots"]
    )
    for example in examples:
        utterances = {
            row["utt"] for row in rows if row["source_test_id"] == example["id"]
        }
        assert len(utterances) == len(PROBE_KINDS)
