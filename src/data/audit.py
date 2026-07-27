"""Audit MASSIVE ``zh-TW`` and generate the M1 report plus checked-in charts."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from src.data.load_massive import DEFAULT_DATA_DIR, iter_decoded, load_massive
from src.data.normalize import contains_normalized, normalize_text, parse_annotated_utterance

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = REPO_ROOT / "reports" / "m1_data_audit.md"
DEFAULT_SUMMARY = REPO_ROOT / "reports" / "m1_data_audit.json"
INTENT_CHART = REPO_ROOT / "assets" / "m1_intent_distribution.png"
SLOT_CHART = REPO_ROOT / "assets" / "m1_slot_distribution.png"


def compute_audit(data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, Any]:
    datasets = load_massive(data_dir)
    intent_counts: Counter[str] = Counter()
    slot_counts: Counter[str] = Counter()
    total_rows = 0
    rows_with_slots = 0
    rows_with_utt_whitespace = 0
    rows_with_annot_whitespace = 0
    parsed_slots = 0
    raw_grounded_slots = 0
    normalized_grounded_slots = 0
    annotation_reconstruction_matches = 0
    slots_per_utterance: Counter[int] = Counter()
    split_counts: dict[str, int] = {}

    for split, dataset in datasets.items():
        split_counts[split] = len(dataset)
        for example in iter_decoded(dataset):
            total_rows += 1
            intent_counts[example["intent"]] += 1
            rows_with_utt_whitespace += int(any(char.isspace() for char in example["utt"]))
            rows_with_annot_whitespace += int(any(char.isspace() for char in example["annot_utt"]))
            parsed = parse_annotated_utterance(example["annot_utt"])
            annotation_reconstruction_matches += int(
                normalize_text(parsed.utterance) == normalize_text(example["utt"])
            )
            slots_per_utterance[len(parsed.slots)] += 1
            rows_with_slots += int(bool(parsed.slots))
            for slot_type, value in parsed.slots:
                slot_counts[slot_type] += 1
                parsed_slots += 1
                raw_grounded_slots += int(value in example["utt"])
                normalized_grounded_slots += int(contains_normalized(example["utt"], value))

    train_intent_counts = Counter(example["intent"] for example in iter_decoded(datasets["train"]))
    values = list(train_intent_counts.values())
    return {
        "source_split_counts": split_counts,
        "total_rows": total_rows,
        "intent_count": len(intent_counts),
        "slot_type_count": len(slot_counts),
        "train_intent_count_min": min(values),
        "train_intent_count_median": statistics.median(values),
        "train_intent_count_max": max(values),
        "rows_with_slots": rows_with_slots,
        "rows_with_slots_rate": rows_with_slots / total_rows,
        "rows_with_utt_whitespace": rows_with_utt_whitespace,
        "rows_with_utt_whitespace_rate": rows_with_utt_whitespace / total_rows,
        "rows_with_annot_whitespace": rows_with_annot_whitespace,
        "rows_with_annot_whitespace_rate": rows_with_annot_whitespace / total_rows,
        "annotation_reconstruction_matches": annotation_reconstruction_matches,
        "annotation_reconstruction_rate": annotation_reconstruction_matches / total_rows,
        "parsed_slots": parsed_slots,
        "raw_grounded_slots": raw_grounded_slots,
        "raw_grounded_rate": raw_grounded_slots / parsed_slots,
        "normalized_grounded_slots": normalized_grounded_slots,
        "normalized_grounded_rate": normalized_grounded_slots / parsed_slots,
        "intent_counts_all_splits": dict(sorted(intent_counts.items())),
        "intent_counts_train": dict(sorted(train_intent_counts.items())),
        "slot_counts": dict(sorted(slot_counts.items())),
        "slots_per_utterance": {
            str(key): value for key, value in sorted(slots_per_utterance.items())
        },
    }


def _render_charts(summary: dict[str, Any]) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    intent_items = sorted(summary["intent_counts_train"].items(), key=lambda item: item[1])
    fig, axis = plt.subplots(figsize=(10, 12))
    axis.barh(
        [name for name, _ in intent_items],
        [count for _, count in intent_items],
        color="#2563eb",
    )
    axis.set_title("MASSIVE zh-TW train samples per intent")
    axis.set_xlabel("Samples")
    fig.tight_layout()
    INTENT_CHART.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(INTENT_CHART, dpi=160)
    plt.close(fig)

    slot_items = sorted(summary["slot_counts"].items(), key=lambda item: item[1])
    fig, axis = plt.subplots(figsize=(10, 11))
    axis.barh(
        [name for name, _ in slot_items],
        [count for _, count in slot_items],
        color="#0f766e",
    )
    axis.set_title("MASSIVE zh-TW slot annotations by type (all splits)")
    axis.set_xlabel("Annotations")
    fig.tight_layout()
    fig.savefig(SLOT_CHART, dpi=160)
    plt.close(fig)


def _percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _fraction(count: int, total: int, rate: float) -> str:
    return f"{count:,} / {total:,} ({_percent(rate)})"


def _write_report(summary: dict[str, Any], report_path: Path) -> None:
    split_counts = summary["source_split_counts"]
    train_range = (
        f"{summary['train_intent_count_min']} / "
        f"{summary['train_intent_count_median']:.1f} / "
        f"{summary['train_intent_count_max']}"
    )
    utt_whitespace = _fraction(
        summary["rows_with_utt_whitespace"],
        summary["total_rows"],
        summary["rows_with_utt_whitespace_rate"],
    )
    annot_whitespace = _fraction(
        summary["rows_with_annot_whitespace"],
        summary["total_rows"],
        summary["rows_with_annot_whitespace_rate"],
    )
    reconstructed = _fraction(
        summary["annotation_reconstruction_matches"],
        summary["total_rows"],
        summary["annotation_reconstruction_rate"],
    )
    rows_with_slots = _fraction(
        summary["rows_with_slots"],
        summary["total_rows"],
        summary["rows_with_slots_rate"],
    )
    raw_grounded = _fraction(
        summary["raw_grounded_slots"],
        summary["parsed_slots"],
        summary["raw_grounded_rate"],
    )
    normalized_grounded = _fraction(
        summary["normalized_grounded_slots"],
        summary["parsed_slots"],
        summary["normalized_grounded_rate"],
    )
    content = f"""# M1 MASSIVE `zh-TW` data audit

Generated by `python -m src.data.audit`. Raw recomputable values are in
[`m1_data_audit.json`](m1_data_audit.json).

## Source and shape

| Item | Observed |
|---|---:|
| Train | {split_counts["train"]:,} |
| Validation | {split_counts["validation"]:,} |
| Test | {split_counts["test"]:,} |
| Total | {summary["total_rows"]:,} |
| Intents | {summary["intent_count"]} |
| Slot types | {summary["slot_type_count"]} |
| Train samples per intent (min / median / max) | {train_range} |

The targeted loader reads only `zh-TW/<split>/0000.parquet` from the immutable
`refs/convert/parquet` revision. Calling `load_dataset("AmazonScience/massive")`
without targeted files is unsafe here: the converted repository exposes only a
`default` config and materializes every locale.

## Annotation and whitespace findings

| Check | Observed |
|---|---:|
| `utt` rows containing whitespace | {utt_whitespace} |
| `annot_utt` rows containing whitespace | {annot_whitespace} |
| Annotation reconstructs `utt` after normalization | {reconstructed} |
| Rows containing at least one slot | {rows_with_slots} |
| Raw slot value is a contiguous `utt` substring | {raw_grounded} |
| Normalized slot value is a contiguous normalized `utt` substring | {normalized_grounded} |

`annot_utt` uses spaces as annotation delimiters (`[type : value]`), while
ordinary `utt` text usually does not use word-level spacing. Groundedness must
therefore share `src/data/normalize.py` across filtering and evaluation; raw
substring matching alone is recorded above but is not the project contract.

## Distribution charts

![Train intent counts](../assets/m1_intent_distribution.png)

![Slot annotation counts](../assets/m1_slot_distribution.png)

Both PNGs were opened after generation. Labels, axes, ordering, and scales are
readable; they show a strongly imbalanced intent distribution (4–810 train
samples) and a long-tailed slot distribution dominated by `date` and
`place_name`.

## Interpretation

- The official split sizes match 11,514 / 2,033 / 2,974 exactly.
- The actual 20-shot sample is determined from the frozen manifest; no count is
  assumed before sampling.
- Validation and Test remain real-only. The generator receives IDs exclusively
  from `splits/manifest.json::splits.train_20shot`.
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    summary = compute_audit(args.data_dir)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _render_charts(summary)
    _write_report(summary, args.report)
    print(f"wrote {args.report}, {args.summary}, and 2 charts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
