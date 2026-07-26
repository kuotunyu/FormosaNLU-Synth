"""Procedural slot replacement followed by teacher fluency repair."""

from __future__ import annotations

from typing import Any

from src.synthetic.recipes.base import (
    STYLE_GUIDES,
    RecipePlan,
    compact_json,
    render_prompt,
    slot_pairs,
)
from src.synthetic.schema import StyleName

PROMPT_VERSION = "slot_substitution.v1"


def substitute_seed(
    seed: dict[str, Any],
    replacement: tuple[str, str, str],
) -> dict[str, Any]:
    """Replace one exact slot value in code; the model never chooses the label."""
    slot_type, old_value, new_value = replacement
    if not new_value or old_value == new_value:
        raise ValueError("Replacement slot value must be non-empty and different")
    if old_value not in seed["utt"]:
        raise ValueError(f"Slot value {old_value!r} is not an exact substring of the seed")

    replaced = False
    slots: list[dict[str, str]] = []
    for slot in seed["slots"]:
        if not replaced and slot["type"] == slot_type and slot["value"] == old_value:
            slots.append({"type": slot_type, "value": new_value})
            replaced = True
        else:
            slots.append(dict(slot))
    if not replaced:
        raise ValueError("Requested source slot was not found")

    return {
        "id": seed["id"],
        "utt": seed["utt"].replace(old_value, new_value, 1),
        "intent": seed["intent"],
        "slots": slots,
    }


def build_slot_substitution(
    seed: dict[str, Any],
    style: StyleName,
    replacement: tuple[str, str, str],
) -> RecipePlan:
    draft = substitute_seed(seed, replacement)
    return RecipePlan(
        recipe="slot_substitution",
        prompt_version=PROMPT_VERSION,
        style=style,
        system_prompt=(
            "You repair fluency after a programmatic slot substitution. "
            "Never alter labels or literal slot values. Return JSON only."
        ),
        user_prompt=render_prompt(
            "slot_substitution.v1.md",
            {
                "STYLE_GUIDE": STYLE_GUIDES[style],
                "DRAFT_JSON": compact_json(draft),
            },
        ),
        expected_intent=draft["intent"],
        expected_slots=slot_pairs(draft),
        seed_sample_id=seed["id"],
    )

