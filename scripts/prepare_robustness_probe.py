"""Build the deterministic M10 evaluation-only robustness probe."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from src.data.load_massive import decode_example, load_massive_split
from src.data.normalize import parse_annotated_utterance
from src.evaluation.probe import build_probe_rows, probe_summary

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "data" / "evaluation" / "robustness_probe.jsonl"
DEFAULT_REPORT = REPO_ROOT / "reports" / "m10_probe_manifest.json"


def _test_examples() -> list[dict]:
    dataset = load_massive_split("test", download=False)
    examples = []
    for index in range(len(dataset)):
        decoded = decode_example(dataset, index)
        parsed = parse_annotated_utterance(decoded["annot_utt"])
        examples.append(
            {
                "id": decoded["id"],
                "utt": decoded["utt"],
                "intent": decoded["intent"],
                "slots": [
                    {"type": slot_type, "value": value}
                    for slot_type, value in parsed.slots
                ],
            }
        )
    return examples


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    examples = _test_examples()
    rows = build_probe_rows(examples, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    report = probe_summary(rows, source_count=len(examples))
    report.update(
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "output": str(args.output.relative_to(REPO_ROOT)),
            "output_sha256": _sha256(args.output),
        }
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"prepared {report['probe_count']} evaluation-only probe rows: "
        f"{report['probe_kinds']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
