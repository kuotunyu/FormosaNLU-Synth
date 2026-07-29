from __future__ import annotations

import numpy as np
import pytest

from scripts.paired_statistics import (
    DEFAULT_SCOPE,
    exact_mcnemar,
    holm_adjust,
    validate_pair,
)


def test_validate_pair_requires_identical_expected_rows() -> None:
    baseline = [{"generation_index": 0, "expected": {"id": "a"}}]
    treatment = [{"generation_index": 0, "expected": {"id": "a"}}]
    validate_pair(baseline, treatment)

    treatment[0]["expected"] = {"id": "b"}
    with pytest.raises(ValueError, match="expected"):
        validate_pair(baseline, treatment)


def test_exact_mcnemar_counts_discordant_pairs() -> None:
    baseline = np.asarray([True, True, False, False, False])
    treatment = np.asarray([True, False, True, True, False])
    result = exact_mcnemar(baseline, treatment)

    assert result["baseline_only_correct"] == 1
    assert result["filtered_only_correct"] == 2
    assert result["discordant"] == 3
    assert result["p_value"] == 1.0


def test_holm_adjust_is_monotone_in_sorted_order() -> None:
    adjusted = holm_adjust({"a": 0.001, "b": 0.02, "c": 0.03})

    assert adjusted == {
        "a": pytest.approx(0.003),
        "b": pytest.approx(0.04),
        "c": pytest.approx(0.04),
    }


def test_default_scope_does_not_overclaim_cross_model_generalization() -> None:
    assert "does not establish cross-model" in DEFAULT_SCOPE
