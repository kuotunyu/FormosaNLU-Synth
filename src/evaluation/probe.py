"""Deterministic slot-safe robustness probes derived from real Test only."""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any

from src.training.augmentation import (
    character_noise,
    slot_safe_eda,
    slots_are_grounded,
)

PROBE_KINDS = ("colloquial", "lexical", "asr_noise")


def _candidate(
    example: dict[str, Any],
    *,
    kind: str,
    seed: int,
    attempt: int,
) -> str | None:
    if kind == "colloquial":
        return slot_safe_eda(example, seed=seed, variant=2 + 4 * attempt)
    if kind == "lexical":
        return slot_safe_eda(example, seed=seed, variant=4 * attempt)
    if kind == "asr_noise":
        noisy = character_noise(example, seed=seed, variant=attempt)
        if noisy:
            return noisy
        fallback = slot_safe_eda(example, seed=seed, variant=3 + 4 * attempt)
        if fallback != example["utt"]:
            return fallback
        disfluency = ("呃", "嗯", "那個", "就是")[attempt % 4]
        return f"{disfluency}，{example['utt']}"
    raise ValueError(f"Unknown probe kind: {kind}")


def build_probe_rows(
    examples: list[dict[str, Any]],
    *,
    seed: int = 42,
) -> list[dict[str, Any]]:
    if not examples:
        raise ValueError("Robustness probe requires real Test examples")
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for example in examples:
        used_utterances = {example["utt"]}
        for kind in PROBE_KINDS:
            utterance: str | None = None
            for attempt in range(50):
                candidate = _candidate(
                    example,
                    kind=kind,
                    seed=seed,
                    attempt=attempt,
                )
                if (
                    candidate
                    and candidate not in used_utterances
                    and slots_are_grounded(example, candidate)
                ):
                    utterance = candidate
                    break
            if utterance is None:
                raise RuntimeError(
                    f"Could not build {kind} probe for Test id {example['id']}"
                )
            digest = hashlib.sha256(
                f"{seed}:{kind}:{example['id']}:{utterance}".encode()
            ).hexdigest()[:20]
            probe_id = f"probe_{digest}"
            if probe_id in seen_ids:
                raise AssertionError(f"Duplicate probe id: {probe_id}")
            seen_ids.add(probe_id)
            used_utterances.add(utterance)
            rows.append(
                {
                    "id": probe_id,
                    "source_test_id": example["id"],
                    "probe_kind": kind,
                    "utt": utterance,
                    "intent": example["intent"],
                    "slots": example["slots"],
                    "seed": seed,
                    "evaluation_only": True,
                }
            )
    return rows


def probe_summary(rows: list[dict[str, Any]], *, source_count: int) -> dict[str, Any]:
    source_ids = {row["source_test_id"] for row in rows}
    return {
        "schema_version": 1,
        "status": "ready_not_evaluated",
        "source": "MASSIVE zh-TW untouched Test labels",
        "source_count": source_count,
        "source_ids_covered": len(source_ids),
        "probe_count": len(rows),
        "probe_kinds": dict(sorted(Counter(row["probe_kind"] for row in rows).items())),
        "evaluation_only": True,
        "must_not_flow_into_training": True,
    }
