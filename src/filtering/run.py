"""Run cheap F1-F4 filters and write accepted/rejected pilot records."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.filtering.stages import run_cheap_filters

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "data" / "generated" / "pilot.jsonl"
DEFAULT_ACCEPTED = REPO_ROOT / "data" / "filtered" / "pilot_f1_f4.jsonl"
DEFAULT_REJECTED = REPO_ROOT / "data" / "filtered" / "pilot_rejected_f1_f4.jsonl"
DEFAULT_REPORT = REPO_ROOT / "reports" / "m5_cheap_filter_funnel.json"


def _update_sample_trace(
    record: dict[str, Any],
    *,
    scores: dict[str, float],
    passed_stage: str | None,
    reject_reason: str | None,
) -> dict[str, Any]:
    copied = json.loads(json.dumps(record, ensure_ascii=False))
    if isinstance(copied.get("sample"), dict):
        provenance = copied["sample"]["provenance"]
        provenance["filter_score"].update(scores)
        provenance["filter_stage_passed"] = passed_stage
        provenance["reject_reason"] = reject_reason
    copied["filter_result"] = {
        "filter_stage_passed": passed_stage,
        "reject_reason": reject_reason,
        "scores": scores,
    }
    return copied


def run_pipeline(
    input_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    total = 0
    json_valid = 0
    f3_passed = 0
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            total += 1
            record = json.loads(line)
            result = run_cheap_filters(record)
            if result.sample is not None:
                json_valid += 1
            if result.passed_stage in {"F3", "F4"}:
                f3_passed += 1
            traced = _update_sample_trace(
                record,
                scores=result.scores,
                passed_stage=result.passed_stage,
                reject_reason=result.reject_reason,
            )
            if result.reject_reason is None:
                accepted.append(traced)
            else:
                rejected.append(traced)
                reasons[result.reject_reason] += 1
    report = {
        "schema_version": 1,
        "input": str(input_path),
        "total": total,
        "f1_json_valid": json_valid,
        "f1_f3_passed": f3_passed,
        "f1_f4_passed": len(accepted),
        "rejected": len(rejected),
        "reject_reasons": dict(sorted(reasons.items())),
    }
    if len(accepted) + len(rejected) != total:
        raise AssertionError("Filter funnel does not sum to total")
    return accepted, rejected, report


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--accepted", type=Path, default=DEFAULT_ACCEPTED)
    parser.add_argument("--rejected", type=Path, default=DEFAULT_REJECTED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    accepted, rejected, report = run_pipeline(args.input)
    _write_jsonl(args.accepted, accepted)
    _write_jsonl(args.rejected, rejected)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"F1-F4 accepted {len(accepted)}/{report['total']}; rejected {len(rejected)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
