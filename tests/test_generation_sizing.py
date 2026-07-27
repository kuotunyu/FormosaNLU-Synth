from __future__ import annotations

import pytest

from src.synthetic.sizing import recommend_generation_size, wilson_lower_bound


def test_wilson_lower_bound_is_conservative() -> None:
    lower = wilson_lower_bound(437, 500)
    assert lower < 437 / 500
    assert lower == pytest.approx(0.842, abs=0.001)


def test_generation_sizing_passes_or_fails_fixed_wall_gate() -> None:
    passing = recommend_generation_size(
        pilot_accepted=350,
        pilot_total=500,
        seconds_per_record=1.287466431,
    )
    assert passing.gate_passed
    assert passing.recommended_generation_rows is not None
    assert passing.recommended_generation_rows <= passing.max_generation_rows

    failing = recommend_generation_size(
        pilot_accepted=250,
        pilot_total=500,
        seconds_per_record=1.287466431,
    )
    assert not failing.gate_passed
    assert failing.recommended_generation_rows is None
