"""Lazy production adapter for the selected BAAI/bge-m3 embedding model."""

from __future__ import annotations

from typing import Any

import numpy as np


class BgeM3Backend:
    """Load BGE-M3 only when M5 calibration is explicitly run."""

    model_name = "BAAI/bge-m3"

    def __init__(
        self,
        *,
        local_files_only: bool = True,
        device: str = "cuda",
        batch_size: int = 64,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed; install the locked M5 dependency"
            ) from exc
        self._model: Any = SentenceTransformer(
            self.model_name,
            device=device,
            local_files_only=local_files_only,
        )
        self._batch_size = batch_size

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
            convert_to_numpy=True,
        )
        return np.asarray(vectors, dtype=np.float32)

