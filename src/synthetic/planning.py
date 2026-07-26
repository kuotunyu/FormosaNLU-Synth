"""Deterministic generation planning from frozen train-only seeds."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.data.load_massive import DEFAULT_DATA_DIR, decode_example, load_massive_split
from src.data.normalize import parse_annotated_utterance
from src.synthetic.recipes import (
    RecipePlan,
    build_hard_negative,
    build_noise_codeswitch,
    build_paraphrase,
    build_slot_substitution,
)
from src.synthetic.recipes.hard_negative import CONFUSION_PAIRS

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "splits" / "manifest.json"
RECIPE_WEIGHTS = {
    "paraphrase": 0.35,
    "slot_substitution": 0.30,
    "noise_codeswitch": 0.20,
    "hard_negative": 0.15,
}


@dataclass(frozen=True)
class SeedPool:
    """Only the immutable train_20shot split; Val/Test are never loaded here."""

    by_intent: dict[str, list[dict[str, Any]]]
    flat: list[dict[str, Any]]


def _seed_from_example(example: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_annotated_utterance(example["annot_utt"])
    return {
        "id": example["id"],
        "utt": example["utt"],
        "intent": example["intent"],
        "slots": [
            {"type": slot_type, "value": slot_value}
            for slot_type, slot_value in parsed.slots
        ],
    }


def load_seed_pool(
    manifest_path: Path = DEFAULT_MANIFEST,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> SeedPool:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = manifest["splits"]["train_20shot_by_intent"]
    dataset = load_massive_split("train", data_dir, download=False)
    index_by_id = {sample_id: index for index, sample_id in enumerate(dataset["id"])}

    by_intent: dict[str, list[dict[str, Any]]] = {}
    flat: list[dict[str, Any]] = []
    for intent in sorted(selected):
        seeds = [
            _seed_from_example(decode_example(dataset, index_by_id[sample_id]))
            for sample_id in selected[intent]
        ]
        by_intent[intent] = seeds
        flat.extend(seeds)
    if len(flat) != manifest["counts"]["train_20shot"]:
        raise ValueError("Seed-pool size differs from frozen manifest")
    return SeedPool(by_intent=by_intent, flat=flat)


def _allocate_counts(total: int) -> dict[str, int]:
    if total <= 0:
        raise ValueError("Generation count must be positive")
    raw = {name: total * weight for name, weight in RECIPE_WEIGHTS.items()}
    allocated = {name: int(value) for name, value in raw.items()}
    remainder = total - sum(allocated.values())
    order = sorted(raw, key=lambda name: (raw[name] - allocated[name], name), reverse=True)
    for name in order[:remainder]:
        allocated[name] += 1
    return allocated


def _substitution_candidates(
    pool: SeedPool,
) -> list[tuple[dict[str, Any], tuple[str, str, str]]]:
    value_bank: dict[str, list[str]] = {}
    for seed in pool.flat:
        for slot in seed["slots"]:
            values = value_bank.setdefault(slot["type"], [])
            if slot["value"] not in values:
                values.append(slot["value"])

    candidates: list[tuple[dict[str, Any], tuple[str, str, str]]] = []
    for seed in pool.flat:
        for slot in seed["slots"]:
            old_value = slot["value"]
            if old_value not in seed["utt"]:
                continue
            replacement = next(
                (
                    value
                    for value in value_bank[slot["type"]]
                    if value != old_value and value not in seed["utt"]
                ),
                None,
            )
            if replacement is not None:
                candidates.append(
                    (seed, (slot["type"], old_value, replacement))
                )
                break
    if not candidates:
        raise ValueError("No grounded slot-substitution candidates")
    return candidates


def build_generation_plans(
    total: int,
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    data_dir: Path = DEFAULT_DATA_DIR,
    schedule_seed: int = 42,
) -> list[RecipePlan]:
    """Build a reproducible recipe mix whose counts sum exactly to total."""
    pool = load_seed_pool(manifest_path, data_dir)
    counts = _allocate_counts(total)
    plans: list[RecipePlan] = []

    for index in range(counts["paraphrase"]):
        style = "massive_like" if index % 2 == 0 else "tw_colloquial"
        plans.append(build_paraphrase(pool.flat[index % len(pool.flat)], style))

    substitutions = _substitution_candidates(pool)
    for index in range(counts["slot_substitution"]):
        seed, replacement = substitutions[index % len(substitutions)]
        style = "massive_like" if index % 2 == 0 else "tw_colloquial"
        plans.append(build_slot_substitution(seed, style, replacement))

    for index in range(counts["noise_codeswitch"]):
        plans.append(build_noise_codeswitch(pool.flat[(index + 311) % len(pool.flat)]))

    for index in range(counts["hard_negative"]):
        anchor_intent, target_intent = CONFUSION_PAIRS[index % len(CONFUSION_PAIRS)]
        cycle = index // len(CONFUSION_PAIRS)
        anchor = pool.by_intent[anchor_intent][cycle % len(pool.by_intent[anchor_intent])]
        target = pool.by_intent[target_intent][cycle % len(pool.by_intent[target_intent])]
        style = "massive_like" if index % 2 == 0 else "tw_colloquial"
        plans.append(build_hard_negative(anchor, target, style))

    random.Random(schedule_seed).shuffle(plans)
    if len(plans) != total:
        raise AssertionError(f"Planned {len(plans)} requests, expected {total}")
    return plans
