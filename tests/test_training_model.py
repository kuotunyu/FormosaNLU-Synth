from __future__ import annotations

import re

from src.training.model import TEXT_CHECKPOINT_KEY_MAPPING


def test_multimodal_language_prefix_maps_to_causal_lm_prefix() -> None:
    source, target = next(iter(TEXT_CHECKPOINT_KEY_MAPPING.items()))
    key = "model.language_model.layers.0.self_attn.q_proj.weight"
    assert re.sub(source, target, key) == "model.layers.0.self_attn.q_proj.weight"
    assert re.sub(source, target, "model.vision_tower.weight") == ("model.vision_tower.weight")
