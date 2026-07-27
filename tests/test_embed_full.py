from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from src.filtering.embed_full import load_corpus, load_frozen_references


def test_load_corpus_requires_unique_ids_and_nonempty_text(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        "\n".join(
            [
                json.dumps({"sample": {"id": "a", "utt": "播放音樂"}}),
                json.dumps({"sample": {"id": "b", "utt": "設定鬧鐘"}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert load_corpus(corpus) == (["a", "b"], ["播放音樂", "設定鬧鐘"])

    corpus.write_text(
        "\n".join(
            [
                json.dumps({"sample": {"id": "a", "utt": "播放音樂"}}),
                json.dumps({"sample": {"id": "a", "utt": "設定鬧鐘"}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_corpus(corpus)


def test_load_frozen_references_validates_alignment(tmp_path: Path) -> None:
    archive = tmp_path / "references.npz"
    np.savez(
        archive,
        seed_ids=np.asarray(["seed"]),
        eval_ids=np.asarray(["test:1"]),
        seed_embeddings=np.asarray([[1.0, 0.0]], dtype=np.float32),
        eval_embeddings=np.asarray([[0.0, 1.0]], dtype=np.float32),
    )
    seed_ids, eval_ids, seed_vectors, eval_vectors = load_frozen_references(archive)
    assert seed_ids.tolist() == ["seed"]
    assert eval_ids.tolist() == ["test:1"]
    assert seed_vectors.shape == (1, 2)
    assert eval_vectors.shape == (1, 2)
