"""Create or verify the deterministic low-resource split manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.data.load_massive import (
    DATASET_ID,
    DATASET_REVISION,
    DEFAULT_DATA_DIR,
    LOCALE,
    SPLITS,
    class_label_names,
    ensure_parquet_files,
    iter_decoded,
    load_massive,
    resolved_revision,
    row_counts,
)
from src.data.normalize import parse_annotated_utterance

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "splits" / "manifest.json"
SEED = 42
SHOTS_PER_INTENT = 20


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _selection_key(sample_id: str) -> str:
    return hashlib.sha256(f"{SEED}:{sample_id}".encode()).hexdigest()


def build_manifest(data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, Any]:
    """Build a content-addressed manifest from the official Parquet shards."""
    paths = ensure_parquet_files(data_dir)
    datasets = load_massive(data_dir, download=False)
    train_by_intent: dict[str, list[str]] = defaultdict(list)
    slot_types: set[str] = set()

    for split in SPLITS:
        for example in iter_decoded(datasets[split]):
            parsed = parse_annotated_utterance(example["annot_utt"])
            slot_types.update(slot_type for slot_type, _ in parsed.slots)
            if split == "train":
                train_by_intent[example["intent"]].append(example["id"])

    intents = sorted(class_label_names(datasets["train"], "intent"))
    selected: list[str] = []
    selected_by_intent: dict[str, list[str]] = {}
    available_by_intent: dict[str, int] = {}
    for intent in intents:
        ids = train_by_intent[intent]
        available_by_intent[intent] = len(ids)
        chosen = sorted(ids, key=_selection_key)[: min(SHOTS_PER_INTENT, len(ids))]
        selected_by_intent[intent] = chosen
        selected.extend(chosen)

    file_hashes = {split: _sha256_file(paths[split]) for split in SPLITS}
    combined_source_hash = hashlib.sha256(_canonical_bytes(file_hashes)).hexdigest()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset": {
            "repo_id": DATASET_ID,
            "revision": DATASET_REVISION,
            "resolved_commit": resolved_revision(),
            "locale": LOCALE,
            "parquet_sha256": file_hashes,
            "combined_sha256": combined_source_hash,
        },
        "sampling": {
            "seed": SEED,
            "shots_per_intent": SHOTS_PER_INTENT,
            "method": "sort by SHA256('<seed>:<sample_id>'), then take min(N, available)",
        },
        "counts": {
            "source": row_counts(datasets),
            "train_20shot": len(selected),
            "available_train_by_intent": available_by_intent,
        },
        "labels": {
            "intents": intents,
            "slot_types": sorted(slot_types),
        },
        "splits": {
            "train_20shot": selected,
            "train_20shot_by_intent": selected_by_intent,
            "validation": sorted(datasets["validation"]["id"]),
            "test": sorted(datasets["test"]["id"]),
        },
    }
    payload["manifest_sha256"] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return payload


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def verify_manifest(path: Path, data_dir: Path = DEFAULT_DATA_DIR) -> bool:
    """Rebuild the manifest and require byte-equivalent canonical content."""
    existing = json.loads(path.read_text(encoding="utf-8"))
    expected_hash = existing.get("manifest_sha256")
    without_hash = {key: value for key, value in existing.items() if key != "manifest_sha256"}
    actual_hash = hashlib.sha256(_canonical_bytes(without_hash)).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError(
            f"Manifest self-hash mismatch: stored={expected_hash}, recomputed={actual_hash}"
        )
    rebuilt = build_manifest(data_dir)
    if rebuilt != existing:
        raise ValueError(
            "Manifest differs from a deterministic rebuild. "
            f"stored={expected_hash}, rebuilt={rebuilt['manifest_sha256']}"
        )
    print(f"verified manifest SHA256 {expected_hash}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()
    if args.verify:
        verify_manifest(args.manifest, args.data_dir)
    else:
        manifest = build_manifest(args.data_dir)
        _write_manifest(args.manifest, manifest)
        print(f"wrote {args.manifest} ({manifest['manifest_sha256']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
