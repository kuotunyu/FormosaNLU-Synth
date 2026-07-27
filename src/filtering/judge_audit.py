"""Deterministic F7 audit selection for the full F1-F6 corpus."""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from pathlib import Path
from typing import Any

SYNTHETIC_DUPLICATE_MAX = 0.999
SEED_TOO_CLOSE_MAX = 0.995
SEED_OUTLIER_MIN = 0.650
CONTAMINATION_MAX = 0.990


def stable_rank(record: dict[str, Any], *, seed: int, namespace: str) -> str:
    sample_id = record["sample"]["id"]
    return hashlib.sha256(f"{seed}:{namespace}:{sample_id}".encode()).hexdigest()


def boundary_margin(record: dict[str, Any]) -> float:
    """Return the smallest distance to an F5/F6 decision boundary."""
    scores = record["sample"]["provenance"]["filter_score"]
    margins = [
        SYNTHETIC_DUPLICATE_MAX - float(scores["f5_max_prior_synthetic"]),
        SEED_TOO_CLOSE_MAX - float(scores["f5_max_seed"]),
        float(scores["f5_max_seed"]) - SEED_OUTLIER_MIN,
        CONTAMINATION_MAX - float(scores["f6_max_eval"]),
    ]
    return min(margins)


def slot_count_changed(record: dict[str, Any]) -> bool:
    return len(record["sample"]["slots"]) != len(record["expected"]["slots"])


def _annotate(record: dict[str, Any], *, stratum: str, margin: float) -> dict[str, Any]:
    copied = dict(record)
    copied["f7_selection"] = {
        "stratum": stratum,
        "boundary_margin": margin,
        "slot_count_changed": slot_count_changed(record),
    }
    return copied


def select_full_audit(
    records: list[dict[str, Any]],
    *,
    fraction: float = 0.10,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Select all hard negatives, then boundary conflicts and stable random rows."""
    if not records:
        raise ValueError("F7 audit requires at least one record")
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    ids = [record["sample"]["id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("F7 source contains duplicate sample ids")

    target = math.ceil(len(records) * fraction)
    hard = [
        record
        for record in records
        if record["sample"]["provenance"]["recipe"] == "hard_negative"
    ]
    hard.sort(key=lambda row: stable_rank(row, seed=seed, namespace="hard"))
    target = max(target, len(hard))
    hard_ids = {record["sample"]["id"] for record in hard}
    remaining = [record for record in records if record["sample"]["id"] not in hard_ids]
    open_slots = target - len(hard)
    conflict_count = math.ceil(open_slots / 2)
    remaining.sort(
        key=lambda row: (
            not slot_count_changed(row),
            boundary_margin(row),
            stable_rank(row, seed=seed, namespace="conflict"),
        )
    )
    conflicts = remaining[:conflict_count]
    conflict_ids = {record["sample"]["id"] for record in conflicts}
    random_pool = [
        record for record in remaining if record["sample"]["id"] not in conflict_ids
    ]
    random_pool.sort(key=lambda row: stable_rank(row, seed=seed, namespace="random"))
    random_rows = random_pool[: open_slots - len(conflicts)]

    selected = [
        *(_annotate(row, stratum="hard_negative", margin=boundary_margin(row)) for row in hard),
        *(
            _annotate(
                row,
                stratum="boundary_conflict",
                margin=boundary_margin(row),
            )
            for row in conflicts
        ),
        *(_annotate(row, stratum="random", margin=boundary_margin(row)) for row in random_rows),
    ]
    if len(selected) != target:
        raise AssertionError(f"F7 selection has {len(selected)} rows; expected {target}")
    if len({record["sample"]["id"] for record in selected}) != len(selected):
        raise AssertionError("F7 selection contains duplicate sample ids")
    return selected


def selection_summary(
    selected: list[dict[str, Any]],
    *,
    source: Path,
    source_count: int,
    fraction: float,
    seed: int,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "manifest_ready_gpu_not_started",
        "source": str(source),
        "source_count": source_count,
        "selection_fraction": fraction,
        "selection_seed": seed,
        "selected_count": len(selected),
        "selected_rate": len(selected) / source_count,
        "strata": dict(
            sorted(Counter(row["f7_selection"]["stratum"] for row in selected).items())
        ),
        "recipes": dict(
            sorted(
                Counter(
                    row["sample"]["provenance"]["recipe"] for row in selected
                ).items()
            )
        ),
        "styles": dict(
            sorted(Counter(row["sample"]["style"] for row in selected).items())
        ),
        "gpu_execution_started": False,
    }
