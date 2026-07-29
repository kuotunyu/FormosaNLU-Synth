"""Build M15 paired statistical evidence after all six Phi evaluations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.paired_statistics import build_report, render_markdown
from src.training.cross_model import RESULT_ROOT
from src.training.train import REPO_ROOT

DEFAULT_JSON = REPO_ROOT / "reports" / "m15_phi4mini_paired_statistics.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports" / "m15_phi4mini_paired_statistics.md"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=5_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260729)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    report = build_report(
        repetitions=args.repetitions,
        bootstrap_seed=args.bootstrap_seed,
        results_root=RESULT_ROOT,
        experiment="M15 Phi-4-mini",
        interpretation_scope=(
            "Evidence applies to the frozen MASSIVE zh-TW Test set and the "
            "preregistered Phi-4-mini training contract. Cross-family conclusions "
            "must compare this report with M14 without pooling model families."
        ),
    )
    args.json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.markdown.write_text(
        render_markdown(report),
        encoding="utf-8",
        newline="\n",
    )
    print(
        "M15 Phi paired statistics complete: "
        f"{report['test_rows_per_seed']} rows × {len(report['seeds'])} seeds"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
