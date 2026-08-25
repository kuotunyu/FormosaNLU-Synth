from __future__ import annotations

from pathlib import Path


def test_find_forbidden_paths_reports_file_and_personal_windows_marker(
    tmp_path: Path,
) -> None:
    from scripts.verify_public_paths import find_forbidden_paths

    tracked_report = tmp_path / "tracked_report.md"
    marker = "C:" + r"\Users\3Hml"
    tracked_report.write_text(
        f"adapter: {marker}\\example\\runs\\adapter\n",
        encoding="utf-8",
    )

    findings = find_forbidden_paths([tracked_report])

    assert any(
        tracked_report.name in finding and marker in finding for finding in findings
    )


def test_find_forbidden_paths_allows_repository_relative_paths(tmp_path: Path) -> None:
    from scripts.verify_public_paths import find_forbidden_paths

    tracked_report = tmp_path / "tracked_report.md"
    tracked_report.write_text(
        "windows: runs\\m15\\seed_42\\adapter\n"
        "posix: runs/m15/seed_42/adapter\n",
        encoding="utf-8",
    )

    assert find_forbidden_paths([tracked_report]) == []
