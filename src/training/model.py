"""Shared Gemma 4 text-tower loading contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

# E4B is distributed as a multimodal checkpoint. Gemma4ForCausalLM expects the
# same language weights without the intermediate `language_model` prefix.
TEXT_CHECKPOINT_KEY_MAPPING = {r"^model\.language_model\.": "model."}


def load_quantized_text_model(
    model_path: Path,
    *,
    quantization_config: Any,
    dtype: Any,
) -> Any:
    """Load only E4B's language tower, remapping the multimodal checkpoint keys."""
    from transformers import Gemma4Config, Gemma4ForCausalLM

    multimodal_config = Gemma4Config.from_pretrained(model_path)
    return Gemma4ForCausalLM.from_pretrained(
        model_path,
        config=multimodal_config.text_config,
        key_mapping=TEXT_CHECKPOINT_KEY_MAPPING,
        quantization_config=quantization_config,
        dtype=dtype,
        device_map={"": 0},
    )
