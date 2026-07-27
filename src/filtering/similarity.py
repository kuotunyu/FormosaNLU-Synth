"""F5 diversity and F6 contamination decisions over precomputed embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


class EmbeddingBackend(Protocol):
    """Minimal backend interface; production uses BGE-M3, tests use fixed vectors."""

    model_name: str

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return L2-normalized embeddings shaped (len(texts), dimensions)."""


@dataclass(frozen=True)
class SimilarityThresholds:
    """Thresholds must come from inspected pilot distributions, never defaults."""

    synthetic_duplicate_max: float
    seed_too_close_max: float
    seed_outlier_min: float
    contamination_max: float

    def __post_init__(self) -> None:
        values = (
            self.synthetic_duplicate_max,
            self.seed_too_close_max,
            self.seed_outlier_min,
            self.contamination_max,
        )
        if any(value < -1 or value > 1 for value in values):
            raise ValueError("Cosine thresholds must be between -1 and 1")
        if self.seed_outlier_min >= self.seed_too_close_max:
            raise ValueError("Outlier minimum must be below too-close maximum")


@dataclass(frozen=True)
class SimilarityDecision:
    passed: bool
    reject_reason: str | None
    max_prior_synthetic: float
    max_seed: float
    max_eval: float
    nearest_eval_id: str | None


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    values = np.asarray(vectors, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError("Embeddings must be a 2D array")
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("Zero-norm embedding")
    return values / norms


def _maximum(query: np.ndarray, candidates: np.ndarray) -> float:
    if len(candidates) == 0:
        return -1.0
    return float(np.max(candidates @ query))


def apply_similarity_filters(
    synthetic_embeddings: np.ndarray,
    seed_embeddings: np.ndarray,
    eval_embeddings: np.ndarray,
    eval_ids: list[str],
    thresholds: SimilarityThresholds,
) -> list[SimilarityDecision]:
    """Apply F5 then F6, comparing F5 duplicates only to prior accepted rows."""
    synthetic = l2_normalize(synthetic_embeddings)
    seeds = l2_normalize(seed_embeddings)
    evaluation = l2_normalize(eval_embeddings)
    if len(evaluation) != len(eval_ids):
        raise ValueError("eval_ids length differs from eval embeddings")

    accepted_vectors: list[np.ndarray] = []
    decisions: list[SimilarityDecision] = []
    for vector in synthetic:
        prior = (
            np.stack(accepted_vectors)
            if accepted_vectors
            else np.empty((0, synthetic.shape[1]), dtype=np.float32)
        )
        max_prior = _maximum(vector, prior)
        max_seed = _maximum(vector, seeds)
        eval_scores = evaluation @ vector
        eval_index = int(np.argmax(eval_scores))
        max_eval = float(eval_scores[eval_index])
        nearest_eval_id = eval_ids[eval_index]

        reason: str | None = None
        if max_prior >= thresholds.synthetic_duplicate_max:
            reason = "F5_DUP_SYNTHETIC"
        elif max_seed >= thresholds.seed_too_close_max:
            reason = "F5_DUP_SEED"
        elif max_seed <= thresholds.seed_outlier_min:
            reason = "F5_OUTLIER_SEED"
        elif max_eval >= thresholds.contamination_max:
            reason = "F6_CONTAM_EVAL"
        if reason is None:
            accepted_vectors.append(vector)
        decisions.append(
            SimilarityDecision(
                passed=reason is None,
                reject_reason=reason,
                max_prior_synthetic=max_prior,
                max_seed=max_seed,
                max_eval=max_eval,
                nearest_eval_id=nearest_eval_id,
            )
        )
    return decisions


def nearest_similarity_distribution(
    query_embeddings: np.ndarray,
    reference_embeddings: np.ndarray,
) -> np.ndarray:
    """Return one nearest-reference cosine per query for pilot calibration plots."""
    queries = l2_normalize(query_embeddings)
    references = l2_normalize(reference_embeddings)
    return np.max(queries @ references.T, axis=1)


def nearest_nonself_distribution(embeddings: np.ndarray) -> np.ndarray:
    """Return each row's nearest different row for duplicate calibration."""
    vectors = l2_normalize(embeddings)
    if len(vectors) < 2:
        raise ValueError("At least two embeddings are required")
    similarities = vectors @ vectors.T
    np.fill_diagonal(similarities, -np.inf)
    return np.max(similarities, axis=1)
