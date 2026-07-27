"""Write local-only top BGE-M3 matches for M5 threshold review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.filtering.calibrate import _load_eval, _load_pilot
from src.synthetic.planning import load_seed_pool

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PILOT = REPO_ROOT / "data" / "filtered" / "pilot_f1_f4.jsonl"
DEFAULT_EMBEDDINGS = REPO_ROOT / "data" / "embeddings" / "m5_pilot_bge_m3.npz"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "embeddings" / "m5_top_similarity_pairs.json"


def top_matches(
    query_embeddings: np.ndarray,
    reference_embeddings: np.ndarray,
    query_ids: list[str],
    query_texts: list[str],
    reference_ids: list[str],
    reference_texts: list[str],
    *,
    exclude_self: bool,
    limit: int,
    largest: bool = True,
) -> list[dict]:
    similarities = query_embeddings @ reference_embeddings.T
    if exclude_self:
        if query_ids != reference_ids:
            raise ValueError("Self-exclusion requires identical ordered ids")
        np.fill_diagonal(similarities, -np.inf)
    best_reference = np.argmax(similarities, axis=1)
    best_scores = similarities[np.arange(len(query_embeddings)), best_reference]
    order = np.argsort(best_scores)
    if largest:
        order = order[::-1]
    order = order[:limit]
    return [
        {
            "similarity": float(best_scores[index]),
            "query_id": query_ids[index],
            "query_text": query_texts[index],
            "reference_id": reference_ids[best_reference[index]],
            "reference_text": reference_texts[best_reference[index]],
            "text_equal": query_texts[index] == reference_texts[best_reference[index]],
        }
        for index in order
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--embeddings", type=Path, default=DEFAULT_EMBEDDINGS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    pilot_ids, pilot_texts = _load_pilot(args.pilot)
    seeds = list(load_seed_pool().flat)
    seed_ids = [seed["id"] for seed in seeds]
    seed_texts = [seed["utt"] for seed in seeds]
    eval_ids, eval_texts = _load_eval()
    with np.load(args.embeddings) as archive:
        payload = {
            "nearest_other_synthetic": top_matches(
                archive["pilot_embeddings"],
                archive["pilot_embeddings"],
                pilot_ids,
                pilot_texts,
                pilot_ids,
                pilot_texts,
                exclude_self=True,
                limit=args.limit,
            ),
            "nearest_seed": top_matches(
                archive["pilot_embeddings"],
                archive["seed_embeddings"],
                pilot_ids,
                pilot_texts,
                seed_ids,
                seed_texts,
                exclude_self=False,
                limit=args.limit,
            ),
            "farthest_from_seed": top_matches(
                archive["pilot_embeddings"],
                archive["seed_embeddings"],
                pilot_ids,
                pilot_texts,
                seed_ids,
                seed_texts,
                exclude_self=False,
                limit=args.limit,
                largest=False,
            ),
            "nearest_eval": top_matches(
                archive["pilot_embeddings"],
                archive["eval_embeddings"],
                pilot_ids,
                pilot_texts,
                eval_ids,
                eval_texts,
                exclude_self=False,
                limit=args.limit,
            ),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
