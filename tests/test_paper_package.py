from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PAPER = REPO_ROOT / "paper" / "formosanlu_synth.tex"
BIBLIOGRAPHY = REPO_ROOT / "paper" / "references.bib"
BUILD_README = REPO_ROOT / "paper" / "README.md"


def _json(relative: str) -> dict:
    return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))


def test_paper_package_files_exist() -> None:
    assert PAPER.is_file()
    assert BIBLIOGRAPHY.is_file()
    assert BUILD_README.is_file()


def test_paper_contains_required_sections() -> None:
    tex = PAPER.read_text(encoding="utf-8")
    for section in (
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
    ):
        assert rf"\section{{{section}}}" in tex


def test_paper_preserves_the_m19_negative_result() -> None:
    tex = PAPER.read_text(encoding="utf-8")

    assert "single seed" in tex.lower()
    assert "2.5 percentage points" in tex
    assert "does not support a recipe-level causal claim" in tex


def test_paper_headline_values_match_tracked_reports() -> None:
    tex = PAPER.read_text(encoding="utf-8")
    paired = _json("reports/m14_paired_statistics.json")
    replication = _json("reports/m15_cross_model_replication.json")
    ablation = _json("reports/m19_ablation.json")
    resources = _json("reports/m12_resource_ledger.json")

    paired_metrics = paired["hierarchical_bootstrap"]["metrics"]
    expected = {
        "3,754",
        f"{paired_metrics['intent_accuracy']['mean_delta_percentage_points']:+.2f}",
        f"{paired_metrics['exact_match']['mean_delta_percentage_points']:+.2f}",
        f"{replication['metrics']['intent_accuracy']['phi']['mean_delta_percentage_points']:+.2f}",
        f"{replication['metrics']['exact_match']['phi']['mean_delta_percentage_points']:+.2f}",
        f"{resources['measured_total_local_gpu_hours']:.3f}",
        f"{resources['gpu_tdp_total_energy_upper_bound_kwh']:.3f}",
    }
    expected.update(
        f"{group['delta_vs_control_percentage_points']['exact_match']:+.2f}"
        for group in ablation["groups"]
        if group["group"] != ablation["control_group"]
    )

    assert expected.issubset(set(tex.split()))


def test_bibliography_uses_primary_sources_and_official_model_cards() -> None:
    bibliography = BIBLIOGRAPHY.read_text(encoding="utf-8")

    for key in (
        "fitzgerald2023massive",
        "hu2022lora",
        "dettmers2023qlora",
        "wang2023selfinstruct",
        "gemma4modelcard",
        "phi4minimodelcard",
    ):
        assert "{" + key + "," in bibliography
    assert "aclanthology.org/2023.acl-long.235" in bibliography
    assert "openreview.net/forum?id=nZeVKeeFYf9" in bibliography
    assert "papers.nips.cc/paper/2023/hash/1feb87871436031bdc0f2beaa62a049b" in bibliography
    assert "aclanthology.org/2023.acl-long.754" in bibliography
    assert "huggingface.co/google/gemma-4-E4B-it" in bibliography
    assert "huggingface.co/microsoft/Phi-4-mini-instruct" in bibliography


def test_build_readme_documents_reproducible_external_build() -> None:
    instructions = BUILD_README.read_text(encoding="utf-8")

    assert "no TeX engine is installed locally" in instructions
    assert "technical report, not a peer-reviewed publication" in instructions
    assert "tracked reports are authoritative" in instructions
    commands = (
        "pdflatex formosanlu_synth.tex",
        "bibtex formosanlu_synth",
        "pdflatex formosanlu_synth.tex",
        "pdflatex formosanlu_synth.tex",
    )
    assert "\n".join(commands) in instructions
