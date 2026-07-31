from __future__ import annotations

import re

import pytest
import yaml

from src.training.model import (
    SUPPORTED_MODEL_CLASSES,
    TEXT_CHECKPOINT_KEY_MAPPING,
    load_quantized_causal_model,
)
from src.training.train import REPO_ROOT


def test_multimodal_language_prefix_maps_to_causal_lm_prefix() -> None:
    source, target = next(iter(TEXT_CHECKPOINT_KEY_MAPPING.items()))
    key = "model.language_model.layers.0.self_attn.q_proj.weight"
    assert re.sub(source, target, key) == "model.layers.0.self_attn.q_proj.weight"
    assert re.sub(source, target, "model.vision_tower.weight") == ("model.vision_tower.weight")


def test_model_loader_rejects_unregistered_class() -> None:
    with pytest.raises(ValueError, match="Unsupported causal model class"):
        load_quantized_causal_model(
            model_path=None,  # type: ignore[arg-type]
            model_class="UnreviewedRemoteCodeModel",
            quantization_config=None,
            dtype=None,
        )


def test_every_training_config_declares_a_dispatchable_model_class() -> None:
    """Training and the robustness probe both dispatch on model.class.

    A config naming a class the loader cannot handle stays silent until a model
    starts loading, which is exactly how the probe path kept using the
    Gemma-only loader after a second student family was added.
    """
    configs = sorted((REPO_ROOT / "configs").glob("train*.yaml"))
    assert configs, "expected at least one training config"

    for path in configs:
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        model_class = config.get("model", {}).get("class")
        assert model_class, f"{path.name} declares no model.class"
        assert model_class in SUPPORTED_MODEL_CLASSES, (
            f"{path.name} declares {model_class!r}, which the loader cannot "
            f"dispatch; supported: {sorted(SUPPORTED_MODEL_CLASSES)}"
        )
