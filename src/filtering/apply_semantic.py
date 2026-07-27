"""Apply calibrated BGE-M3 F5/F6 thresholds to the F1-F4 pilot."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from src.filtering.decontaminate import write_exclusion_log
from src.filtering.similarity import SimilarityThresholds, apply_similarity_filters

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "data" / "filtered" / "pilot_f1_f4.jsonl"
DEFAULT_CHEAP_REPORT = REPO_ROOT / "reports" / "m5_cheap_filter_funnel.json"
DEFAULT_EMBEDDINGS = REPO_ROOT / "data" / "embeddings" / "m5_pilot_bge_m3.npz"
DEFAULT_CONFIG = REPO_ROOT / "configs" / "filtering.yaml"
DEFAULT_ACCEPTED = REPO_ROOT / "data" / "filtered" / "pilot_f1_f6.jsonl"
DEFAULT_REJECTED = REPO_ROOT / "data" / "filtered" / "pilot_rejected_f5_f6.jsonl"
DEFAULT_EXCLUSIONS = REPO_ROOT / "data" / "filtered" / "pilot_f6_exclusions.jsonl"
DEFAULT_REPORT = REPO_ROOT / "reports" / "m5_full_filter_funnel.json"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def load_thresholds(path: Path) -> SimilarityThresholds:
    values = yaml.safe_load(path.read_text(encoding="utf-8"))["thresholds"]
    if any(value is None for value in values.values()):
        raise RuntimeError("F5/F6 thresholds are null; inspect calibration distributions first")
    return SimilarityThresholds(**values)


def apply_semantic_filters(
    records: list[dict[str, Any]],
    embedding_path: Path,
    thresholds: SimilarityThresholds,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    Counter[str],
]:
    with np.load(embedding_path) as archive:
        pilot_ids = archive["pilot_ids"].tolist()
        record_ids = [record["sample"]["id"] for record in records]
        if pilot_ids != record_ids:
            raise ValueError("Embedding pilot ids do not align with F1-F4 records")
        eval_ids = archive["eval_ids"].tolist()
        decisions = apply_similarity_filters(
            archive["pilot_embeddings"],
            archive["seed_embeddings"],
            archive["eval_embeddings"],
            eval_ids,
            thresholds,
        )
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    for record, decision in zip(records, decisions, strict=True):
        copied = json.loads(json.dumps(record, ensure_ascii=False))
        scores = {
            "f5_max_prior_synthetic": decision.max_prior_synthetic,
            "f5_max_seed": decision.max_seed,
            "f6_max_eval": decision.max_eval,
        }
        passed_stage = (
            "F6"
            if decision.passed
            else "F5"
            if decision.reject_reason == "F6_CONTAM_EVAL"
            else "F4"
        )
        provenance = copied["sample"]["provenance"]
        provenance["filter_score"].update(scores)
        provenance["filter_stage_passed"] = passed_stage
        provenance["reject_reason"] = decision.reject_reason
        copied["filter_result"] = {
            "filter_stage_passed": passed_stage,
            "reject_reason": decision.reject_reason,
            "scores": scores,
        }
        if decision.passed:
            accepted.append(copied)
        else:
            rejected.append(copied)
            reasons[decision.reject_reason or "UNKNOWN"] += 1
            if decision.reject_reason == "F6_CONTAM_EVAL":
                assert decision.nearest_eval_id is not None
                split, matched_id = decision.nearest_eval_id.split(":", maxsplit=1)
                exclusions.append(
                    {
                        "sample_id": copied["sample"]["id"],
                        "similarity": decision.max_eval,
                        "matched_eval_id": matched_id,
                        "split": split,
                    }
                )
    return accepted, rejected, exclusions, reasons


def run(args: argparse.Namespace) -> dict[str, Any]:
    thresholds = load_thresholds(args.config)
    records = _load_jsonl(args.input)
    accepted, rejected, exclusions, reasons = apply_semantic_filters(
        records,
        args.embeddings,
        thresholds,
    )
    _write_jsonl(args.accepted, accepted)
    _write_jsonl(args.rejected, rejected)
    write_exclusion_log(exclusions, args.exclusions)
    cheap = json.loads(args.cheap_report.read_text(encoding="utf-8"))
    all_reasons = Counter(cheap["reject_reasons"])
    all_reasons.update(reasons)
    report = {
        "schema_version": 1,
        "total": cheap["total"],
        "f1_json_valid": cheap["f1_json_valid"],
        "f1_f3_passed": cheap["f1_f3_passed"],
        "f1_f4_passed": cheap["f1_f4_passed"],
        "f1_f6_passed": len(accepted),
        "f1_f6_rate": len(accepted) / cheap["total"],
        "rejected": cheap["total"] - len(accepted),
        "semantic_rejected": len(rejected),
        "f6_exclusions": len(exclusions),
        "reject_reasons": dict(sorted(all_reasons.items())),
        "thresholds": {
            "synthetic_duplicate_max": thresholds.synthetic_duplicate_max,
            "seed_too_close_max": thresholds.seed_too_close_max,
            "seed_outlier_min": thresholds.seed_outlier_min,
            "contamination_max": thresholds.contamination_max,
        },
    }
    if report["f1_f6_passed"] + report["rejected"] != report["total"]:
        raise AssertionError("Full filter funnel does not sum to total")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"F1-F6 accepted {len(accepted)}/{cheap['total']}; semantic rejected {len(rejected)}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--cheap-report", type=Path, default=DEFAULT_CHEAP_REPORT)
    parser.add_argument("--embeddings", type=Path, default=DEFAULT_EMBEDDINGS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--accepted", type=Path, default=DEFAULT_ACCEPTED)
    parser.add_argument("--rejected", type=Path, default=DEFAULT_REJECTED)
    parser.add_argument("--exclusions", type=Path, default=DEFAULT_EXCLUSIONS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
