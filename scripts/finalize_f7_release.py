"""Build the release-only filtered corpus after the completed F7 judge audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.training.train import REPO_ROOT

DEFAULT_INPUT = REPO_ROOT / "data" / "filtered" / "full_f1_f6.jsonl"
DEFAULT_JUDGE_RESULTS = (
    REPO_ROOT / "data" / "filtered" / "full_f7_judge_results.jsonl"
)
DEFAULT_OUTPUT = REPO_ROOT / "data" / "filtered" / "full_f1_f7_release.jsonl"
DEFAULT_REPORT = REPO_ROOT / "reports" / "m6_f7_release.json"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    try:
        value = path.relative_to(REPO_ROOT)
    except ValueError:
        value = path
    return str(value).replace("\\", "/")


def _wilson_interval(
    rejected: int,
    total: int,
    *,
    z: float = 1.959963984540054,
) -> tuple[float, float]:
    if total <= 0:
        raise ValueError("Wilson interval requires at least one observation")
    proportion = rejected / total
    denominator = 1 + z * z / total
    centre = proportion + z * z / (2 * total)
    radius = z * math.sqrt(
        proportion * (1 - proportion) / total + z * z / (4 * total * total)
    )
    return (centre - radius) / denominator, (centre + radius) / denominator


def finalize_release(
    *,
    source: Path,
    judge_results: Path,
    output: Path,
    report: Path,
) -> dict[str, Any]:
    rows = _load_jsonl(source)
    judged = _load_jsonl(judge_results)
    source_ids = [row["sample"]["id"] for row in rows]
    judged_ids = [row["sample_id"] for row in judged]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("F1-F6 source contains duplicate sample ids")
    if len(judged_ids) != len(set(judged_ids)):
        raise ValueError("F7 results contain duplicate sample ids")
    unknown = sorted(set(judged_ids) - set(source_ids))
    if unknown:
        raise ValueError(f"F7 results reference {len(unknown)} unknown sample ids")
    if len(judged) != 376:
        raise ValueError(f"F7 audit must contain 376 rows, found {len(judged)}")
    invalid = [
        row["sample_id"]
        for row in judged
        if not row.get("json_valid") or not isinstance(row.get("verdict"), dict)
    ]
    if invalid:
        raise ValueError(f"F7 audit has {len(invalid)} invalid verdicts")

    rejected = [
        row for row in judged if not bool(row["verdict"].get("accepted", False))
    ]
    rejected_ids = {row["sample_id"] for row in rejected}
    retained = [row for row in rows if row["sample"]["id"] not in rejected_ids]
    random_rows = [row for row in judged if row["selection_stratum"] == "random"]
    random_rejected = sum(
        not bool(row["verdict"]["accepted"]) for row in random_rows
    )
    random_interval = _wilson_interval(random_rejected, len(random_rows))

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in retained:
            handle.write(
                json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            )

    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "source": _display_path(source),
        "source_rows": len(rows),
        "source_sha256": _sha256(source),
        "judge_results": _display_path(judge_results),
        "judge_rows": len(judged),
        "judge_results_sha256": _sha256(judge_results),
        "excluded_rows": len(rejected),
        "excluded_sample_ids": sorted(rejected_ids),
        "release_output": _display_path(output),
        "release_rows": len(retained),
        "release_sha256": _sha256(output),
        "random_stratum": {
            "samples": len(random_rows),
            "rejected": random_rejected,
            "observed_miss_rate": random_rejected / len(random_rows),
            "wilson_95_percent_interval": list(random_interval),
            "is_unbiased_rate_estimator": True,
        },
        "targeted_strata_are_not_unbiased_rate_estimators": True,
        "training_contract_unchanged": True,
        "training_source_remains": "data/filtered/full_f1_f6.jsonl",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--judge-results", type=Path, default=DEFAULT_JUDGE_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    payload = finalize_release(
        source=args.input,
        judge_results=args.judge_results,
        output=args.output,
        report=args.report,
    )
    print(
        f"F7 release complete: {payload['source_rows']} -> "
        f"{payload['release_rows']} rows; excluded={payload['excluded_rows']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
