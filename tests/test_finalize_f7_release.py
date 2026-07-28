from __future__ import annotations

import json

import pytest

from scripts.finalize_f7_release import _wilson_interval, finalize_release


def _write_jsonl(path, rows) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def test_finalize_release_excludes_only_rejected_judged_rows(tmp_path) -> None:
    source = tmp_path / "source.jsonl"
    judge = tmp_path / "judge.jsonl"
    output = tmp_path / "release.jsonl"
    report = tmp_path / "report.json"
    source_rows = [{"sample": {"id": f"syn-{index}"}} for index in range(400)]
    judged_rows = []
    for index in range(376):
        judged_rows.append(
            {
                "sample_id": f"syn-{index}",
                "json_valid": True,
                "selection_stratum": "random" if index < 50 else "hard_negative",
                "verdict": {"accepted": index not in {1, 2, 3}},
            }
        )
    _write_jsonl(source, source_rows)
    _write_jsonl(judge, judged_rows)

    payload = finalize_release(
        source=source,
        judge_results=judge,
        output=output,
        report=report,
    )

    released = [
        json.loads(line)
        for line in output.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert payload["status"] == "complete"
    assert payload["excluded_rows"] == 3
    assert payload["release_rows"] == 397
    assert {row["sample"]["id"] for row in released}.isdisjoint(
        {"syn-1", "syn-2", "syn-3"}
    )
    assert payload["training_contract_unchanged"] is True


def test_finalize_release_rejects_incomplete_audit(tmp_path) -> None:
    source = tmp_path / "source.jsonl"
    judge = tmp_path / "judge.jsonl"
    _write_jsonl(source, [{"sample": {"id": "syn-0"}}])
    _write_jsonl(
        judge,
        [
            {
                "sample_id": "syn-0",
                "json_valid": True,
                "selection_stratum": "random",
                "verdict": {"accepted": True},
            }
        ],
    )
    with pytest.raises(ValueError, match="376 rows"):
        finalize_release(
            source=source,
            judge_results=judge,
            output=tmp_path / "output.jsonl",
            report=tmp_path / "report.json",
        )


def test_wilson_interval_contains_observed_rate() -> None:
    lower, upper = _wilson_interval(3, 50)
    assert lower < 0.06 < upper
    assert lower == pytest.approx(0.02061497034832388)
    assert upper == pytest.approx(0.16217091688838137)
