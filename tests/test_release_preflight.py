from __future__ import annotations

import json

from scripts.release_preflight import (
    _f7_release_status,
    _json_status,
    _sha256,
    render_markdown,
)


def test_json_status_handles_missing_invalid_and_status(tmp_path) -> None:
    missing = tmp_path / "missing.json"
    invalid = tmp_path / "invalid.json"
    complete = tmp_path / "complete.json"
    invalid.write_text("{", encoding="utf-8")
    complete.write_text(json.dumps({"status": "complete"}), encoding="utf-8")
    assert _json_status(missing) == "missing"
    assert _json_status(invalid) == "invalid"
    assert _json_status(complete) == "complete"


def test_markdown_marks_nonblocking_failure_as_info() -> None:
    markdown = render_markdown(
        {
            "status": "blocked",
            "checks": [
                {
                    "name": "remote_not_created_early",
                    "passed": False,
                    "observed": "origin",
                    "requirement": "none",
                    "blocking": False,
                }
            ],
        }
    )
    assert "| `remote_not_created_early` | INFO | origin |" in markdown


def test_f7_release_status_recomputes_rows_and_hashes(tmp_path) -> None:
    source = tmp_path / "source.jsonl"
    judge = tmp_path / "judge.jsonl"
    release = tmp_path / "release.jsonl"
    report = tmp_path / "report.json"
    source.write_text('{"id":1}\n{"id":2}\n', encoding="utf-8")
    judge.write_text('{"accepted":true}\n', encoding="utf-8")
    release.write_text('{"id":1}\n', encoding="utf-8")

    report.write_text(
        json.dumps(
            {
                "status": "complete",
                "source": "source.jsonl",
                "source_rows": 2,
                "source_sha256": _sha256(source),
                "judge_results": "judge.jsonl",
                "judge_rows": 1,
                "judge_results_sha256": _sha256(judge),
                "release_output": "release.jsonl",
                "release_rows": 1,
                "release_sha256": _sha256(release),
            }
        ),
        encoding="utf-8",
    )
    assert _f7_release_status(report, repo_root=tmp_path) == "complete"

    release.write_text('{"id":9}\n', encoding="utf-8")
    assert (
        _f7_release_status(report, repo_root=tmp_path)
        == "release_output_sha256_mismatch"
    )
