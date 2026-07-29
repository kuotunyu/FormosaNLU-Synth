"""Verify that README headline numbers reproduce from tracked reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.training.train import REPO_ROOT

README = REPO_ROOT / "README.md"
M10 = REPO_ROOT / "reports" / "m10_main_results.json"
M9_REPLICATES = REPO_ROOT / "reports" / "m9_replicate_summary.json"
M10_ROBUSTNESS = REPO_ROOT / "reports" / "m10_robustness.json"
M13_PUBLICATION = REPO_ROOT / "reports" / "m13_publication.json"
M14_PAIRED = REPO_ROOT / "reports" / "m14_paired_statistics.json"
GENERATION = REPO_ROOT / "reports" / "generation_report.json"
RESOURCES = REPO_ROOT / "reports" / "m12_resource_ledger.json"
M11 = REPO_ROOT / "reports" / "m11_demo_evidence.json"

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


def expected_replicate_rows(summary: dict[str, Any]) -> list[str]:
    """Format every three-seed metric row from the tracked summary."""
    labels = {
        "intent_accuracy": "Intent accuracy",
        "intent_macro_f1": "Intent macro-F1",
        "slot_micro_f1": "Slot micro-F1",
        "exact_match": "Exact match",
        "json_valid_rate": "JSON-valid rate",
    }
    rows = []
    for metric, label in labels.items():
        real = summary["metrics"]["real_only"][metric]
        filtered = summary["metrics"]["real_syn_filtered"][metric]
        paired = summary["paired_filtered_minus_real_only"][metric]
        rows.append(
            f"| {label} | "
            f"{real['mean']:.2%} ± {real['sample_std']:.2%} | "
            f"{filtered['mean']:.2%} ± {filtered['sample_std']:.2%} | "
            f"{paired['mean']:+.2%} ± {paired['sample_std']:.2%} | "
            f"[{paired['ci95_low']:+.2%}, {paired['ci95_high']:+.2%}] |"
        )
    return rows


def expected_robustness_rows(report: dict[str, Any]) -> list[str]:
    """Format the two-adapter, three-probe robustness table."""
    rows = []
    for group in ("real_only", "real_syn_filtered"):
        group_report = report["groups"][group]
        for kind in ("asr_noise", "colloquial", "lexical"):
            metrics = group_report["metrics_by_probe_kind"][kind]
            rows.append(
                f"| `{group}` | `{kind}` | "
                f"{metrics['intent_accuracy']:.2%} | "
                f"{metrics['slot_micro_f1']:.2%} | "
                f"{metrics['exact_match']:.2%} | "
                f"{metrics['json_valid_rate']:.2%} |"
            )
    return rows


def expected_publication_markers(report: dict[str, Any]) -> list[str]:
    """Return the public URLs and release-row marker required in README."""
    return [
        report["github"]["url"],
        report["dataset"]["url"],
        report["model"]["url"],
        f"{int(report['dataset']['rows']):,}-row",
    ]


def expected_paired_markers(report: dict[str, Any]) -> list[str]:
    """Return formatted M14 markers that must be visible in README."""
    metrics = report["hierarchical_bootstrap"]["metrics"]
    markers = [
        f"{int(report['hierarchical_bootstrap']['repetitions']):,} 次",
        "hierarchical paired",
    ]
    for metric in ("intent_accuracy", "exact_match"):
        item = metrics[metric]
        lower, upper = item["hierarchical_bootstrap_95_ci_percentage_points"]
        markers.extend(
            [
                f"{item['mean_delta_percentage_points']:+.2f}",
                f"[{lower:+.2f}, {upper:+.2f}]",
            ]
        )
    return markers


def verify_readme(
    *,
    readme: str,
    m10: dict[str, Any],
    generation: dict[str, Any],
    resources: dict[str, Any],
    m11: dict[str, Any],
    replicates: dict[str, Any] | None = None,
    robustness: dict[str, Any] | None = None,
    publication: dict[str, Any] | None = None,
    paired: dict[str, Any] | None = None,
) -> list[str]:
    checks: list[tuple[str, bool]] = []
    for expected in expected_main_rows(m10):
        checks.append((f"main row {expected.split('|')[1].strip()}", expected in readme))
    if replicates is not None:
        checks.append(("three-seed summary complete", replicates.get("status") == "complete"))
        for expected in expected_replicate_rows(replicates):
            checks.append(
                (
                    f"three-seed row {expected.split('|')[1].strip()}",
                    expected in readme,
                )
            )
    if robustness is not None:
        checks.append(("robustness report complete", robustness.get("status") == "complete"))
        for expected in expected_robustness_rows(robustness):
            checks.append(
                (
                    f"robustness row {' / '.join(expected.split('|')[1:3]).strip()}",
                    expected in readme,
                )
            )
    if publication is not None:
        checks.append(("public release verified", publication.get("status") == "public_verified"))
        checks.append(
            (
                "public contributors only kuotunyu",
                publication["github"].get("contributors_only_kuotunyu") is True
                and "Contributors 僅 `kuotunyu`" in readme,
            )
        )
        for marker in expected_publication_markers(publication):
            checks.append((f"public marker {marker}", marker in readme))
    if paired is not None:
        tests = paired["exact_mcnemar"]["tests"]
        checks.append(("paired statistics complete", paired.get("status") == "complete"))
        checks.append(
            (
                "paired Holm tests all significant",
                len(tests) == 6
                and all(item.get("holm_adjusted_p_value", 1.0) < 0.05 for item in tests.values()),
            )
        )
        for marker in expected_paired_markers(paired):
            checks.append((f"paired marker {marker}", marker in readme))

    filtered_gap = m10["gap_closed"]["real_syn_filtered"]["exact_match"]
    comparisons = m11["comparisons"]
    base_valid = sum(bool(row["base"]["valid"]) for row in comparisons)
    adapted_valid = sum(bool(row["adapted"]["valid"]) for row in comparisons)
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
                "F7 release row count",
                f"{generation['f7_audit']['release_rows']:,}" in readme,
            ),
            (
                "F7 random-stratum miss rate",
                (f"{generation['f7_audit']['random_stratum']['observed_miss_rate']:.1%}" in readme),
            ),
            (
                "training hours",
                f"{resources['phases']['primary_training_seed_42']['wall_hours']:.3f} h" in readme,
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
            (
                "auxiliary GPU hours",
                f"{resources['measured_auxiliary_gpu_hours']:.3f} h" in readme,
            ),
            (
                "local total GPU hours",
                f"{resources['measured_total_local_gpu_hours']:.3f} h" in readme,
            ),
            (
                "local total TDP envelope",
                (f"{resources['gpu_tdp_total_energy_upper_bound_kwh']:.3f} kWh" in readme),
            ),
            (
                "M11 base strict validity",
                f"base model {base_valid}/{len(comparisons)}" in readme,
            ),
            (
                "M11 adapted strict validity",
                f"{adapted_valid}/{len(comparisons)} valid JSON" in readme,
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
        m11=_load(M11),
        replicates=_load(M9_REPLICATES),
        robustness=_load(M10_ROBUSTNESS) if M10_ROBUSTNESS.is_file() else None,
        publication=_load(M13_PUBLICATION) if M13_PUBLICATION.is_file() else None,
        paired=_load(M14_PAIRED) if M14_PAIRED.is_file() else None,
    )
    print(f"README verification passed: {len(checks)} reproducible checks")
    for check in checks:
        print(f"  PASS {check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
