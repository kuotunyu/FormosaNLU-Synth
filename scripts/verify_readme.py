"""Verify that README headline numbers reproduce from tracked reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.training.train import REPO_ROOT

README = REPO_ROOT / "README.md"
M10 = REPO_ROOT / "reports" / "m10_main_results.json"
GENERATION = REPO_ROOT / "reports" / "generation_report.json"
RESOURCES = REPO_ROOT / "reports" / "m12_resource_ledger.json"

DESCRIPTIONS = {
    "zero_shot": "未訓練",
    "real_only": "20-shot real",
    "real_std_aug": "+ classical augmentation",
    "real_syn_unfiltered_full": "+ 全部 unfiltered synthetic",
    "real_syn_unfiltered_eqn": "+ equal-N unfiltered synthetic",
    "real_syn_filtered": "+ filtered synthetic",
    "full_real": "完整 MASSIVE train",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_main_rows(m10: dict[str, Any]) -> list[str]:
    rows = []
    for row in m10["rows"]:
        metrics = row["metrics"]
        rows.append(
            f"| `{row['group']}` | {DESCRIPTIONS[row['group']]} | "
            f"{metrics['intent_accuracy']:.2%} | "
            f"{metrics['intent_macro_f1']:.2%} | "
            f"{metrics['slot_micro_f1']:.2%} | "
            f"{metrics['exact_match']:.2%} | "
            f"{metrics['json_valid_rate']:.2%} |"
        )
    return rows


def verify_readme(
    *,
    readme: str,
    m10: dict[str, Any],
    generation: dict[str, Any],
    resources: dict[str, Any],
) -> list[str]:
    checks: list[tuple[str, bool]] = []
    for expected in expected_main_rows(m10):
        checks.append((f"main row {expected.split('|')[1].strip()}", expected in readme))

    filtered_gap = m10["gap_closed"]["real_syn_filtered"]["exact_match"]
    checks.extend(
        [
            (
                "exact-match absolute delta",
                f"{filtered_gap['absolute_delta']:+.2%}" in readme,
            ),
            (
                "exact-match gap closed",
                f"{filtered_gap['gap_closed_percent']:.1f}%" in readme,
            ),
            (
                "generated row count",
                f"{generation['generation']['completed_rows']:,}" in readme,
            ),
            (
                "accepted row count",
                f"{generation['filtering']['f1_f6_passed']:,}" in readme,
            ),
            (
                "training hours",
                f"{resources['phases']['primary_training_seed_42']['wall_hours']:.3f} h"
                in readme,
            ),
            (
                "evaluation hours",
                f"{resources['phases']['trained_evaluation_seed_42']['wall_hours']:.3f} h"
                in readme,
            ),
            (
                "core GPU hours",
                f"{resources['measured_core_gpu_hours']:.3f} h" in readme,
            ),
            ("M12 placeholders removed", "FILL AT M12" not in readme),
        ]
    )
    for asset in (
        "m12_main_results.png",
        "m12_filter_comparison.png",
        "m12_filter_funnel.png",
        "m12_intent_movement.png",
        "m12_pipeline.png",
    ):
        checks.append((f"asset {asset}", f"assets/{asset}" in readme))

    failed = [name for name, passed in checks if not passed]
    if failed:
        raise AssertionError("README verification failed: " + ", ".join(failed))
    return [name for name, _ in checks]


def main() -> int:
    checks = verify_readme(
        readme=README.read_text(encoding="utf-8"),
        m10=_load(M10),
        generation=_load(GENERATION),
        resources=_load(RESOURCES),
    )
    print(f"README verification passed: {len(checks)} reproducible checks")
    for check in checks:
        print(f"  PASS {check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
