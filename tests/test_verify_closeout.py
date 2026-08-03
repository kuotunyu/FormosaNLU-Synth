from __future__ import annotations

import json
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
        "doi_backlinks",
        "v120_release_links",
        "next_session_reports",
        "model_license_language",
        "version_metadata",
        "license_scope",
    }
    failed = {check.name for check in collect_checks() if not check.passed}

    assert failed.isdisjoint(required)


def test_rejects_missing_doi_backlinks(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    docs = tmp_path / "docs"
    reports.mkdir()
    docs.mkdir()
    (reports / "v121_zenodo.json").write_text(
        json.dumps(
            {
                "doi": "10.5281/zenodo.12345678",
                "doi_url": "https://doi.org/10.5281/zenodo.12345678",
                "record_url": "https://zenodo.org/records/12345678",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
    (tmp_path / "CITATION.cff").write_text(
        "cff-version: 1.2.0\nversion: 1.2.1\nidentifiers: []\n",
        encoding="utf-8",
    )
    (docs / "HANDOFF.md").write_text("No DOI yet.\n", encoding="utf-8")
    (docs / "RELEASE_NOTES_v1.2.1.md").write_text(
        "No DOI yet.\n",
        encoding="utf-8",
    )

    check = _check(tmp_path, "doi_backlinks")

    assert check.passed is False
    assert "README.md" in check.observed
    assert "CITATION.cff" in check.observed


def test_accepts_exact_doi_backlinks(tmp_path: Path) -> None:
    doi = "10.5281/zenodo.12345678"
    doi_url = f"https://doi.org/{doi}"
    record_url = "https://zenodo.org/records/12345678"
    reports = tmp_path / "reports"
    docs = tmp_path / "docs"
    reports.mkdir()
    docs.mkdir()
    (reports / "v121_zenodo.json").write_text(
        json.dumps(
            {"doi": doi, "doi_url": doi_url, "record_url": record_url}
        ),
        encoding="utf-8",
    )
    badge = (
        "[![DOI](https://img.shields.io/badge/DOI-"
        f"{doi.replace('-', '--').replace('/', '%2F')}-1682D4)]({doi_url})"
    )
    (tmp_path / "README.md").write_text(
        f"{badge}\n## 引用\n{record_url}\n",
        encoding="utf-8",
    )
    (tmp_path / "CITATION.cff").write_text(
        "cff-version: 1.2.0\n"
        "version: 1.2.1\n"
        f"identifiers:\n  - type: doi\n    value: {doi}\n",
        encoding="utf-8",
    )
    (docs / "HANDOFF.md").write_text(
        f"{doi}\n{record_url}\n",
        encoding="utf-8",
    )
    (docs / "RELEASE_NOTES_v1.2.1.md").write_text(
        f"{doi}\n{record_url}\n",
        encoding="utf-8",
    )

    assert _check(tmp_path, "doi_backlinks").passed is True


def test_rejects_fragile_zenodo_svg_badge(tmp_path: Path) -> None:
    doi = "10.5281/zenodo.12345678"
    doi_url = f"https://doi.org/{doi}"
    record_url = "https://zenodo.org/records/12345678"
    reports = tmp_path / "reports"
    docs = tmp_path / "docs"
    reports.mkdir()
    docs.mkdir()
    (reports / "v121_zenodo.json").write_text(
        json.dumps(
            {"doi": doi, "doi_url": doi_url, "record_url": record_url}
        ),
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        f"[![DOI](https://zenodo.org/badge/DOI/{doi}.svg)]({doi_url})\n"
        f"## 引用\n{record_url}\n",
        encoding="utf-8",
    )
    (tmp_path / "CITATION.cff").write_text(
        "cff-version: 1.2.0\n"
        "version: 1.2.1\n"
        f"identifiers:\n  - type: doi\n    value: {doi}\n",
        encoding="utf-8",
    )
    (docs / "HANDOFF.md").write_text(f"{doi}\n{record_url}\n", encoding="utf-8")
    (docs / "RELEASE_NOTES_v1.2.1.md").write_text(
        f"{doi}\n{record_url}\n",
        encoding="utf-8",
    )

    check = _check(tmp_path, "doi_backlinks")

    assert check.passed is False
    assert "README.md" in check.observed


def test_markdown_link_check_ignores_fenced_code_examples(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```python\nfixture = '[example](missing.md)'\n```\n",
        encoding="utf-8",
    )

    assert _check(tmp_path, "markdown_links").passed is True


def test_repository_closeout_checks_pass() -> None:
    failed = [check for check in collect_checks() if not check.passed]

    assert failed == []
