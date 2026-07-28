from __future__ import annotations

import json

from scripts.release_preflight import _json_status, render_markdown


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
