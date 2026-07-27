"""Build the M10 seven-row table from zero-shot, run, and adapter reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.evaluation.report import build_results, render_markdown
from src.training.train import REPO_ROOT

DEFAULT_JSON = REPO_ROOT / "reports" / "m10_main_results.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports" / "m10_main_results.md"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    payload = build_results(seed=args.seed)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(render_markdown(payload), encoding="utf-8")
    print(
        f"M10 report status={payload['status']}; "
        f"missing={payload['missing_groups']}"
    )
    if payload["status"] != "complete" and not args.allow_incomplete:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
