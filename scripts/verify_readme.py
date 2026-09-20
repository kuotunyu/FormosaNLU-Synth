"""Verify that README and its linked detail documents reproduce from tracked reports.

README carries the headline evidence. The full result tables live in
docs/results.md and the method detail in docs/method.md. Every number is still
formatted from the raw report and must appear verbatim in the one document that
publishes it, so moving a table out of README never unbinds it from evidence.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.training.train import REPO_ROOT

README = REPO_ROOT / "README.md"
RESULTS_DOC = REPO_ROOT / "docs" / "results.md"
METHOD_DOC = REPO_ROOT / "docs" / "method.md"
M10 = REPO_ROOT / "reports" / "m10_main_results.json"
M9_REPLICATES = REPO_ROOT / "reports" / "m9_replicate_summary.json"
M10_ROBUSTNESS = REPO_ROOT / "reports" / "m10_robustness.json"
M13_PUBLICATION = REPO_ROOT / "reports" / "m13_publication.json"
M14_PAIRED = REPO_ROOT / "reports" / "m14_paired_statistics.json"
M15_CROSS_MODEL = REPO_ROOT / "reports" / "m15_cross_model_replication.json"
M16_ROBUSTNESS_SEEDS = {
    "gemma": REPO_ROOT / "reports" / "m16_robustness_summary_gemma.json",
    "phi4mini": REPO_ROOT / "reports" / "m16_robustness_summary_phi4mini.json",
}
M19_ABLATION = REPO_ROOT / "reports" / "m19_ablation.json"
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


def _mermaid_blocks(text: str) -> list[str]:
    return [section.split("```", 1)[0] for section in text.split("```mermaid")[1:]]


def readme_diagram_checks(readme: str, method_doc: str) -> dict[str, bool]:
    """Verify the README data-flow diagram and the paired flow in docs/method.md."""
    readme_blocks = _mermaid_blocks(readme)
    method_blocks = _mermaid_blocks(method_doc)
    data_flow = readme_blocks[0] if readme_blocks else ""
    paired_flow = method_blocks[0] if method_blocks else ""
    return {
        "README keeps exactly one Mermaid diagram": readme.count("```mermaid") == 1,
        "method doc keeps exactly one Mermaid diagram": (
            method_doc.count("```mermaid") == 1
        ),
        "vertical reader-first data pipeline": (
            "flowchart TB" in data_flow
            and all(
                marker in data_flow
                for marker in (
                    "MASSIVE",
                    "格式與標籤檢查",
                    "去重與防止資料洩漏",
                    "3,760-row",
                    "training corpus",
                    "獨立模型品質稽核",
                    "3,754-row",
                    "public Dataset",
                )
            )
            and not any(
                re.search(rf"\bF{stage}\b", data_flow) for stage in range(1, 8)
            )
        ),
        "F1-F7 audit glossary in method doc": (
            "F1–F7 是什麼？" in method_doc
            and all(f"| F{stage} |" in method_doc for stage in range(1, 8))
        ),
        "paired evidence diagram in method doc": all(
            marker in paired_flow
            for marker in (
                "real_only",
                "real_syn_filtered",
                "2,974-row",
                "hierarchical paired",
                "cross-family",
            )
        ),
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


def expected_headline_rows(
    replicates: dict[str, Any], paired: dict[str, Any], cross_model: dict[str, Any]
) -> list[str]:
    """Return the two first-screen rows, one per student family.

    Gemma shows the three-seed means next to the M14 paired delta and interval;
    Phi shows the M15 paired delta and interval. Nothing is retyped by hand.
    """

    def delta(mean: float, low: float, high: float) -> str:
        return f"**{mean:+.2f} pp**，95% CI [{low:+.2f}, {high:+.2f}]"

    gemma_cells = []
    phi_cells = []
    for metric in ("intent_accuracy", "exact_match"):
        real = replicates["metrics"]["real_only"][metric]["mean"]
        filtered = replicates["metrics"]["real_syn_filtered"][metric]["mean"]
        item = paired["hierarchical_bootstrap"]["metrics"][metric]
        low, high = item["hierarchical_bootstrap_95_ci_percentage_points"]
        gemma_cells.append(
            f"{real:.2%} → {filtered:.2%}"
            f"（{delta(item['mean_delta_percentage_points'], low, high)}）"
        )
        phi = cross_model["metrics"][metric]["phi"]
        phi_cells.append(delta(phi["mean_delta_percentage_points"], *phi["ci"]))
    return [
        f"| Gemma 4 E4B | {gemma_cells[0]} | {gemma_cells[1]} |",
        f"| Phi-4-mini | {phi_cells[0]} | {phi_cells[1]} |",
    ]


def expected_cross_model_rows(report: dict[str, Any]) -> list[str]:
    """Return the M15 cross-model table rows that must appear verbatim.

    Both families are formatted from the same raw report, so a README row can
    never drift from the measured delta or its hierarchical interval.
    """
    rows = []
    for metric, item in report["metrics"].items():
        gemma, phi = item["gemma"], item["phi"]
        gemma_low, gemma_high = gemma["ci"]
        phi_low, phi_high = phi["ci"]
        mark = "✅" if item["both_ci_exclude_zero_positive"] else "❌"
        rows.append(
            f"| `{metric}` "
            f"| {gemma['mean_delta_percentage_points']:+.2f} "
            f"[{gemma_low:+.2f}, {gemma_high:+.2f}] "
            f"| {phi['mean_delta_percentage_points']:+.2f} "
            f"[{phi_low:+.2f}, {phi_high:+.2f}] "
            f"| {mark} |"
        )
    return rows


def expected_demo_examples(evidence: dict[str, Any], utterances: list[str]) -> list[str]:
    """Return the exact strings a worked example must reproduce.

    README quotes real model output, so the utterance and the adapter's raw
    JSON are both taken from the evidence file rather than retyped. A reworded
    example or a hand-edited JSON blob fails this check.
    """
    by_utterance = {row["utterance"]: row for row in evidence["comparisons"]}
    expected: list[str] = []
    for utterance in utterances:
        row = by_utterance[utterance]
        expected.append(utterance)
        expected.append(row["adapted"]["raw"])
    return expected


def expected_robustness_headline(summary: dict[str, Any]) -> str:
    """Return the across-seed exact-match delta README quotes in one sentence."""
    item = summary["paired_filtered_minus_real_only"]["exact_match"]
    return f"{item['mean'] * 100:+.2f} pp"


def expected_robustness_seed_rows(summary: dict[str, Any]) -> list[str]:
    """Return the across-seed paired-delta rows, in percentage points.

    Formatted identically to the aggregator's own markdown so the README table
    and reports/m16_robustness_summary_*.md cannot disagree.
    """
    rows = []
    for metric, item in summary["paired_filtered_minus_real_only"].items():
        std = item["sample_std"]
        std_text = "—" if std is None else f"{std * 100:.2f}"
        rows.append(f"| `{metric}` | {item['mean'] * 100:+.2f} | {std_text} |")
    return rows


def expected_ablation_rows(report: dict[str, Any]) -> list[str]:
    """Return the M19 equal-N rows exactly as README must reproduce them."""
    rows = []
    for item in report["groups"]:
        metrics = item["metrics"]
        excluded = item["excluded_recipe"] or "— (equal-N control)"
        mark = "yes" if item["detectable_on_exact_match"] else "no"
        rows.append(
            f"| `{item['group']}` | `{excluded}` | "
            f"{metrics['intent_accuracy']:.2%} | "
            f"{metrics['intent_macro_f1']:.2%} | "
            f"{metrics['slot_micro_f1']:.2%} | "
            f"{metrics['exact_match']:.2%} | "
            f"{item['delta_vs_control_percentage_points']['exact_match']:+.2f} | "
            f"{metrics['json_valid_rate']:.2%} | {mark} |"
        )
    return rows


def verify_readme(
    *,
    readme: str,
    results_doc: str,
    method_doc: str,
    m10: dict[str, Any],
    generation: dict[str, Any],
    resources: dict[str, Any],
    m11: dict[str, Any],
    replicates: dict[str, Any] | None = None,
    robustness: dict[str, Any] | None = None,
    publication: dict[str, Any] | None = None,
    paired: dict[str, Any] | None = None,
    cross_model: dict[str, Any] | None = None,
    robustness_seeds: dict[str, dict[str, Any]] | None = None,
    ablation: dict[str, Any] | None = None,
) -> list[str]:
    """Check each published number in the one document that carries it.

    `readme` holds the headline evidence, `results_doc` (docs/results.md) the
    full result tables, and `method_doc` (docs/method.md) the method detail.
    """
    checks: list[tuple[str, bool]] = []
    checks.extend(readme_diagram_checks(readme, method_doc).items())
    for expected in expected_main_rows(m10):
        checks.append(
            (
                f"main row {expected.split('|')[1].strip()} (docs/results.md)",
                expected in results_doc,
            )
        )
    if replicates is not None:
        checks.append(("three-seed summary complete", replicates.get("status") == "complete"))
        for expected in expected_replicate_rows(replicates):
            checks.append(
                (
                    f"three-seed row {expected.split('|')[1].strip()} (docs/results.md)",
                    expected in results_doc,
                )
            )
    if replicates is not None and paired is not None and cross_model is not None:
        for expected in expected_headline_rows(replicates, paired, cross_model):
            checks.append(
                (f"headline row {expected.split('|')[1].strip()}", expected in readme)
            )
    if robustness is not None:
        checks.append(("robustness report complete", robustness.get("status") == "complete"))
        for expected in expected_robustness_rows(robustness):
            checks.append(
                (
                    f"robustness row {' / '.join(expected.split('|')[1:3]).strip()} "
                    "(docs/results.md)",
                    expected in results_doc,
                )
            )
    if publication is not None:
        checks.append(("public release verified", publication.get("status") == "public_verified"))
        checks.append(
            (
                "public contributors only kuotunyu (docs/results.md)",
                publication["github"].get("contributors_only_kuotunyu") is True
                and "Contributors 僅 `kuotunyu`" in results_doc,
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
            checks.append(
                (f"paired marker {marker} (docs/results.md)", marker in results_doc)
            )
    if cross_model is not None:
        criterion = cross_model["preregistered_replication_criterion"]
        checks.append(
            ("cross-model report complete", cross_model.get("status") == "complete")
        )
        # The verdict is only reportable if the preregistered rule actually held
        # for both primary metrics, so tie the README wording to the raw flag.
        checks.append(
            (
                "cross-model criterion passed",
                criterion.get("passed") is True
                and all(
                    cross_model["metrics"][metric]["both_ci_exclude_zero_positive"]
                    for metric in criterion["primary_metrics"]
                ),
            )
        )
        checks.append(
            (
                "cross-model verdict stated",
                cross_model["conclusion"] == "replicated_across_student_families"
                and "replicated_across_student_families" in readme,
            )
        )
        checks.append(
            (
                "cross-model families named",
                cross_model["models"]["gemma"] in readme
                and cross_model["models"]["phi"] in readme,
            )
        )
        checks.append(
            (
                "cross-model families not pooled",
                "不 pooling" in readme or "不做 pooling" in readme,
            )
        )
        for row in expected_cross_model_rows(cross_model):
            checks.append(
                (f"cross-model row {row.split('|')[1].strip()}", row in readme)
            )
    # Only enforced once every expected seed has landed, so a partial summary
    # cannot be quoted as if it were the finished evidence.
    for target, summary in sorted((robustness_seeds or {}).items()):
        if summary.get("status") != "complete":
            continue
        seeds = summary["seeds"]
        for label, document in (("README", readme), ("docs/results.md", results_doc)):
            checks.append(
                (
                    f"robustness seeds stated ({target}, {label})",
                    len(seeds) >= 3 and all(str(seed) in document for seed in seeds),
                )
            )
            checks.append(
                (
                    f"robustness no longer claims a single seed ({target}, {label})",
                    "robustness 只使用 seed 42" not in document
                    and "Robustness 只比較 seed-42 adapters" not in document,
                )
            )
        checks.append(
            (
                f"robustness headline {target}",
                expected_robustness_headline(summary) in readme,
            )
        )
        for row in expected_robustness_seed_rows(summary):
            checks.append(
                (
                    f"robustness seed row {target} {row.split('|')[1].strip()} "
                    "(docs/results.md)",
                    row in results_doc,
                )
            )

    if ablation is not None:
        checks.append(("M19 ablation complete", ablation.get("status") == "complete"))
        threshold = (
            f"{ablation['detectability_threshold_percentage_points']:.1f} percentage points"
        )
        # README states the negative result in one sentence and docs/results.md
        # carries the table, so both must keep the same three disclosures.
        for label, document in (("README", readme), ("docs/results.md", results_doc)):
            checks.append(
                (f"M19 single-seed scope disclosed ({label})", "seed 42（n=1）" in document)
            )
            checks.append(
                (f"M19 detectability threshold disclosed ({label})", threshold in document)
            )
            checks.append(
                (
                    f"M19 no recipe-level causal claim ({label})",
                    ablation.get("causal_claim_allowed") is False
                    and "不做單一 recipe 的 causal claim" in document,
                )
            )
        for expected in expected_ablation_rows(ablation):
            checks.append(
                (
                    f"M19 row {expected.split('|')[1].strip()} (docs/results.md)",
                    expected in results_doc,
                )
            )

    # The worked examples are the only place raw model output is shown, so they
    # must come from the evidence file verbatim: one in README, both in the doc.
    for expected in expected_demo_examples(m11, ["播放周杰倫"]):
        checks.append((f"demo example {expected[:24]}", expected in readme))
    for expected in expected_demo_examples(m11, ["播放周杰倫", "台北明天會不會下雨"]):
        checks.append(
            (f"demo example {expected[:24]} (docs/results.md)", expected in results_doc)
        )
    for label, document in (("README", readme), ("docs/results.md", results_doc)):
        checks.append(
            (
                f"demo prompt asymmetry disclosed ({label})",
                "zero-shot" in document and "catalog" in document,
            )
        )

    filtered_gap = m10["gap_closed"]["real_syn_filtered"]["exact_match"]
    comparisons = m11["comparisons"]
    base_valid = sum(bool(row["base"]["valid"]) for row in comparisons)
    adapted_valid = sum(bool(row["adapted"]["valid"]) for row in comparisons)
    phases = resources["phases"]
    core_hours = f"{resources['measured_core_gpu_hours']:.3f} h"
    total_hours = f"{resources['measured_total_local_gpu_hours']:.3f} h"
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
                "training hours (docs/results.md)",
                f"{phases['primary_training_seed_42']['wall_hours']:.3f} h" in results_doc,
            ),
            (
                "evaluation hours (docs/results.md)",
                f"{phases['trained_evaluation_seed_42']['wall_hours']:.3f} h" in results_doc,
            ),
            ("core GPU hours", core_hours in readme),
            ("core GPU hours (docs/results.md)", core_hours in results_doc),
            (
                "auxiliary GPU hours (docs/results.md)",
                f"{resources['measured_auxiliary_gpu_hours']:.3f} h" in results_doc,
            ),
            ("local total GPU hours", total_hours in readme),
            ("local total GPU hours (docs/results.md)", total_hours in results_doc),
            (
                "local total TDP envelope (docs/results.md)",
                f"{resources['gpu_tdp_total_energy_upper_bound_kwh']:.3f} kWh" in results_doc,
            ),
            (
                "M11 base strict validity",
                f"base model {base_valid}/{len(comparisons)}" in readme,
            ),
            (
                "M11 adapted strict validity",
                f"{adapted_valid}/{len(comparisons)} valid JSON" in readme,
            ),
            (
                "M12 placeholders removed",
                all("FILL AT M12" not in text for text in (readme, results_doc, method_doc)),
            ),
        ]
    )
    for asset, label, document in (
        ("m12_main_results.png", "README", readme),
        ("m12_filter_comparison.png", "docs/results.md", results_doc),
        ("m12_filter_funnel.png", "docs/results.md", results_doc),
        ("m12_intent_movement.png", "docs/results.md", results_doc),
        ("m12_pipeline.png", "docs/method.md", method_doc),
    ):
        checks.append((f"asset {asset} ({label})", f"assets/{asset}" in document))

    failed = [name for name, passed in checks if not passed]
    if failed:
        raise AssertionError("README verification failed: " + ", ".join(failed))
    return [name for name, _ in checks]


def main() -> int:
    checks = verify_readme(
        readme=README.read_text(encoding="utf-8"),
        results_doc=RESULTS_DOC.read_text(encoding="utf-8"),
        method_doc=METHOD_DOC.read_text(encoding="utf-8"),
        m10=_load(M10),
        generation=_load(GENERATION),
        resources=_load(RESOURCES),
        m11=_load(M11),
        replicates=_load(M9_REPLICATES),
        robustness=_load(M10_ROBUSTNESS) if M10_ROBUSTNESS.is_file() else None,
        publication=_load(M13_PUBLICATION) if M13_PUBLICATION.is_file() else None,
        paired=_load(M14_PAIRED) if M14_PAIRED.is_file() else None,
        cross_model=_load(M15_CROSS_MODEL) if M15_CROSS_MODEL.is_file() else None,
        robustness_seeds={
            target: _load(path)
            for target, path in M16_ROBUSTNESS_SEEDS.items()
            if path.is_file()
        }
        or None,
        ablation=_load(M19_ABLATION) if M19_ABLATION.is_file() else None,
    )
    print(f"README verification passed: {len(checks)} reproducible checks")
    for check in checks:
        print(f"  PASS {check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
