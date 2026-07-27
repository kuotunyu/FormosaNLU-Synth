from __future__ import annotations

import numpy as np
import pytest

from src.filtering.similarity import (
    SimilarityThresholds,
    apply_similarity_filters,
    l2_normalize,
    nearest_nonself_distribution,
    nearest_similarity_distribution,
)

THRESHOLDS = SimilarityThresholds(
    synthetic_duplicate_max=0.95,
    seed_too_close_max=0.95,
    seed_outlier_min=0.20,
    contamination_max=0.96,
)


def test_l2_normalize_and_nearest_distribution() -> None:
    values = l2_normalize(np.array([[3.0, 4.0], [0.0, 2.0]]))
    assert np.allclose(np.linalg.norm(values, axis=1), 1.0)
    nearest = nearest_similarity_distribution(
        np.array([[1.0, 0.0]]),
        np.array([[0.0, 1.0], [1.0, 0.0]]),
    )
    assert nearest.tolist() == pytest.approx([1.0])


def test_nearest_nonself_distribution_excludes_diagonal() -> None:
    nearest = nearest_nonself_distribution(np.array([[1.0, 0.0], [0.8, 0.6], [0.0, 1.0]]))
    assert nearest.tolist() == pytest.approx([0.8, 0.8, 0.6])


def test_f5_rejects_prior_duplicate() -> None:
    decisions = apply_similarity_filters(
        np.array([[0.8, 0.6], [0.8, 0.6]]),
        np.array([[1.0, 0.0]]),
        np.array([[-1.0, 0.0]]),
        ["test-1"],
        THRESHOLDS,
    )
    assert decisions[0].passed
    assert decisions[1].reject_reason == "F5_DUP_SYNTHETIC"


def test_f5_rejects_seed_copy_and_outlier() -> None:
    seed_copy = apply_similarity_filters(
        np.array([[1.0, 0.0]]),
        np.array([[1.0, 0.0]]),
        np.array([[-1.0, 0.0]]),
        ["test-1"],
        THRESHOLDS,
    )
    assert seed_copy[0].reject_reason == "F5_DUP_SEED"

    outlier = apply_similarity_filters(
        np.array([[0.0, 1.0]]),
        np.array([[1.0, 0.0]]),
        np.array([[-1.0, 0.0]]),
        ["test-1"],
        THRESHOLDS,
    )
    assert outlier[0].reject_reason == "F5_OUTLIER_SEED"


def test_f6_rejects_contamination_and_logs_nearest_id() -> None:
    decisions = apply_similarity_filters(
        np.array([[0.0, 1.0]]),
        np.array([[0.8, 0.6]]),
        np.array([[0.0, 1.0], [-1.0, 0.0]]),
        ["validation-1", "test-2"],
        THRESHOLDS,
    )
    assert decisions[0].reject_reason == "F6_CONTAM_EVAL"
    assert decisions[0].nearest_eval_id == "validation-1"
    assert decisions[0].max_eval == pytest.approx(1.0)


def test_thresholds_reject_invalid_order() -> None:
    with pytest.raises(ValueError):
        SimilarityThresholds(
            synthetic_duplicate_max=0.95,
            seed_too_close_max=0.2,
            seed_outlier_min=0.3,
            contamination_max=0.9,
        )
