"""Shared Traditional Chinese text normalization.

Filtering groundedness and evaluation metrics must import this exact module so
that training-time and evaluation-time comparisons cannot silently diverge.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from opencc import OpenCC

# Groundedness needs a compositional mapping: normalizing a substring on its
# own must match the same span normalized inside a sentence. Phrase-level
# Taiwan conversion can violate that property, so locale vocabulary is handled
# separately by F4 while this module uses character-level Simplified→Traditional.
_OPENCC = OpenCC("s2t")
_WHITESPACE_RE = re.compile(r"\s+")
_ANNOTATION_RE = re.compile(r"\[\s*([^\[\]:]+?)\s*:\s*(.*?)\s*\]")


@dataclass(frozen=True)
class ParsedAnnotation:
    """A MASSIVE utterance reconstructed from ``annot_utt`` plus its slots."""

    utterance: str
    slots: tuple[tuple[str, str], ...]


def normalize_text(text: str, *, convert_simplified: bool = True) -> str:
    """Normalize comparison text while preserving semantic characters.

    The order is deliberate: NFKC folds full-width forms, OpenCC converts
    simplified Chinese and Taiwan phrase variants, whitespace is removed for
    MASSIVE's inconsistent spacing, and casefold handles Latin code-switching.
    """
    normalized = unicodedata.normalize("NFKC", text)
    if convert_simplified:
        normalized = _OPENCC.convert(normalized)
    return _WHITESPACE_RE.sub("", normalized).casefold()


def contains_normalized(haystack: str, needle: str) -> bool:
    """Return whether a non-empty normalized value occurs in normalized text."""
    normalized_needle = normalize_text(needle)
    return bool(normalized_needle) and normalized_needle in normalize_text(haystack)


def parse_annotated_utterance(annotated: str) -> ParsedAnnotation:
    """Parse MASSIVE's ``[slot_type : value]`` inline annotation format."""
    cursor = 0
    utterance_parts: list[str] = []
    slots: list[tuple[str, str]] = []
    for match in _ANNOTATION_RE.finditer(annotated):
        utterance_parts.append(annotated[cursor : match.start()])
        slot_type = match.group(1).strip()
        value = match.group(2).strip()
        if not slot_type or not value:
            raise ValueError(f"Empty slot annotation in {annotated!r}")
        utterance_parts.append(value)
        slots.append((slot_type, value))
        cursor = match.end()
    utterance_parts.append(annotated[cursor:])
    reconstructed = "".join(utterance_parts)
    if "[" in reconstructed or "]" in reconstructed:
        raise ValueError(f"Unparsed bracket in annotation: {annotated!r}")
    return ParsedAnnotation(reconstructed, tuple(slots))
