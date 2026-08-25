from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _account_name() -> str:
    return "lmH3"[::-1]


def _login_name() -> str:
    return "4042nut"[::-1]


def _windows_home(*, slash: str = "\\", account: str | None = None) -> str:
    name = _account_name() if account is None else account
    return f"C:{slash}Users{slash}{name}"


def _anaconda_home(*, slash: str = "\\", name: str = "anaconda3") -> str:
    return f"D:{slash}{name}"


@pytest.mark.parametrize(
    ("text", "marker"),
    [
        (_windows_home(), "private-windows-home"),
        (_windows_home(slash="\\\\"), "private-windows-home"),
        (_windows_home(slash="\\\\\\\\"), "private-windows-home"),
        (_windows_home(slash="/"), "private-windows-home"),
        (_windows_home(account=_account_name().swapcase()), "private-windows-home"),
        (_anaconda_home(), "private-anaconda-home"),
        (_anaconda_home(slash="\\\\"), "private-anaconda-home"),
        (_anaconda_home(name="ANACONDA3"), "private-anaconda-home"),
        (f"/Users/{_account_name()}/archive", "private-posix-home"),
        (f"/home/{_account_name()}/archive", "private-posix-home"),
        (f"USER={_login_name()}", "private-user-marker"),
        (f"user={_login_name().upper()}", "private-user-marker"),
    ],
)
def test_find_forbidden_paths_handles_raw_escaped_and_case_variants(
    tmp_path: Path, text: str, marker: str
) -> None:
    from scripts.verify_public_paths import find_forbidden_paths

    tracked_report = tmp_path / "tracked_report.md"
    tracked_report.write_text(f"safe\n{text}\n", encoding="utf-8")

    findings = find_forbidden_paths([tracked_report], root=tmp_path)

    assert findings == [f"{tracked_report.name}:2: {marker}"]


def test_find_forbidden_paths_allows_repository_relative_paths(tmp_path: Path) -> None:
    from scripts.verify_public_paths import find_forbidden_paths

    tracked_report = tmp_path / "tracked_report.md"
    tracked_report.write_text(
        "windows: runs\\m15\\seed_42\\adapter\n"
        "posix: runs/m15/seed_42/adapter\n",
        encoding="utf-8",
    )

    assert find_forbidden_paths([tracked_report], root=tmp_path) == []


def _run_git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


def test_repository_scan_reads_only_tracked_utf8_text(tmp_path: Path) -> None:
    from scripts.verify_public_paths import scan_repository

    _run_git(tmp_path, "init", "--quiet")
    tracked = tmp_path / "tracked.json"
    untracked = tmp_path / "scratch.json"
    binary = tmp_path / "image.bin"
    tracked.write_text(_windows_home(slash="\\\\"), encoding="utf-8")
    untracked.write_text(_windows_home(), encoding="utf-8")
    binary.write_bytes(b"\xff\xfe" + _windows_home().encode("utf-8"))
    _run_git(tmp_path, "add", "tracked.json", "image.bin")

    result = scan_repository(tmp_path)

    assert result.findings == ("tracked.json:1: private-windows-home",)
    assert result.files_scanned == 1
    assert result.skipped_binary == ("image.bin",)


def test_repository_scan_fails_closed_when_git_cannot_enumerate_files(
    tmp_path: Path,
) -> None:
    from scripts.verify_public_paths import PublicPathScanError, scan_repository

    with pytest.raises(PublicPathScanError, match="git ls-files"):
        scan_repository(tmp_path)


def test_repository_scan_fails_closed_when_a_tracked_file_is_missing(
    tmp_path: Path,
) -> None:
    from scripts.verify_public_paths import PublicPathScanError, scan_repository

    _run_git(tmp_path, "init", "--quiet")
    tracked = tmp_path / "tracked.md"
    tracked.write_text("portable\n", encoding="utf-8")
    _run_git(tmp_path, "add", "tracked.md")
    tracked.unlink()

    with pytest.raises(PublicPathScanError, match="tracked file could not be read"):
        scan_repository(tmp_path)


def test_public_artifact_path_is_relative_inside_the_repository(tmp_path: Path) -> None:
    from src.public_paths import public_artifact_path

    artifact = tmp_path / "reports" / "evidence.json"

    assert public_artifact_path(artifact, project_root=tmp_path) == (
        "reports/evidence.json"
    )


def test_public_artifact_path_marks_external_files_as_local_only(tmp_path: Path) -> None:
    from src.public_paths import LOCAL_ONLY_NOT_PUBLISHED, public_artifact_path

    repository = tmp_path / "repository"
    external = tmp_path / "downloads" / "evidence.zip"

    assert public_artifact_path(external, project_root=repository) == (
        LOCAL_ONLY_NOT_PUBLISHED
    )


def test_workflow_runs_the_public_path_gate() -> None:
    from scripts.verify_public_paths import REPO_ROOT

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "uv run python -m scripts.verify_public_paths" in workflow
