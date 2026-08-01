"""Equal-N per-recipe leave-one-out groups.

The frozen corpus carries no recipe field, but `build_generation_plans` is
deterministic and every row keeps its `generation_index`, so the recipe is
recoverable by rebuilding the plan. The mapping is checked, not assumed: each
row's expected intent must match its plan's.

Every group here holds the same number of synthetic rows. Dropping a recipe
changes both composition and size, and without holding size fixed a difference
cannot be attributed to either -- the same confound the equal-N unfiltered
control exists to remove.

Design and detectability limits are preregistered in
docs/M19_ABLATION_PROTOCOL.md.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.synthetic.planning import build_generation_plans
from src.training.data import (
    DEFAULT_FILTERED,
    deterministic_downsample,
    load_synthetic_examples,
    real_only_examples,
)

RECIPES = (
    "paraphrase",
    "slot_substitution",
    "noise_codeswitch",
    "hard_negative",
)
CONTROL_GROUP = "abl_all_eqn"
GENERATION_TOTAL = 11_264


def group_name(recipe: str) -> str:
    return f"abl_no_{recipe}"


ABLATION_GROUPS = (CONTROL_GROUP, *(group_name(recipe) for recipe in RECIPES))


@lru_cache(maxsize=1)
def _plans() -> tuple[Any, ...]:
    """Rebuilding 11,264 plans is slow and the result is deterministic."""
    return tuple(build_generation_plans(GENERATION_TOTAL))


@lru_cache(maxsize=4)
def recipe_by_row_id(filtered_path: Path = DEFAULT_FILTERED) -> dict[str, str]:
    """Map each frozen corpus row id to the recipe that produced it.

    Raises if a row's plan does not agree with its recorded intent, so a silent
    misalignment between corpus and rebuilt plan cannot pass as a valid mapping.
    """
    plans = _plans()
    mapping: dict[str, str] = {}
    with filtered_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            index = row["generation_index"]
            plan = plans[index]
            expected_intent = row["expected"]["intent"]
            if plan.expected_intent != expected_intent:
                raise ValueError(
                    f"{filtered_path}:{line_number}: plan/corpus mismatch at "
                    f"generation_index {index}: plan says {plan.expected_intent!r}, "
                    f"corpus says {expected_intent!r}"
                )
            mapping[str(row["sample"]["id"])] = plan.recipe
    return mapping


def recipe_counts(filtered_path: Path = DEFAULT_FILTERED) -> dict[str, int]:
    counts = dict.fromkeys(RECIPES, 0)
    for recipe in recipe_by_row_id(filtered_path).values():
        counts[recipe] = counts.get(recipe, 0) + 1
    return counts


def equal_n_size(filtered_path: Path = DEFAULT_FILTERED) -> int:
    """The smallest leave-one-out corpus; every group is held to this size."""
    counts = recipe_counts(filtered_path)
    total = sum(counts.values())
    return total - max(counts.values())


def ablation_examples(
    group: str,
    *,
    seed: int = 42,
    filtered_path: Path = DEFAULT_FILTERED,
) -> list[dict[str, Any]]:
    if group not in ABLATION_GROUPS:
        raise ValueError(f"Unknown ablation group: {group}")

    synthetic = load_synthetic_examples(filtered_path)
    mapping = recipe_by_row_id(filtered_path)
    target = equal_n_size(filtered_path)

    if group == CONTROL_GROUP:
        pool = synthetic
    else:
        excluded = group.removeprefix("abl_no_")
        if excluded not in RECIPES:
            raise ValueError(f"Unknown recipe in group name: {group}")
        pool = [row for row in synthetic if mapping[str(row["id"])] != excluded]

    # Every group is downsampled under its own namespace, so the control is not
    # merely a superset of any leave-one-out group's rows.
    sampled = deterministic_downsample(
        pool, count=target, seed=seed, namespace=group
    )
    return [*real_only_examples(), *sampled]


def build_plan(
    *, seed: int = 42, filtered_path: Path = DEFAULT_FILTERED
) -> dict[str, Any]:
    """Describe the ablation without training anything."""
    counts = recipe_counts(filtered_path)
    target = equal_n_size(filtered_path)
    total = sum(counts.values())
    groups = {}
    for group in ABLATION_GROUPS:
        excluded = None if group == CONTROL_GROUP else group.removeprefix("abl_no_")
        available = total - (counts[excluded] if excluded else 0)
        groups[group] = {
            "excluded_recipe": excluded,
            "available_rows": available,
            "synthetic_rows": target,
            "share_removed": (counts[excluded] / total) if excluded else 0.0,
        }
    return {
        "schema_version": 1,
        "seed": seed,
        "recipe_counts": counts,
        "filtered_total": total,
        "equal_n": target,
        "groups": groups,
        "note": (
            "All groups carry the same synthetic row count, so differences "
            "reflect composition rather than volume. Detectability limits are "
            "preregistered in docs/M19_ABLATION_PROTOCOL.md."
        ),
    }
