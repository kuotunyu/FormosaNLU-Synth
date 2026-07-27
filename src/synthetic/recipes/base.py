"""Shared contracts for prompt recipes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.synthetic.schema import RecipeName, StyleName

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"

STYLE_GUIDES: dict[StyleName, str] = {
    "massive_like": (
        "Use concise translated-assistant phrasing similar to the MASSIVE zh-TW corpus. "
        "Do not add Taiwan slang or code-switching."
    ),
    "tw_colloquial": (
        "Use natural contemporary Taiwan Mandarin: concise spoken particles or light "
        "code-switching are allowed, but do not change any slot value."
    ),
}


@dataclass(frozen=True)
class RecipePlan:
    """One deterministic request plan before the model is called."""

    recipe: RecipeName
    prompt_version: str
    style: StyleName
    system_prompt: str
    user_prompt: str
    expected_intent: str
    expected_slots: tuple[tuple[str, str], ...]
    seed_sample_id: str | list[str]
    pair_id: str | None = None


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def render_prompt(filename: str, replacements: dict[str, str]) -> str:
    """Render explicit double-brace placeholders and reject incomplete templates."""
    rendered = (PROMPT_DIR / filename).read_text(encoding="utf-8")
    for key, value in replacements.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    if "{{" in rendered or "}}" in rendered:
        raise ValueError(f"Unresolved placeholder in {filename}")
    return rendered.strip()


def stable_pair_id(*sample_ids: str) -> str:
    joined = "\0".join(sample_ids).encode("utf-8")
    return "pair_" + hashlib.sha256(joined).hexdigest()[:16]


def slot_pairs(seed: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple((slot["type"], slot["value"]) for slot in seed["slots"])
