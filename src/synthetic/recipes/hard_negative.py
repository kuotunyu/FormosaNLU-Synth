"""Minimal-pair hard-negative recipe across confusable intents."""

from __future__ import annotations

from typing import Any

from src.synthetic.recipes.base import (
    STYLE_GUIDES,
    RecipePlan,
    compact_json,
    render_prompt,
    slot_pairs,
    stable_pair_id,
)
from src.synthetic.schema import StyleName

PROMPT_VERSION = "hard_negative.v2"

CONFUSION_PAIRS = (
    ("alarm_query", "alarm_set"),
    ("calendar_query", "calendar_set"),
    ("lists_query", "lists_createoradd"),
    ("takeaway_query", "takeaway_order"),
    ("music_query", "play_music"),
    ("transport_query", "transport_ticket"),
    ("recommendation_locations", "recommendation_events"),
    ("datetime_query", "datetime_convert"),
)


def build_hard_negative(
    anchor_seed: dict[str, Any],
    target_seed: dict[str, Any],
    style: StyleName,
) -> RecipePlan:
    if anchor_seed["intent"] == target_seed["intent"]:
        raise ValueError("Hard-negative seeds must have different intents")
    ids = [anchor_seed["id"], target_seed["id"]]
    return RecipePlan(
        recipe="hard_negative",
        prompt_version=PROMPT_VERSION,
        style=style,
        system_prompt=(
            "You create minimal-pair NLU examples for confusable intents. "
            "The target labels are authoritative. Return JSON only."
        ),
        user_prompt=render_prompt(
            "hard_negative.v2.md",
            {
                "STYLE_GUIDE": STYLE_GUIDES[style],
                "ANCHOR_JSON": compact_json(anchor_seed),
                "TARGET_JSON": compact_json(target_seed),
            },
        ),
        expected_intent=target_seed["intent"],
        expected_slots=slot_pairs(target_seed),
        seed_sample_id=ids,
        pair_id=stable_pair_id(*ids),
    )
