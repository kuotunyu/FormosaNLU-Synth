"""Create the deterministic full-corpus F7 audit manifest without using a model."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.filtering.judge_audit import select_full_audit, selection_summary

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "data" / "filtered" / "full_f1_f6.jsonl"
DEFAULT_MANIFEST = REPO_ROOT / "data" / "filtered" / "full_f7_audit_manifest.jsonl"
DEFAULT_REPORT = REPO_ROOT / "reports" / "m6_f7_audit_plan.json"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(args: argparse.Namespace) -> dict[str, Any]:
    records = _load_jsonl(args.input)
    selected = select_full_audit(
        records,
        fraction=args.fraction,
        seed=args.seed,
    )
    _write_jsonl(args.manifest, selected)
    summary = selection_summary(
        selected,
        source=args.input.relative_to(REPO_ROOT),
        source_count=len(records),
        fraction=args.fraction,
        seed=args.seed,
    )
    summary.update(
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "manifest": str(args.manifest.relative_to(REPO_ROOT)),
            "manifest_sha256": _sha256(args.manifest),
        }
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"prepared F7 manifest {summary['selected_count']}/{summary['source_count']}: "
        f"{summary['strata']}"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--fraction", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
