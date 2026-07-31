"""Shared quantized causal-language-model loading contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

# E4B is distributed as a multimodal checkpoint. Gemma4ForCausalLM expects the
# same language weights without the intermediate `language_model` prefix.
TEXT_CHECKPOINT_KEY_MAPPING = {r"^model\.language_model\.": "model."}

# The classes load_quantized_causal_model can dispatch. Every configs/train*.yaml
# must declare one of these, otherwise the mismatch only surfaces once a model
# starts loading -- which is how the Gemma-only loader went unnoticed in the
# probe path until a smoke run hit it.
SUPPORTED_MODEL_CLASSES = frozenset({"Gemma4ForCausalLM", "AutoModelForCausalLM"})


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


def load_quantized_causal_model(
    model_path: Path,
    *,
    model_class: str,
    quantization_config: Any,
    dtype: Any,
) -> Any:
    """Load a frozen local model without silently falling back to the network."""
    if model_class not in SUPPORTED_MODEL_CLASSES:
        raise ValueError(f"Unsupported causal model class: {model_class}")
    if model_class == "Gemma4ForCausalLM":
        return load_quantized_text_model(
            model_path,
            quantization_config=quantization_config,
            dtype=dtype,
        )
    if model_class == "AutoModelForCausalLM":
        from transformers import AutoModelForCausalLM

        return AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=quantization_config,
            dtype=dtype,
            device_map={"": 0},
            local_files_only=True,
            trust_remote_code=False,
        )
    raise ValueError(f"Unsupported causal model class: {model_class}")
