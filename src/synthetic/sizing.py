"""Conservative pilot-to-full generation sizing."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass


def wilson_lower_bound(successes: int, total: int, *, z: float = 1.96) -> float:
    """Return the two-sided 95% Wilson interval's lower acceptance bound."""
    if total <= 0 or successes < 0 or successes > total:
        raise ValueError("Successes must be between zero and a positive total")
    rate = successes / total
    denominator = 1 + z**2 / total
    center = rate + z**2 / (2 * total)
    spread = z * math.sqrt(rate * (1 - rate) / total + z**2 / (4 * total**2))
    return (center - spread) / denominator


@dataclass(frozen=True)
class GenerationSizing:
    pilot_accepted: int
    pilot_total: int
    point_acceptance_rate: float
    wilson_lower_acceptance_rate: float
    minimum_filtered_rows: int
    recommended_generation_rows: int | None
    max_generation_rows: int
    projected_hours: float | None
    gate_passed: bool

    def as_dict(self) -> dict:
        return asdict(self)


def recommend_generation_size(
    *,
    pilot_accepted: int,
    pilot_total: int,
    seconds_per_record: float,
    minimum_filtered_rows: int = 8_000,
    maximum_wall_seconds: float = 5 * 60 * 60,
) -> GenerationSizing:
    if seconds_per_record <= 0:
        raise ValueError("seconds_per_record must be positive")
    lower = wilson_lower_bound(pilot_accepted, pilot_total)
    maximum_rows = math.floor(maximum_wall_seconds / seconds_per_record)
    required = math.ceil(minimum_filtered_rows / lower) if lower > 0 else None
    gate_passed = required is not None and required <= maximum_rows
    projected_hours = required * seconds_per_record / 3600 if required is not None else None
    return GenerationSizing(
        pilot_accepted=pilot_accepted,
        pilot_total=pilot_total,
        point_acceptance_rate=pilot_accepted / pilot_total,
        wilson_lower_acceptance_rate=lower,
        minimum_filtered_rows=minimum_filtered_rows,
        recommended_generation_rows=required if gate_passed else None,
        max_generation_rows=maximum_rows,
        projected_hours=projected_hours,
        gate_passed=gate_passed,
    )
