"""Taiwan-colloquial and light code-switch robustness recipe."""

from __future__ import annotations

from typing import Any

from src.synthetic.recipes.base import RecipePlan, compact_json, render_prompt, slot_pairs

PROMPT_VERSION = "noise_codeswitch.v2"


def build_noise_codeswitch(seed: dict[str, Any]) -> RecipePlan:
    return RecipePlan(
        recipe="noise_codeswitch",
        prompt_version=PROMPT_VERSION,
        style="tw_colloquial",
        system_prompt=(
            "You create realistic Taiwan Mandarin robustness examples. "
            "Labels and literal slot values are immutable. Return JSON only."
        ),
        user_prompt=render_prompt(
            "noise_codeswitch.v2.md",
            {"SEED_JSON": compact_json(seed)},
        ),
        expected_intent=seed["intent"],
        expected_slots=slot_pairs(seed),
        seed_sample_id=seed["id"],
    )
