"""Versioned prompt contract shared by training and inference."""

from __future__ import annotations

import json
from typing import Any

from src.synthetic.labels import INTENTS, SLOT_TYPES

TEMPLATE_VERSION = "formosanlu_nlu.v1"
SYSTEM_PROMPT = (
    "You are a Taiwan Mandarin spoken-language NLU parser. "
    "Return exactly one JSON object with keys intent and slots. "
    "Do not use markdown or add explanations."
)


def _catalog() -> str:
    intents = ", ".join(INTENTS)
    slot_types = ", ".join(SLOT_TYPES)
    return (
        "\nAllowed intents (choose exactly one): "
        + intents
        + "\nAllowed slot types (use only when grounded in the utterance): "
        + slot_types
    )


def build_user_prompt(utterance: str, *, include_label_catalog: bool) -> str:
    if not utterance.strip():
        raise ValueError("Utterance must be non-empty")
    catalog = _catalog() if include_label_catalog else ""
    return (
        "Parse the following utterance. Slot values must be literal contiguous spans "
        "from the utterance. Use an empty slots array when no slot is present."
        f"{catalog}\nUtterance: {utterance}"
    )


def build_prompt_messages(
    utterance: str,
    *,
    zero_shot: bool,
) -> list[dict[str, str]]:
    """Build inference messages; zero-shot alone receives the label catalog."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_user_prompt(
                utterance,
                include_label_catalog=zero_shot,
            ),
        },
    ]


def target_json(intent: str, slots: list[dict[str, str]]) -> str:
    return json.dumps(
        {"intent": intent, "slots": slots},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def build_prompt_completion(
    example: dict[str, Any],
) -> dict[str, list[dict[str, str]]]:
    """TRL conversational prompt-completion row with loss only on completion."""
    return {
        "prompt": build_prompt_messages(example["utt"], zero_shot=False),
        "completion": [
            {
                "role": "assistant",
                "content": target_json(example["intent"], example["slots"]),
            }
        ],
    }
