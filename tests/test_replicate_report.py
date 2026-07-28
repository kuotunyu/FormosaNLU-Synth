from __future__ import annotations

import json

import pytest

from src.evaluation import replicate_report
from src.evaluation.replicate_report import _summary, render_markdown


def test_summary_uses_sample_standard_deviation_and_t_interval() -> None:
    summary = _summary([0.70, 0.75, 0.80])
    assert summary["n"] == 3
    assert summary["mean"] == pytest.approx(0.75)
    assert summary["sample_std"] == pytest.approx(0.05)
    assert summary["ci95_low"] < summary["mean"] < summary["ci95_high"]


def test_pending_markdown_names_missing_runs() -> None:
    markdown = render_markdown(
        {
            "status": "pending",
            "missing": [
                {
                    "group": "real_syn_filtered",
                    "seed": 43,
                    "path": "ignored",
                }
            ],
        }
    )
    assert "real_syn_filtered" in markdown
    assert "seed 43" in markdown


def test_complete_report_computes_seed_paired_delta(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def report_path(group: str, seed: int):
        return tmp_path / f"{group}_seed_{seed}.json"

    monkeypatch.setattr(replicate_report, "_report_path", report_path)
    for group in replicate_report.GROUPS:
        for seed in replicate_report.SEEDS:
            baseline = 0.70 + 0.01 * (seed - 42)
            value = baseline + (0.03 if group == "real_syn_filtered" else 0.0)
            payload = {
                "evaluation_mode": "trained_adapter",
                "completed": 2_974,
                "target": 2_974,
                "metrics": {
                    metric: value for metric in replicate_report.METRICS
                },
            }
            report_path(group, seed).write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

    summary = replicate_report.build_replicate_summary()
    assert summary["status"] == "complete"
    assert summary["paired_filtered_minus_real_only"]["exact_match"][
        "mean"
    ] == pytest.approx(0.03)
