"""Versioned synthetic-data recipes."""

from src.synthetic.recipes.base import RecipePlan
from src.synthetic.recipes.hard_negative import build_hard_negative
from src.synthetic.recipes.noise_codeswitch import build_noise_codeswitch
from src.synthetic.recipes.paraphrase import build_paraphrase
from src.synthetic.recipes.slot_substitution import build_slot_substitution

__all__ = [
    "RecipePlan",
    "build_hard_negative",
    "build_noise_codeswitch",
    "build_paraphrase",
    "build_slot_substitution",
]
