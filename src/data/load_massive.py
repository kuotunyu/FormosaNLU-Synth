"""Load the MASSIVE ``zh-TW`` configuration without dataset loading scripts.

Hugging Face Datasets 3+ no longer executes dataset scripts. MASSIVE is a
script-based repository on its main branch, so this module downloads only the
three converted Parquet shards for ``zh-TW`` from ``refs/convert/parquet``.
The targeted download avoids accidentally materializing every locale.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from datasets import Dataset, DatasetDict
from huggingface_hub import HfApi, hf_hub_download

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_ID = "AmazonScience/massive"
DATASET_REVISION = "refs/convert/parquet"
LOCALE = "zh-TW"
SPLITS = ("train", "validation", "test")
EXPECTED_ROWS = {"train": 11_514, "validation": 2_033, "test": 2_974}
EXPECTED_PARTITIONS = {"train": "train", "validation": "dev", "test": "test"}
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "raw" / "massive"


class MassiveLoadError(RuntimeError):
    """Raised when every supported MASSIVE loading route fails."""


def parquet_filename(split: str) -> str:
    """Return the Hub path for one locale/split Parquet shard."""
    if split not in SPLITS:
        raise ValueError(f"Unsupported split: {split}")
    return f"{LOCALE}/{split}/0000.parquet"


def _download_parquet_files(data_dir: Path) -> dict[str, Path]:
    """Download only the three converted ``zh-TW`` Parquet shards."""
    data_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for split in SPLITS:
        downloaded = hf_hub_download(
            repo_id=DATASET_ID,
            filename=parquet_filename(split),
            repo_type="dataset",
            revision=DATASET_REVISION,
            local_dir=data_dir,
        )
        paths[split] = Path(downloaded)
    return paths


def _existing_parquet_files(data_dir: Path) -> dict[str, Path] | None:
    paths = {split: data_dir / parquet_filename(split) for split in SPLITS}
    return paths if all(path.is_file() for path in paths.values()) else None


def ensure_parquet_files(
    data_dir: Path = DEFAULT_DATA_DIR,
    *,
    download: bool = True,
) -> dict[str, Path]:
    """Resolve local MASSIVE Parquet files, downloading them when allowed.

    Supported recovery routes are intentionally explicit:

    1. Existing targeted Parquet files under ``data/raw/massive``.
    2. Targeted Hub download from ``refs/convert/parquet``.
    3. A manually unpacked official release using the same directory contract.
    4. As a last resort, use ``datasets<3`` with the upstream loading script in
       a separate legacy environment; this environment is deliberately not
       downgraded because script execution is a larger supply-chain surface.
    """
    data_dir = data_dir.resolve()
    existing = _existing_parquet_files(data_dir)
    if existing:
        return existing
    if download:
        try:
            return _download_parquet_files(data_dir)
        except Exception as exc:
            raise MassiveLoadError(
                "Could not download targeted MASSIVE Parquet files. "
                f"Place the official shards at {data_dir / LOCALE}/<split>/0000.parquet, "
                "or use an isolated datasets<3 legacy environment. "
                f"Original error: {type(exc).__name__}: {exc}"
            ) from exc
    raise MassiveLoadError(
        f"MASSIVE files are absent under {data_dir}; rerun without --offline "
        "or place official Parquet shards there."
    )


def load_massive(
    data_dir: Path = DEFAULT_DATA_DIR,
    *,
    download: bool = True,
) -> DatasetDict:
    """Load and validate the three real MASSIVE ``zh-TW`` splits."""
    paths = ensure_parquet_files(data_dir, download=download)
    datasets = DatasetDict(
        {
            # Reading through PyArrow avoids Datasets' generated cache-lock path,
            # which can exceed Windows' legacy MAX_PATH for a deeply nested repo.
            # Hugging Face feature metadata embedded in Parquet is retained.
            split: Dataset(pq.read_table(path, memory_map=True))
            for split, path in paths.items()
        }
    )
    counts = {split: len(dataset) for split, dataset in datasets.items()}
    if counts != EXPECTED_ROWS:
        raise MassiveLoadError(f"Unexpected MASSIVE row counts: {counts}; expected {EXPECTED_ROWS}")
    for split, dataset in datasets.items():
        locales = set(dataset.unique("locale"))
        partitions = set(dataset.unique("partition"))
        if locales != {LOCALE} or partitions != {EXPECTED_PARTITIONS[split]}:
            raise MassiveLoadError(
                f"{split} contains locales={sorted(locales)} partitions={sorted(partitions)}"
            )
    return datasets


def load_massive_split(
    split: str,
    data_dir: Path = DEFAULT_DATA_DIR,
    *,
    download: bool = True,
) -> Dataset:
    """Load exactly one split, keeping train-only callers away from Val/Test."""
    if split not in SPLITS:
        raise ValueError(f"Unsupported split: {split}")
    paths = ensure_parquet_files(data_dir, download=download)
    dataset = Dataset(pq.read_table(paths[split], memory_map=True))
    if len(dataset) != EXPECTED_ROWS[split]:
        raise MassiveLoadError(
            f"Unexpected {split} row count: {len(dataset)}; expected {EXPECTED_ROWS[split]}"
        )
    locales = set(dataset.unique("locale"))
    partitions = set(dataset.unique("partition"))
    if locales != {LOCALE} or partitions != {EXPECTED_PARTITIONS[split]}:
        raise MassiveLoadError(
            f"{split} contains locales={sorted(locales)} partitions={sorted(partitions)}"
        )
    return dataset


def class_label_names(dataset: Dataset, column: str) -> list[str]:
    """Return names from a Hugging Face ClassLabel column."""
    feature = dataset.features[column]
    names = getattr(feature, "names", None)
    if not names:
        raise MassiveLoadError(f"Column {column!r} is not a ClassLabel")
    return list(names)


def decode_example(dataset: Dataset, index: int) -> dict[str, Any]:
    """Return one example with ClassLabel integers decoded to names."""
    example = dict(dataset[index])
    for column in ("scenario", "intent"):
        feature = dataset.features[column]
        example[column] = feature.int2str(example[column])
    return example


def iter_decoded(dataset: Dataset) -> Iterator[dict[str, Any]]:
    """Yield decoded examples without mutating the Arrow dataset."""
    scenario_feature = dataset.features["scenario"]
    intent_feature = dataset.features["intent"]
    for example in dataset:
        decoded = dict(example)
        decoded["scenario"] = scenario_feature.int2str(decoded["scenario"])
        decoded["intent"] = intent_feature.int2str(decoded["intent"])
        yield decoded


def resolved_revision() -> str:
    """Resolve the immutable Hub commit behind the Parquet conversion ref."""
    info = HfApi().dataset_info(DATASET_ID, revision=DATASET_REVISION)
    return info.sha


def row_counts(datasets: Mapping[str, Dataset]) -> dict[str, int]:
    """Return split row counts in stable order."""
    return {split: len(datasets[split]) for split in SPLITS}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="require existing local Parquet files",
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()
    datasets = load_massive(args.data_dir, download=not args.offline)
    print(row_counts(datasets))
    print(decode_example(datasets["train"], 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
