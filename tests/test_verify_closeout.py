from __future__ import annotations

from pathlib import Path

from scripts.verify_closeout import Check, collect_checks


def _check(root: Path, name: str) -> Check:
    return next(check for check in collect_checks(root) if check.name == name)


def test_collect_checks_reports_missing_inputs_instead_of_raising(tmp_path: Path) -> None:
    checks = collect_checks(tmp_path)

    assert checks
    assert all(isinstance(check, Check) for check in checks)
    assert all(not check.passed for check in checks)


def test_rejects_release_links_that_are_not_absolute_and_tag_pinned(
    tmp_path: Path,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "RELEASE_NOTES_v1.2.0.md").write_text(
        "[evidence](../reports/m19_ablation.md)\n",
        encoding="utf-8",
    )

    check = _check(tmp_path, "v120_release_links")

    assert check.passed is False
    assert "v1.2.0" in check.expected


def test_accepts_the_five_exact_v120_tag_pinned_links(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    prefix = "https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.0/"
    targets = (
        "reports/m19_ablation.md",
        "reports/m19_runtime_audit.json",
        "docs/M19_ABLATION_PROTOCOL.md",
        "reports/m12_resource_ledger.json",
        "docs/DECISIONS.md",
    )
    (docs / "RELEASE_NOTES_v1.2.0.md").write_text(
        "\n".join(f"[{index}]({prefix}{target})" for index, target in enumerate(targets)),
        encoding="utf-8",
    )

    assert _check(tmp_path, "v120_release_links").passed is True


def test_rejects_missing_next_session_report_paths(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "NEXT_SESSION.md").write_text(
        "`reports/m15_cross_model_report.json`\n",
        encoding="utf-8",
    )

    check = _check(tmp_path, "next_session_reports")

    assert check.passed is False
    assert "reports/m15_cross_model_report.json" in check.observed


def test_accepts_next_session_report_paths_that_exist(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    reports = tmp_path / "reports"
    docs.mkdir()
    reports.mkdir()
    (reports / "evidence.json").write_text("{}\n", encoding="utf-8")
    (docs / "NEXT_SESSION.md").write_text(
        "`reports/evidence.json`\n",
        encoding="utf-8",
    )

    assert _check(tmp_path, "next_session_reports").passed is True


def test_rejects_mixed_student_license_claim(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "| Teacher、judge 與 student weights | Apache-2.0 |\n"
        "M15 使用 `microsoft/Phi-4-mini-instruct`（MIT）\n",
        encoding="utf-8",
    )

    check = _check(tmp_path, "model_license_language")

    assert check.passed is False
    assert "Phi-4-mini" in check.expected


def test_accepts_explicit_apache_and_phi_mit_license_language(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "Gemma adapter 與適用的 upstream weights：Apache-2.0。\n"
        "`microsoft/Phi-4-mini-instruct`：MIT。\n",
        encoding="utf-8",
    )

    assert _check(tmp_path, "model_license_language").passed is True


def test_repository_metadata_checks_pass() -> None:
    required = {
        "v120_release_links",
        "next_session_reports",
        "model_license_language",
        "version_metadata",
        "license_scope",
    }
    failed = {check.name for check in collect_checks() if not check.passed}

    assert failed.isdisjoint(required)


def test_markdown_link_check_ignores_fenced_code_examples(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```python\nfixture = '[example](missing.md)'\n```\n",
        encoding="utf-8",
    )

    assert _check(tmp_path, "markdown_links").passed is True
