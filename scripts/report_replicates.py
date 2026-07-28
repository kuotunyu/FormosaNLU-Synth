"""Build the M9 three-seed uncertainty report from adapter evaluations."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.evaluation.replicate_report import (
    DEFAULT_JSON,
    DEFAULT_MARKDOWN,
    build_replicate_summary,
    write_replicate_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    payload = build_replicate_summary()
    write_replicate_summary(
        payload,
        json_path=args.json,
        markdown_path=args.markdown,
    )
    print(
        f"M9 replicate report status={payload['status']}; "
        f"missing={len(payload['missing'])}"
    )
    return int(args.require_complete and payload["status"] != "complete")


if __name__ == "__main__":
    raise SystemExit(main())
