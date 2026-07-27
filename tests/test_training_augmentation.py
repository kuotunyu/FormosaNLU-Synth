from __future__ import annotations

from src.training.augmentation import (
    character_noise,
    generate_standard_augmentations,
    rebuild_from_segments,
    slot_safe_eda,
    split_non_slot_segments,
    translate_non_slot_segments,
)


def _seed(sample_id: str = "seed-1") -> dict:
    return {
        "id": sample_id,
        "utt": "請在下午三點播放周杰倫的歌",
        "intent": "play_music",
        "slots": [
            {"type": "time", "value": "下午三點"},
            {"type": "artist_name", "value": "周杰倫"},
        ],
    }


def test_slot_safe_eda_and_character_noise_preserve_slots() -> None:
    source = _seed()
    candidates = [
        slot_safe_eda(source, seed=42, variant=index) for index in range(8)
    ] + [character_noise(source, seed=42, variant=index) for index in range(8)]
    for candidate in (value for value in candidates if value is not None):
        assert "下午三點" in candidate
        assert "周杰倫" in candidate


def test_split_and_rebuild_protects_slot_values() -> None:
    source = _seed()
    segments, slots = split_non_slot_segments(source)
    assert slots == ["下午三點", "周杰倫"]
    assert rebuild_from_segments(segments, slots) == source["utt"]

    translated = translate_non_slot_segments(
        [source],
        lambda values: [f"譯{index}" for index, _ in enumerate(values)],
    )
    assert translated[0][1] == "譯0下午三點譯1周杰倫譯2"


def test_standard_augmentations_are_exact_unique_and_deterministic() -> None:
    seeds = [_seed("seed-1"), {**_seed("seed-2"), "utt": "幫我在下午三點播放周杰倫"}]
    first = generate_standard_augmentations(seeds, target_count=12, seed=42)
    second = generate_standard_augmentations(seeds, target_count=12, seed=42)
    assert first == second
    assert len(first) == 12
    assert len({row["id"] for row in first}) == 12
    assert all(row["augmentation"]["source_id"].startswith("seed-") for row in first)
    assert all("下午三點" in row["utt"] and "周杰倫" in row["utt"] for row in first)
