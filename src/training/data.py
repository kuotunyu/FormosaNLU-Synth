"""Training/evaluation row construction from immutable local data."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.data.load_massive import decode_example, load_massive_split
from src.data.normalize import parse_annotated_utterance
from src.synthetic.planning import load_seed_pool
from src.training.prompt_template import build_prompt_completion

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UNFILTERED = REPO_ROOT / "data" / "generated" / "full_unfiltered.jsonl"
DEFAULT_FILTERED = REPO_ROOT / "data" / "filtered" / "full_f1_f6.jsonl"
DEFAULT_STANDARD_AUG = REPO_ROOT / "data" / "training" / "standard_aug.jsonl"


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


def _sample_to_example(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": sample["id"],
        "utt": sample["utt"],
        "intent": sample["intent"],
        "slots": sample["slots"],
    }


def load_synthetic_examples(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"M9 data artifact is missing: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            decoded = json.loads(line)
            sample = decoded.get("sample")
            if not isinstance(sample, dict):
                raise ValueError(f"Missing sample object at {path}:{line_number}")
            rows.append(_sample_to_example(sample))
    _require_unique_ids(rows, label=str(path))
    return rows


def load_standard_aug_examples(path: Path = DEFAULT_STANDARD_AUG) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Standard Aug artifact is missing: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            decoded = json.loads(line)
            required = {"id", "utt", "intent", "slots", "augmentation"}
            if not required.issubset(decoded):
                raise ValueError(f"Malformed Standard Aug row at {path}:{line_number}")
            rows.append(
                {
                    "id": decoded["id"],
                    "utt": decoded["utt"],
                    "intent": decoded["intent"],
                    "slots": decoded["slots"],
                }
            )
    _require_unique_ids(rows, label=str(path))
    return rows


def deterministic_downsample(
    rows: list[dict[str, Any]],
    *,
    count: int,
    seed: int,
    namespace: str,
) -> list[dict[str, Any]]:
    if count < 0 or count > len(rows):
        raise ValueError(f"Cannot sample {count} rows from {len(rows)}")

    def key(row: dict[str, Any]) -> str:
        return hashlib.sha256(f"{seed}:{namespace}:{row['id']}".encode()).hexdigest()

    return sorted(rows, key=key)[:count]


def _require_unique_ids(rows: list[dict[str, Any]], *, label: str) -> None:
    ids = [str(row["id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{label} contains duplicate ids")


def _combine(real: list[dict[str, Any]], added: list[dict[str, Any]], *, group: str) -> list:
    combined = [*real, *added]
    _require_unique_ids(combined, label=group)
    return combined


def group_examples(
    group: str,
    *,
    seed: int = 42,
    unfiltered_path: Path = DEFAULT_UNFILTERED,
    filtered_path: Path = DEFAULT_FILTERED,
    standard_aug_path: Path = DEFAULT_STANDARD_AUG,
) -> list[dict[str, Any]]:
    real = real_only_examples()
    if group == "real_only":
        return real
    if group == "full_real":
        return full_real_examples()
    filtered = load_synthetic_examples(filtered_path)
    if group == "real_syn_filtered":
        return _combine(real, filtered, group=group)
    unfiltered = load_synthetic_examples(unfiltered_path)
    if group == "real_syn_unfiltered_full":
        return _combine(real, unfiltered, group=group)
    if group == "real_syn_unfiltered_eqn":
        equal_n = deterministic_downsample(
            unfiltered,
            count=len(filtered),
            seed=seed,
            namespace=group,
        )
        return _combine(real, equal_n, group=group)
    if group == "real_std_aug":
        augmented = load_standard_aug_examples(standard_aug_path)
        if len(augmented) != len(filtered):
            raise ValueError(
                "Standard Aug additions must equal the filtered synthetic count: "
                f"{len(augmented)} != {len(filtered)}"
            )
        return _combine(real, augmented, group=group)
    if group.startswith("abl_"):
        # Imported late: ablation builds on the helpers defined here, so a
        # module-level import would be circular.
        from src.training.ablation import ABLATION_GROUPS, ablation_examples

        if group in ABLATION_GROUPS:
            return ablation_examples(group, seed=seed, filtered_path=filtered_path)
    raise ValueError(f"Unknown training group: {group}")


def prompt_completion_rows(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [build_prompt_completion(example) for example in examples]
