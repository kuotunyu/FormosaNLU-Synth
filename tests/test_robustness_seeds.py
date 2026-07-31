from __future__ import annotations

import pytest

from scripts.report_robustness_seeds import (
    render_markdown,
    report_path,
    summarize_robustness_seeds,
)


def _report(*, real_only: float, filtered: float, status: str = "complete") -> dict:
    def group(value: float) -> dict:
        return {
            "metrics": {
                "intent_accuracy": value,
                "intent_macro_f1": value,
                "slot_micro_f1": value,
                "exact_match": value,
                "json_valid_rate": value,
            }
        }

    return {
        "status": status,
        "groups": {"real_only": group(real_only), "real_syn_filtered": group(filtered)},
    }


def test_seed_42_gemma_keeps_the_original_m10_path() -> None:
    """The published seed-42 report must not be relocated by this aggregator."""
    assert report_path("gemma", 42).name == "m10_robustness.json"
    assert report_path("gemma", 43).name == "m16_robustness_gemma_seed_43.json"
    assert report_path("phi4mini", 42).name == "m16_robustness_phi4mini_seed_42.json"


def test_paired_delta_is_computed_within_each_seed() -> None:
    """Averaging per-seed deltas is not the same as differencing two averages
    once seeds differ, and only the former preserves the pairing."""
    summary = summarize_robustness_seeds(
        {
            42: _report(real_only=0.70, filtered=0.74),
            43: _report(real_only=0.60, filtered=0.68),
        },
        target="gemma",
        expected_seeds=(42, 43),
    )

    paired = summary["paired_filtered_minus_real_only"]["exact_match"]
    assert paired["values"] == pytest.approx([0.04, 0.08])
    assert paired["mean"] == pytest.approx(0.06)
    assert summary["seeds"] == [42, 43]
    assert summary["status"] == "complete"


def test_status_is_partial_when_an_expected_seed_has_no_report() -> None:
    """A seed whose file is absent never reaches the function, so without the
    expected-seed list a one-of-three summary would wrongly claim completeness."""
    summary = summarize_robustness_seeds(
        {42: _report(real_only=0.70, filtered=0.74)},
        target="gemma",
        expected_seeds=(42, 43, 44),
    )

    assert summary["status"] == "partial"
    assert summary["seeds"] == [42]
    assert summary["seeds_missing_report"] == [43, 44]


def test_incomplete_seeds_are_excluded_and_recorded() -> None:
    summary = summarize_robustness_seeds(
        {
            42: _report(real_only=0.70, filtered=0.74),
            43: _report(real_only=0.0, filtered=0.0, status="running"),
        },
        target="gemma",
    )

    assert summary["seeds"] == [42]
    assert summary["seeds_skipped"] == [43]
    assert summary["status"] == "partial"
    # The excluded seed must not drag the mean toward zero.
    assert summary["groups"]["real_only"]["exact_match"]["mean"] == pytest.approx(0.70)


def test_single_seed_reports_no_spread() -> None:
    """One observation carries no spread; reporting 0.0 would imply certainty."""
    summary = summarize_robustness_seeds(
        {42: _report(real_only=0.70, filtered=0.74)}, target="gemma"
    )

    assert summary["groups"]["real_only"]["exact_match"]["sample_std"] is None
    assert summary["paired_filtered_minus_real_only"]["exact_match"]["mean"] == (
        pytest.approx(0.04)
    )


def test_markdown_renders_without_spread() -> None:
    summary = summarize_robustness_seeds(
        {42: _report(real_only=0.70, filtered=0.74)}, target="gemma"
    )
    text = render_markdown(summary)

    assert "Robustness across seeds — gemma" in text
    assert "evaluation-only" in text.lower()
    assert "—" in text  # the undefined sample SD renders as a dash, not 0.00%
