"""Verify publication-layer invariants for the v1.2.1 closeout."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import tomllib
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
V120_BLOB_PREFIX = "https://github.com/kuotunyu/FormosaNLU-Synth/blob/v1.2.0/"
V120_EVIDENCE_PATHS = {
    "reports/m19_ablation.md",
    "reports/m19_runtime_audit.json",
    "docs/M19_ABLATION_PROTOCOL.md",
    "reports/m12_resource_ledger.json",
    "docs/DECISIONS.md",
}
CANONICAL_MIT = """MIT License

Copyright (c) 2026 kuotunyu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
FENCED_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
REPORT_REFERENCE = re.compile(r"`(reports/[A-Za-z0-9_./-]+\.(?:json|md))`")
DOCUMENTED_GATE_TOKENS = (
    "`ruff`",
    "`pytest`",
    "`scripts.verify_readme`",
    "`scripts.verify_contributors`",
    "`scripts.verify_reproduce`",
    "`scripts.verify_closeout`",
)
ZENODO_CONCEPT_DOI = "10.5281/zenodo.21767492"
TECHNICAL_REPORT_DOI = "10.5281/zenodo.21879155"
TECHNICAL_REPORT_RECORD_URL = "https://zenodo.org/records/21879155"
TECHNICAL_REPORT_EVIDENCE = "reports/v122_technical_report_zenodo.json"
TECHNICAL_REPORT_TITLE = (
    "FormosaNLU-Synth: Filtered Synthetic Data Distillation for Traditional "
    "Chinese (Taiwan) Natural Language Understanding"
)
TECHNICAL_REPORT_FILES = {
    "formosanlu_synth.pdf": (
        65163,
        "md5:525864c3318f5de28242b89a9dc4e285",
    ),
    "formosanlu_synth.tex": (
        16593,
        "md5:059fbf16c13a353ba3caba09a6790712",
    ),
    "references.bib": (
        2756,
        "md5:f7a9161247f4659f730175b1101df298",
    ),
}


@dataclass(frozen=True)
class Check:
    """One closeout requirement and its observed state."""

    name: str
    passed: bool
    observed: str
    expected: str


def _read_text(root: Path, relative: str) -> str | None:
    path = root / relative
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _tracked_markdown(root: Path) -> list[Path]:
    if (root / ".git").exists():
        completed = subprocess.run(
            ["git", "ls-files", "*.md"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if completed.returncode == 0:
            return [
                root / item
                for item in completed.stdout.splitlines()
                if item and (root / item).is_file()
            ]
    excluded = {".git", ".venv", ".pytest_cache", ".ruff_cache", "dist", "outputs"}
    return [path for path in root.rglob("*.md") if excluded.isdisjoint(path.parts)]


def _markdown_link_check(root: Path) -> Check:
    markdown = _tracked_markdown(root)
    missing: list[str] = []
    for source in markdown:
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            missing.append(f"{source.relative_to(root).as_posix()}:unreadable")
            continue
        text = FENCED_CODE_BLOCK.sub("", text)
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().strip("<>").split(maxsplit=1)[0]
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            path_part = target.split("#", maxsplit=1)[0]
            resolved = (source.parent / path_part).resolve()
            if not resolved.exists():
                missing.append(
                    f"{source.relative_to(root).as_posix()} -> {path_part}"
                )
    passed = bool(markdown) and not missing
    observed = "all tracked Markdown links resolve" if passed else ", ".join(missing)
    if not markdown:
        observed = "no Markdown files found"
    return Check(
        "markdown_links",
        passed,
        observed,
        "every tracked local Markdown link resolves relative to its source",
    )


def _v120_release_link_check(root: Path) -> Check:
    text = _read_text(root, "docs/RELEASE_NOTES_v1.2.0.md")
    expected = {f"{V120_BLOB_PREFIX}{path}" for path in V120_EVIDENCE_PATHS}
    observed = set(MARKDOWN_LINK.findall(text or ""))
    matched = {target for target in observed if target.startswith(V120_BLOB_PREFIX)}
    passed = text is not None and matched == expected
    detail = "five absolute tag-pinned links" if passed else repr(sorted(observed))
    return Check(
        "v120_release_links",
        passed,
        detail,
        "the five evidence links are absolute GitHub blob URLs pinned to v1.2.0",
    )


def _next_session_report_check(root: Path) -> Check:
    text = _read_text(root, "docs/NEXT_SESSION.md")
    references = sorted(set(REPORT_REFERENCE.findall(text or "")))
    missing = [reference for reference in references if not (root / reference).is_file()]
    passed = text is not None and not missing
    observed = "all named report paths exist" if passed else ", ".join(missing)
    if text is None:
        observed = "docs/NEXT_SESSION.md missing or unreadable"
    return Check(
        "next_session_reports",
        passed,
        observed,
        "every backtick-quoted reports/*.json or reports/*.md path exists",
    )


def _gate_documentation_check(root: Path) -> Check:
    text = _read_text(root, "README.md") or ""
    missing = [token.strip("`") for token in DOCUMENTED_GATE_TOKENS if token not in text]
    describes_six = "六道檢查" in text
    passed = bool(text) and describes_six and not missing
    observed_parts = []
    if not describes_six:
        observed_parts.append("README does not say 六道檢查")
    if missing:
        observed_parts.append(f"missing: {', '.join(missing)}")
    return Check(
        "gate_documentation",
        passed,
        "all six gates documented" if passed else "; ".join(observed_parts),
        "README names all six scripts.check_gates checks",
    )


def _public_tree_scope_check(root: Path) -> Check:
    internal_root = root / "docs" / "superpowers"
    if (root / ".git").exists():
        completed = subprocess.run(
            ["git", "ls-files", "docs/superpowers"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        internal = (
            [
                item
                for item in completed.stdout.splitlines()
                if item and (root / item).is_file()
            ]
            if completed.returncode == 0
            else []
        )
    elif internal_root.exists():
        internal = sorted(
            path.relative_to(root).as_posix()
            for path in internal_root.rglob("*")
            if path.is_file()
        )
    else:
        internal = []
    return Check(
        "public_tree_scope",
        not internal,
        "no internal process documents tracked" if not internal else ", ".join(internal),
        "docs/superpowers is excluded from the public repository tree",
    )


def _model_license_check(root: Path) -> Check:
    text = _read_text(root, "README.md") or ""
    mixed_claim = "Teacher、judge 與 student weights | Apache-2.0" in text
    has_phi_mit = "microsoft/Phi-4-mini-instruct" in text and "MIT" in text
    has_apache = "Apache-2.0" in text
    passed = bool(text) and not mixed_claim and has_phi_mit and has_apache
    return Check(
        "model_license_language",
        passed,
        "explicit split" if passed else "mixed or incomplete model-license wording",
        "Apache-2.0 roles are distinct from the MIT Phi-4-mini replication model",
    )


def _card_claim_check(root: Path) -> Check:
    card_paths = (
        "hf_cards/dataset_README.md",
        "hf_cards/model_README.md",
    )
    missing: list[str] = []
    required = ("m19", "42.412", "19.085", "single seed")
    for relative in card_paths:
        text = (_read_text(root, relative) or "").lower()
        absent = [token for token in required if token not in text]
        causal_limit = (
            "no recipe-level causal claim" in text
            or "does not support a recipe-level causal claim" in text
        )
        if not causal_limit:
            absent.append("no recipe-level causal claim")
        if absent:
            missing.append(f"{relative}: {', '.join(absent)}")
    phi_card = (_read_text(root, "hf_cards/phi_model_README.md") or "").lower()
    for token in (
        "microsoft/phi-4-mini-instruct",
        "steven0226/phi-4-mini-formosanlu-lora",
        "e9e4c77d79eb12da8cba64a7a484d260f753d000396752f51159e3c0f4e34376",
        "single adapter",
    ):
        if token not in phi_card:
            missing.append(f"hf_cards/phi_model_README.md: {token}")
    passed = not missing
    return Check(
        "hf_card_claims",
        passed,
        "three cards current" if passed else "; ".join(missing),
        "Dataset, Gemma, and Phi cards contain their bounded current claims",
    )


def _version_check(root: Path) -> Check:
    versions: dict[str, str] = {}
    try:
        pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        versions["pyproject"] = str(pyproject["project"]["version"])
    except (KeyError, OSError, tomllib.TOMLDecodeError):
        versions["pyproject"] = "missing_or_invalid"
    try:
        lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
        package = next(item for item in lock["package"] if item.get("name") == "formosanlu")
        versions["uv.lock"] = str(package["version"])
    except (KeyError, OSError, StopIteration, TypeError, tomllib.TOMLDecodeError):
        versions["uv.lock"] = "missing_or_invalid"
    try:
        citation = yaml.safe_load((root / "CITATION.cff").read_text(encoding="utf-8"))
        versions["CITATION.cff"] = str(citation["version"])
    except (KeyError, OSError, TypeError, yaml.YAMLError):
        versions["CITATION.cff"] = "missing_or_invalid"
    expected = versions["pyproject"]
    passed = expected != "missing_or_invalid" and set(versions.values()) == {expected}
    return Check(
        "version_metadata",
        passed,
        repr(versions),
        "pyproject.toml, uv.lock, and CITATION.cff identify one shared version",
    )


def _doi_backlink_check(root: Path) -> Check:
    version = "missing_or_invalid"
    try:
        citation_payload = yaml.safe_load(
            (root / "CITATION.cff").read_text(encoding="utf-8")
        )
        version = str(citation_payload["version"])
    except (KeyError, OSError, TypeError, UnicodeError, yaml.YAMLError):
        citation_payload = {}
    report_name = f"reports/v{version.replace('.', '')}_zenodo.json"
    try:
        report = json.loads((root / report_name).read_text(encoding="utf-8"))
        doi = str(report["doi"])
        doi_url = str(report["doi_url"])
        record_url = str(report["record_url"])
    except (KeyError, OSError, TypeError, UnicodeError, json.JSONDecodeError):
        surfaces = {
            "README.md": _read_text(root, "README.md") or "",
            "CITATION.cff": _read_text(root, "CITATION.cff") or "",
            "docs/HANDOFF.md": _read_text(root, "docs/HANDOFF.md") or "",
            f"docs/RELEASE_NOTES_v{version}.md": (
                _read_text(root, f"docs/RELEASE_NOTES_v{version}.md") or ""
            ),
        }
        missing = [name for name, text in surfaces.items() if ZENODO_CONCEPT_DOI not in text]
        if not missing:
            return Check(
                "doi_backlinks",
                True,
                f"concept DOI {ZENODO_CONCEPT_DOI}; version DOI pending release archive",
                "the concept DOI is present before archiving; exact version DOI after minting",
            )
        return Check(
            "doi_backlinks",
            False,
            f"{report_name} missing or invalid; concept DOI missing from {', '.join(missing)}",
            "the exact minted version DOI appears on every public citation surface",
        )

    missing: list[str] = []
    readme = _read_text(root, "README.md") or ""
    badge_doi = doi.replace("-", "--").replace("/", "%2F")
    badge = (
        "[![DOI](https://img.shields.io/badge/DOI-"
        f"{badge_doi}-1682D4)]({doi_url})"
    )
    if badge not in readme or "## 引用" not in readme or record_url not in readme:
        missing.append("README.md")

    try:
        has_doi = str(citation_payload.get("doi", "")) == doi
    except (AttributeError, TypeError):
        has_doi = False
    if not has_doi:
        missing.append("CITATION.cff")

    for relative in ("docs/HANDOFF.md", f"docs/RELEASE_NOTES_v{version}.md"):
        text = _read_text(root, relative) or ""
        if doi not in text or record_url not in text:
            missing.append(relative)

    return Check(
        "doi_backlinks",
        not missing,
        f"exact DOI {doi} on all surfaces" if not missing else ", ".join(missing),
        "the exact minted version DOI appears on every public citation surface",
    )


def _technical_report_archive_check(root: Path) -> Check:
    try:
        report = json.loads(
            (root / TECHNICAL_REPORT_EVIDENCE).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError):
        return Check(
            "technical_report_archive",
            False,
            f"{TECHNICAL_REPORT_EVIDENCE} missing or invalid",
            "the public Technical note and its three anonymously verified files are pinned",
        )

    missing: list[str] = []
    expected_fields = {
        "status": "public_verified",
        "anonymous_verification": True,
        "downloads_verified": True,
        "doi": TECHNICAL_REPORT_DOI,
        "doi_url": f"https://doi.org/{TECHNICAL_REPORT_DOI}",
        "record_url": TECHNICAL_REPORT_RECORD_URL,
        "creator_names": ["kuotunyu"],
        "resource_type": "publication-technicalnote",
        "license": "cc-by-4.0",
        "language": "eng",
        "related_software_doi": "10.5281/zenodo.21879133",
    }
    for field, expected in expected_fields.items():
        if report.get(field) != expected:
            missing.append(f"evidence:{field}")

    observed_files: dict[str, tuple[object, object]] = {}
    files = report.get("files")
    if isinstance(files, list):
        for item in files:
            if isinstance(item, dict) and isinstance(item.get("key"), str):
                observed_files[item["key"]] = (item.get("size"), item.get("checksum"))
    if observed_files != TECHNICAL_REPORT_FILES:
        missing.append("evidence:files")

    surfaces = {
        "README.md": _read_text(root, "README.md") or "",
        "docs/HANDOFF.md": _read_text(root, "docs/HANDOFF.md") or "",
        "docs/RELEASE_NOTES_v1.2.2.md": (
            _read_text(root, "docs/RELEASE_NOTES_v1.2.2.md") or ""
        ),
    }
    for relative, text in surfaces.items():
        if TECHNICAL_REPORT_DOI not in text or TECHNICAL_REPORT_RECORD_URL not in text:
            missing.append(relative)

    try:
        citation = yaml.safe_load((root / "CITATION.cff").read_text(encoding="utf-8"))
        preferred = citation.get("preferred-citation", {})
        citation_has_doi = isinstance(preferred, dict) and {
            "authors": preferred.get("authors"),
            "doi": str(preferred.get("doi", "")),
            "title": str(preferred.get("title", "")),
            "type": str(preferred.get("type", "")),
            "url": str(preferred.get("url", "")),
            "year": preferred.get("year"),
        } == {
            "authors": [{"name": "kuotunyu"}],
            "doi": TECHNICAL_REPORT_DOI,
            "title": TECHNICAL_REPORT_TITLE,
            "type": "generic",
            "url": f"https://doi.org/{TECHNICAL_REPORT_DOI}",
            "year": 2026,
        }
    except (AttributeError, OSError, TypeError, UnicodeError, yaml.YAMLError):
        citation_has_doi = False
    if not citation_has_doi:
        missing.append("CITATION.cff")

    paper = _read_text(root, "paper/formosanlu_synth.tex") or ""
    if TECHNICAL_REPORT_DOI not in paper:
        missing.append("paper/formosanlu_synth.tex")

    return Check(
        "technical_report_archive",
        not missing,
        (
            f"Technical note {TECHNICAL_REPORT_DOI} and three files pinned"
            if not missing
            else ", ".join(missing)
        ),
        "the public Technical note and its three anonymously verified files are pinned",
    )


def _license_scope_check(root: Path) -> Check:
    license_text = (_read_text(root, "LICENSE") or "").replace("\r\n", "\n")
    notice = _read_text(root, "THIRD_PARTY_NOTICES.md") or ""
    passed = license_text == CANONICAL_MIT and "SCOPE NOTE" in notice
    return Check(
        "license_scope",
        passed,
        "canonical MIT plus separate notice" if passed else "license or notice mismatch",
        "LICENSE is canonical MIT and THIRD_PARTY_NOTICES.md carries the scope note",
    )


def _paper_check(root: Path) -> Check:
    tex = _read_text(root, "paper/formosanlu_synth.tex") or ""
    bibliography = _read_text(root, "paper/references.bib") or ""
    instructions = _read_text(root, "paper/README.md") or ""
    pdf = root / "paper/formosanlu_synth.pdf"
    sections = (
        "Introduction",
        "Related Work",
        "Method",
        "Experimental Design",
        "Results",
        "Robustness",
        "Cross-Family Replication",
        "Equal-N Recipe Ablation",
        "Limitations",
        "Ethics and Licensing",
        "Resource Accounting",
        "Reproducibility",
    )
    missing = [section for section in sections if f"\\section{{{section}}}" not in tex]
    for token in ("3,754", "+4.14", "+3.86", "42.412", "19.085"):
        if token not in tex:
            missing.append(token)
    lower = tex.lower()
    if "single seed" not in lower:
        missing.append("single seed")
    if "2.5 percentage points" not in lower:
        missing.append("2.5 percentage points")
    if "does not support a recipe-level causal claim" not in lower:
        missing.append("causal limitation")
    if "steven0226/phi-4-mini-formosanlu-lora" not in tex:
        missing.append("public Phi adapter")
    if not pdf.is_file() or pdf.stat().st_size <= 0:
        missing.append("paper/formosanlu_synth.pdf")
    passed = bool(tex and bibliography and instructions) and not missing
    return Check(
        "paper_package",
        passed,
        "paper package complete" if passed else ", ".join(missing or ["files missing"]),
        "the English paper package contains every required section and bounded claim",
    )


def collect_checks(repo_root: Path = REPO_ROOT) -> list[Check]:
    """Return every closeout check without performing a network request."""
    return [
        _markdown_link_check(repo_root),
        _v120_release_link_check(repo_root),
        _next_session_report_check(repo_root),
        _gate_documentation_check(repo_root),
        _public_tree_scope_check(repo_root),
        _model_license_check(repo_root),
        _card_claim_check(repo_root),
        _version_check(repo_root),
        _doi_backlink_check(repo_root),
        _technical_report_archive_check(repo_root),
        _license_scope_check(repo_root),
        _paper_check(repo_root),
    ]


def main() -> int:
    checks = collect_checks()
    for check in checks:
        result = "PASS" if check.passed else "FAIL"
        print(f"{result}  {check.name}: {check.observed}")
    failed = [check.name for check in checks if not check.passed]
    if failed:
        print(f"\n{len(failed)} closeout check(s) failed: {', '.join(failed)}")
        return 1
    print(f"\nAll {len(checks)} closeout checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
