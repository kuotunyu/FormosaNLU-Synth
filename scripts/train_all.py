"""Print the frozen M9 run plan; execution remains forbidden during M8."""

from __future__ import annotations

import argparse

from src.training.train_all import build_run_plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Reserved for M9 after explicit user approval; currently refuses.",
    )
    args = parser.parse_args()
    if args.execute:
        raise RuntimeError("M9 execution is intentionally locked until the user reviews M8")
    plans = build_run_plan()
    for plan in plans:
        print(
            f"{plan.group}: seed={plan.seed} output={plan.output_dir} "
            f"shared={plan.shared_config_sha256[:12]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
