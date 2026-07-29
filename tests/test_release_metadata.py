from __future__ import annotations

from pathlib import Path

import tomllib
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_public_release_metadata_is_versioned() -> None:
    citation = yaml.safe_load((REPO_ROOT / "CITATION.cff").read_text(encoding="utf-8"))
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert citation["version"] == "1.0.0"
    assert citation["authors"] == [{"name": "kuotunyu"}]
    assert pyproject["project"]["version"] == "1.0.0"


def test_data_card_has_no_pre_release_placeholders() -> None:
    data_card = (REPO_ROOT / "docs" / "data_card.md").read_text(encoding="utf-8")

    assert "Both remain pre-release artifacts" not in data_card
    assert "CC BY 4.0 (planned" not in data_card
    assert "while the dataset remains pre-release" not in data_card


def test_ci_runs_quality_evidence_and_contributor_gates() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "ruff check ." in workflow
    assert "uv run pytest" in workflow
    assert "scripts.verify_readme" in workflow
    assert "scripts/verify_contributors.py" in workflow
