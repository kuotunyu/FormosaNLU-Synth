from __future__ import annotations

from pathlib import Path

import numpy as np

from src.filtering.apply_semantic import apply_semantic_filters
from src.filtering.similarity import SimilarityThresholds


def _record(sample_id: str) -> dict:
    return {
        "sample": {
            "id": sample_id,
            "provenance": {
                "filter_score": {},
                "filter_stage_passed": "F4",
                "reject_reason": None,
            },
        }
    }


def test_apply_semantic_aligns_ids_and_writes_f6_exclusion(tmp_path: Path) -> None:
    path = tmp_path / "embeddings.npz"
    np.savez(
        path,
        pilot_ids=np.asarray(["sample-1"]),
        eval_ids=np.asarray(["validation:eval-1"]),
        pilot_embeddings=np.asarray([[0.0, 1.0]], dtype=np.float32),
        seed_embeddings=np.asarray([[0.8, 0.6]], dtype=np.float32),
        eval_embeddings=np.asarray([[0.0, 1.0]], dtype=np.float32),
    )
    thresholds = SimilarityThresholds(
        synthetic_duplicate_max=0.95,
        seed_too_close_max=0.95,
        seed_outlier_min=0.2,
        contamination_max=0.96,
    )
    accepted, rejected, exclusions, reasons = apply_semantic_filters(
        [_record("sample-1")],
        path,
        thresholds,
    )
    assert not accepted
    assert rejected[0]["sample"]["provenance"]["filter_stage_passed"] == "F5"
    assert rejected[0]["sample"]["provenance"]["reject_reason"] == "F6_CONTAM_EVAL"
    assert exclusions == [
        {
            "sample_id": "sample-1",
            "similarity": 1.0,
            "matched_eval_id": "eval-1",
            "split": "validation",
        }
    ]
    assert reasons == {"F6_CONTAM_EVAL": 1}


def test_apply_semantic_marks_f5_rejection_as_only_passing_f4(tmp_path: Path) -> None:
    path = tmp_path / "embeddings.npz"
    np.savez(
        path,
        pilot_ids=np.asarray(["sample-1"]),
        eval_ids=np.asarray(["test:eval-1"]),
        pilot_embeddings=np.asarray([[0.0, 1.0]], dtype=np.float32),
        seed_embeddings=np.asarray([[0.0, 1.0]], dtype=np.float32),
        eval_embeddings=np.asarray([[1.0, 0.0]], dtype=np.float32),
    )
    thresholds = SimilarityThresholds(
        synthetic_duplicate_max=0.95,
        seed_too_close_max=0.95,
        seed_outlier_min=0.2,
        contamination_max=0.96,
    )

    accepted, rejected, exclusions, reasons = apply_semantic_filters(
        [_record("sample-1")],
        path,
        thresholds,
    )

    assert not accepted
    assert rejected[0]["sample"]["provenance"]["filter_stage_passed"] == "F4"
    assert rejected[0]["sample"]["provenance"]["reject_reason"] == "F5_DUP_SEED"
    assert not exclusions
    assert reasons == {"F5_DUP_SEED": 1}
