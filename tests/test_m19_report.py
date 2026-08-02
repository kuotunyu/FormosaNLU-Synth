from __future__ import annotations

import pytest

from scripts.build_m19_report import build_report, render_markdown
from src.training.ablation import ABLATION_GROUPS

METRICS = (
    "intent_accuracy",
    "intent_macro_f1",
    "slot_micro_f1",
    "exact_match",
    "json_valid_rate",
)


def _evaluation(group: str, *, exact_match: float) -> dict[str, object]:
    metrics = {metric: 0.75 for metric in METRICS}
    metrics["exact_match"] = exact_match
    return {
        "evaluation_mode": "trained_adapter",
        "group": group,
        "seed": 42,
        "completed": 2_974,
        "target": 2_974,
        "wall_seconds": 100.0,
        "metrics": metrics,
    }


def test_build_report_computes_preregistered_exact_match_deltas() -> None:
    exact_matches = {
        "abl_all_eqn": 0.50,
        "abl_no_paraphrase": 0.47,
        "abl_no_slot_substitution": 0.49,
        "abl_no_noise_codeswitch": 0.525,
        "abl_no_hard_negative": 0.501,
    }
    report = build_report(
        [_evaluation(group, exact_match=exact_matches[group]) for group in ABLATION_GROUPS]
    )

    assert report["status"] == "complete"
    assert report["seed"] == 42
    assert report["detectability_threshold_percentage_points"] == 2.5
    by_group = {row["group"]: row for row in report["groups"]}
    assert by_group["abl_no_paraphrase"]["delta_vs_control_percentage_points"][
        "exact_match"
    ] == pytest.approx(-3.0)
    assert by_group["abl_no_paraphrase"]["detectable_on_exact_match"] is True
    assert by_group["abl_no_slot_substitution"]["detectable_on_exact_match"] is False
    assert report["detectable_groups_on_exact_match"] == [
        "abl_no_paraphrase",
        "abl_no_noise_codeswitch",
    ]


def test_build_report_rejects_incomplete_or_mismatched_evaluation() -> None:
    rows = [_evaluation(group, exact_match=0.5) for group in ABLATION_GROUPS]
    rows[-1]["completed"] = 2_973

    with pytest.raises(ValueError, match="complete 2,974-row trained-adapter"):
        build_report(rows)


def test_markdown_discloses_single_seed_and_detectability_limit() -> None:
    report = build_report(
        [_evaluation(group, exact_match=0.5) for group in ABLATION_GROUPS]
    )
    markdown = render_markdown(report)

    assert "seed 42（n=1）" in markdown
    assert "2.5 percentage points" in markdown
    assert "不支持 recipe-level causal claim" in markdown
    assert "`abl_no_hard_negative`" in markdown
