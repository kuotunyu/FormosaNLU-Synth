"""Training/evaluation row construction from immutable local data."""

from __future__ import annotations

from typing import Any

from src.data.load_massive import decode_example, load_massive_split
from src.data.normalize import parse_annotated_utterance
from src.synthetic.planning import load_seed_pool
from src.training.prompt_template import build_prompt_completion


def _decoded_to_example(example: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_annotated_utterance(example["annot_utt"])
    return {
        "id": example["id"],
        "utt": example["utt"],
        "intent": example["intent"],
        "slots": [{"type": slot_type, "value": value} for slot_type, value in parsed.slots],
    }


def real_only_examples() -> list[dict[str, Any]]:
    return list(load_seed_pool().flat)


def full_real_examples() -> list[dict[str, Any]]:
    dataset = load_massive_split("train", download=False)
    return [_decoded_to_example(decode_example(dataset, index)) for index in range(len(dataset))]


def validation_examples(limit: int | None = None) -> list[dict[str, Any]]:
    dataset = load_massive_split("validation", download=False)
    length = len(dataset) if limit is None else min(limit, len(dataset))
    return [_decoded_to_example(decode_example(dataset, index)) for index in range(length)]


def group_examples(group: str) -> list[dict[str, Any]]:
    if group == "real_only":
        return real_only_examples()
    if group == "full_real":
        return full_real_examples()
    raise RuntimeError(f"Training group {group!r} depends on M6 filtered/unfiltered artifacts")


def prompt_completion_rows(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_prompt_completion(example) for example in examples]
