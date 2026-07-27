"""Deterministic slot-safe classical augmentation for the M9 control group."""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from src.data.normalize import normalize_text

_SYNONYMS: tuple[tuple[str, str], ...] = (
    ("幫我", "請"),
    ("請", "麻煩"),
    ("打開", "開啟"),
    ("關掉", "關閉"),
    ("告訴我", "跟我說"),
    ("查詢", "查一下"),
    ("搜尋", "找一下"),
    ("播放", "放"),
    ("設定", "設"),
    ("取消", "移除"),
    ("目前", "現在"),
    ("今天", "今日"),
)
_INSERTIONS = ("請", "麻煩", "可以幫我", "我想要", "幫我")
_SUFFIXES = ("一下", "好嗎", "謝謝", "可以嗎")
_DELETABLE = ("請", "麻煩", "幫我", "可以", "一下", "我想要")
_HOMOPHONES: dict[str, tuple[str, ...]] = {
    "的": ("得",),
    "得": ("的",),
    "在": ("再",),
    "再": ("在",),
    "要": ("藥",),
    "時": ("十",),
    "是": ("事",),
    "事": ("是",),
    "到": ("道",),
    "道": ("到",),
    "開": ("該",),
    "關": ("觀",),
    "音": ("因",),
    "新": ("心",),
    "星": ("新",),
}


@dataclass(frozen=True)
class ProtectedUtterance:
    utterance: str
    spans: tuple[tuple[int, int], ...]

    def is_protected(self, start: int, end: int) -> bool:
        return any(start < span_end and end > span_start for span_start, span_end in self.spans)


def _rng(seed: int, *parts: object) -> random.Random:
    encoded = ":".join(str(part) for part in (seed, *parts)).encode("utf-8")
    value = int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big")
    return random.Random(value)


def protect_slots(example: dict[str, Any]) -> ProtectedUtterance:
    utterance = str(example["utt"])
    spans: list[tuple[int, int]] = []
    cursor = 0
    for slot in example["slots"]:
        value = str(slot["value"])
        start = utterance.find(value, cursor)
        if start < 0:
            start = utterance.find(value)
        if start < 0:
            raise ValueError(f"Slot value {value!r} is not a literal span in {utterance!r}")
        end = start + len(value)
        if any(start < prior_end and end > prior_start for prior_start, prior_end in spans):
            raise ValueError(f"Overlapping slot values in {utterance!r}")
        spans.append((start, end))
        cursor = end
    return ProtectedUtterance(utterance, tuple(sorted(spans)))


def slots_are_grounded(example: dict[str, Any], utterance: str) -> bool:
    return all(str(slot["value"]) in utterance for slot in example["slots"])


def _replace_unprotected(
    protected: ProtectedUtterance,
    source: str,
    target: str,
) -> str | None:
    cursor = 0
    while True:
        start = protected.utterance.find(source, cursor)
        if start < 0:
            return None
        end = start + len(source)
        if not protected.is_protected(start, end):
            return protected.utterance[:start] + target + protected.utterance[end:]
        cursor = end


def slot_safe_eda(example: dict[str, Any], *, seed: int, variant: int) -> str | None:
    """Apply one deterministic EDA operation while never editing a slot span."""
    protected = protect_slots(example)
    rng = _rng(seed, example["id"], "eda", variant)
    operation = variant % 4

    if operation == 0:
        candidates = list(_SYNONYMS)
        rng.shuffle(candidates)
        for source, target in candidates:
            replaced = _replace_unprotected(protected, source, target)
            if replaced is not None:
                return replaced
        operation = 2

    if operation == 1:
        candidates = list(_DELETABLE)
        rng.shuffle(candidates)
        for phrase in candidates:
            replaced = _replace_unprotected(protected, phrase, "")
            if replaced is not None and replaced.strip("，。！？、 "):
                return replaced
        operation = 3

    if operation == 2:
        if rng.random() < 0.5:
            return f"{rng.choice(_INSERTIONS)}，{protected.utterance}"
        return f"{protected.utterance}{rng.choice(_SUFFIXES)}"

    editable_pairs = [
        index
        for index in range(len(protected.utterance) - 1)
        if not protected.is_protected(index, index + 2)
        and protected.utterance[index].isalnum()
        and protected.utterance[index + 1].isalnum()
    ]
    if not editable_pairs:
        return f"{protected.utterance}{rng.choice(_SUFFIXES)}"
    index = rng.choice(editable_pairs)
    chars = list(protected.utterance)
    chars[index], chars[index + 1] = chars[index + 1], chars[index]
    return "".join(chars)


def character_noise(example: dict[str, Any], *, seed: int, variant: int) -> str | None:
    """Replace one non-slot character with a deterministic homophone."""
    protected = protect_slots(example)
    candidates = [
        index
        for index, char in enumerate(protected.utterance)
        if char in _HOMOPHONES and not protected.is_protected(index, index + 1)
    ]
    if not candidates:
        return None
    rng = _rng(seed, example["id"], "char", variant)
    index = rng.choice(candidates)
    chars = list(protected.utterance)
    chars[index] = rng.choice(_HOMOPHONES[chars[index]])
    return "".join(chars)


def split_non_slot_segments(example: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Return alternating non-slot segments and immutable slot values."""
    protected = protect_slots(example)
    text_segments: list[str] = []
    slot_values: list[str] = []
    cursor = 0
    for start, end in protected.spans:
        text_segments.append(protected.utterance[cursor:start])
        slot_values.append(protected.utterance[start:end])
        cursor = end
    text_segments.append(protected.utterance[cursor:])
    return text_segments, slot_values


def rebuild_from_segments(text_segments: list[str], slot_values: list[str]) -> str:
    if len(text_segments) != len(slot_values) + 1:
        raise ValueError("Non-slot segments must outnumber slot values by one")
    pieces: list[str] = []
    for index, segment in enumerate(text_segments):
        pieces.append(segment)
        if index < len(slot_values):
            pieces.append(slot_values[index])
    return "".join(pieces)


def make_augmented_example(
    source: dict[str, Any],
    utterance: str,
    *,
    method: str,
    variant: int,
    seed: int,
) -> dict[str, Any] | None:
    utterance = utterance.strip()
    if not utterance or not slots_are_grounded(source, utterance):
        return None
    digest = hashlib.sha256(
        f"{seed}:{method}:{source['id']}:{variant}:{utterance}".encode()
    ).hexdigest()[:20]
    return {
        "id": f"aug_{digest}",
        "utt": utterance,
        "intent": source["intent"],
        "slots": source["slots"],
        "augmentation": {
            "method": method,
            "source_id": source["id"],
            "variant": variant,
            "seed": seed,
        },
    }


def generate_standard_augmentations(
    seeds: list[dict[str, Any]],
    *,
    target_count: int,
    seed: int,
    backtranslated: Iterable[tuple[dict[str, Any], str]] = (),
) -> list[dict[str, Any]]:
    """Build exactly ``target_count`` unique classical augmentations."""
    if target_count <= 0:
        raise ValueError("target_count must be positive")
    if not seeds:
        raise ValueError("At least one frozen seed is required")
    accepted: list[dict[str, Any]] = []
    seen = {(row["intent"], normalize_text(row["utt"])) for row in seeds}

    def add(candidate: dict[str, Any] | None) -> None:
        if candidate is None or len(accepted) >= target_count:
            return
        key = (candidate["intent"], normalize_text(candidate["utt"]))
        if key in seen:
            return
        seen.add(key)
        accepted.append(candidate)

    for variant, (source, utterance) in enumerate(backtranslated):
        add(
            make_augmented_example(
                source,
                utterance,
                method="backtranslation",
                variant=variant,
                seed=seed,
            )
        )

    attempt = 0
    max_attempts = max(target_count * 50, 10_000)
    while len(accepted) < target_count and attempt < max_attempts:
        source = seeds[attempt % len(seeds)]
        variant = attempt // len(seeds)
        method = "slot_aware_eda" if attempt % 2 == 0 else "character_noise"
        utterance = (
            slot_safe_eda(source, seed=seed, variant=variant)
            if method == "slot_aware_eda"
            else character_noise(source, seed=seed, variant=variant)
        )
        add(
            make_augmented_example(
                source,
                utterance,
                method=method,
                variant=variant,
                seed=seed,
            )
            if utterance is not None
            else None
        )
        attempt += 1
    if len(accepted) != target_count:
        raise RuntimeError(
            f"Could only create {len(accepted)}/{target_count} unique slot-safe augmentations"
        )
    return accepted


def translate_non_slot_segments(
    examples: list[dict[str, Any]],
    translate: Callable[[list[str]], list[str]],
) -> list[tuple[dict[str, Any], str]]:
    """Round-trip only non-slot segments, then restore immutable slot values."""
    flattened: list[str] = []
    layouts: list[tuple[dict[str, Any], list[str], list[int | None]]] = []
    for example in examples:
        segments, slots = split_non_slot_segments(example)
        indices: list[int | None] = []
        for segment in segments:
            if segment.strip():
                indices.append(len(flattened))
                flattened.append(segment)
            else:
                indices.append(None)
        layouts.append((example, slots, indices))
    translated = translate(flattened) if flattened else []
    if len(translated) != len(flattened):
        raise ValueError("Translator output count differs from input count")
    results: list[tuple[dict[str, Any], str]] = []
    for example, slots, indices in layouts:
        segments = [translated[index] if index is not None else "" for index in indices]
        rebuilt = rebuild_from_segments(segments, slots)
        if slots_are_grounded(example, rebuilt):
            results.append((example, rebuilt))
    return results
