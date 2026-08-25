from __future__ import annotations

import json
from pathlib import Path

from src.evaluation.run_zeroshot import _write_report
from src.public_paths import LOCAL_ONLY_NOT_PUBLISHED


def test_write_report_uses_portable_adapter_path_in_json_and_markdown(
    tmp_path: Path,
) -> None:
    report_json = tmp_path / "report.json"
    report_markdown = tmp_path / "report.md"
    adapter_dir = tmp_path / "external-adapter"
    records = [
        {
            "raw_prediction": '{"intent":"general_greet","slots":[]}',
            "expected": {"intent": "general_greet", "slots": []},
            "wall_seconds": 1.0,
            "output_tokens": 4,
            "gpu_memory_mib": None,
        }
    ]

    _write_report(
        records,
        target_count=1,
        max_new_tokens=32,
        report_json=report_json,
        report_markdown=report_markdown,
        evaluation_name="External adapter regression",
        evaluation_mode="trained_adapter",
        adapter_dir=adapter_dir,
        group="real_only",
        seed=42,
    )

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    markdown = report_markdown.read_text(encoding="utf-8")

    assert payload["adapter_dir"] == LOCAL_ONLY_NOT_PUBLISHED
    assert f"- Adapter: `{payload['adapter_dir']}`" in markdown
    assert str(adapter_dir) not in markdown
