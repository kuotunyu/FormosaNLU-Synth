"""Label-preserving paraphrase recipe."""

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

PROMPT_VERSION = "paraphrase.v2"


def build_paraphrase(seed: dict[str, Any], style: StyleName) -> RecipePlan:
    return RecipePlan(
        recipe="paraphrase",
        prompt_version=PROMPT_VERSION,
        style=style,
        system_prompt=(
            "You create label-preserving Traditional Chinese NLU examples. "
            "Return only the requested JSON object."
        ),
        user_prompt=render_prompt(
            "paraphrase.v2.md",
            {
                "STYLE_GUIDE": STYLE_GUIDES[style],
                "SEED_JSON": compact_json(seed),
            },
        ),
        expected_intent=seed["intent"],
        expected_slots=slot_pairs(seed),
        seed_sample_id=seed["id"],
    )
