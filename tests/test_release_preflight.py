from __future__ import annotations

import json
import sys

from scripts.release_preflight import (
    EXPECTED_DEMO_UTTERANCES,
    EXPECTED_REPLICATE_GROUPS,
    EXPECTED_REPLICATE_SEEDS,
    _f7_release_status,
    _json_status,
    _m11_evidence_status,
    _replicate_summary_status,
    _robustness_status,
    _run,
    _sha256,
    _three_value_summary,
    _tree_sha256,
    render_markdown,
)
from src.evaluation.report import METRICS


def test_json_status_handles_missing_invalid_and_status(tmp_path) -> None:
    missing = tmp_path / "missing.json"
    invalid = tmp_path / "invalid.json"
    complete = tmp_path / "complete.json"
    invalid.write_text("{", encoding="utf-8")
    complete.write_text(json.dumps({"status": "complete"}), encoding="utf-8")
    assert _json_status(missing) == "missing"
    assert _json_status(invalid) == "invalid"
    assert _json_status(complete) == "complete"


def test_subprocess_runner_forces_utf8_child_output(monkeypatch) -> None:
    """The UTF-8 decoder requires the child process to emit UTF-8 too."""
    monkeypatch.setenv("PYTHONUTF8", "0")
    result = _run(
        [
            sys.executable,
            "-c",
            "import sys; print(sys.flags.utf8_mode); print('正體中文')",
        ]
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == ["1", "正體中文"]


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


def test_markdown_records_verified_public_release() -> None:
    markdown = render_markdown(
        {
            "status": "public_verified",
            "external_actions_performed": True,
            "checks": [],
        }
    )
    assert "public GitHub, dataset, and model release" in markdown


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
    assert _f7_release_status(report, repo_root=tmp_path) == "release_output_sha256_mismatch"


def test_m11_evidence_status_validates_real_rows_and_adapter(tmp_path) -> None:
    adapter = tmp_path / "runs" / "real_syn_filtered" / "seed_42" / "adapter"
    adapter.mkdir(parents=True)
    (adapter / "adapter.bin").write_bytes(b"adapter")
    prediction = {
        "raw": '{"intent":"play_music","slots":[]}',
        "intent": "play_music",
        "slots": [],
        "valid": True,
        "error": None,
        "latency_ms": 12.5,
    }
    report = tmp_path / "m11.json"
    report.write_text(
        json.dumps(
            {
                "status": "complete",
                "runtime_mode": "real",
                "model": "google/gemma-4-E4B-it",
                "adapter_dir": str(adapter),
                "adapter_tree_sha256": _tree_sha256(adapter),
                "unconstrained_decoding": True,
                "comparisons": [
                    {
                        "utterance": utterance,
                        "base": prediction,
                        "adapted": prediction,
                    }
                    for utterance in EXPECTED_DEMO_UTTERANCES
                ],
            }
        ),
        encoding="utf-8",
    )
    assert _m11_evidence_status(report, repo_root=tmp_path) == "complete"

    (adapter / "adapter.bin").write_bytes(b"changed")
    assert _m11_evidence_status(report, repo_root=tmp_path) == "adapter_sha256_mismatch"


def test_replicate_summary_status_recomputes_all_seed_statistics(tmp_path) -> None:
    metrics_by_group: dict[str, dict[int, dict[str, float]]] = {}
    for group in EXPECTED_REPLICATE_GROUPS:
        metrics_by_group[group] = {}
        for seed in EXPECTED_REPLICATE_SEEDS:
            offset = 0.03 if group == "real_syn_filtered" else 0.0
            metrics = {metric: 0.60 + 0.01 * (seed - 42) + offset for metric in METRICS}
            metrics_by_group[group][seed] = metrics
            path = tmp_path / "reports" / "m9" / f"{group}_seed_{seed}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "evaluation_mode": "trained_adapter",
                        "group": group,
                        "seed": seed,
                        "target": 2_974,
                        "completed": 2_974,
                        "metrics": metrics,
                    }
                ),
                encoding="utf-8",
            )

    summary_metrics = {}
    for group in EXPECTED_REPLICATE_GROUPS:
        summary_metrics[group] = {}
        for metric in METRICS:
            values = [metrics_by_group[group][seed][metric] for seed in EXPECTED_REPLICATE_SEEDS]
            summary_metrics[group][metric] = {
                "by_seed": {
                    str(seed): value
                    for seed, value in zip(EXPECTED_REPLICATE_SEEDS, values, strict=True)
                },
                **_three_value_summary(values),
            }
    paired = {}
    for metric in METRICS:
        values = [
            metrics_by_group["real_syn_filtered"][seed][metric]
            - metrics_by_group["real_only"][seed][metric]
            for seed in EXPECTED_REPLICATE_SEEDS
        ]
        paired[metric] = {
            "by_seed": {
                str(seed): value
                for seed, value in zip(EXPECTED_REPLICATE_SEEDS, values, strict=True)
            },
            **_three_value_summary(values),
        }
    report = tmp_path / "replicates.json"
    payload = {
        "status": "complete",
        "groups": list(EXPECTED_REPLICATE_GROUPS),
        "seeds": list(EXPECTED_REPLICATE_SEEDS),
        "missing": [],
        "metrics": summary_metrics,
        "paired_filtered_minus_real_only": paired,
    }
    report.write_text(json.dumps(payload), encoding="utf-8")
    assert _replicate_summary_status(report, repo_root=tmp_path) == "complete"

    payload["metrics"]["real_only"]["exact_match"]["mean"] = 0.0
    report.write_text(json.dumps(payload), encoding="utf-8")
    assert (
        _replicate_summary_status(report, repo_root=tmp_path)
        == "real_only_exact_match_summary_mismatch"
    )


def test_robustness_status_checks_probe_hash_and_group_deltas(tmp_path) -> None:
    probe = tmp_path / "data" / "evaluation" / "robustness_probe.jsonl"
    probe.parent.mkdir(parents=True)
    probe.write_text(
        "".join(
            json.dumps({"id": index, "evaluation_only": True}) + "\n" for index in range(8_922)
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "reports" / "m10_probe_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "status": "ready_not_evaluated",
                "probe_count": 8_922,
                "probe_kinds": {
                    "asr_noise": 2_974,
                    "colloquial": 2_974,
                    "lexical": 2_974,
                },
                "evaluation_only": True,
                "must_not_flow_into_training": True,
                "output_sha256": _sha256(probe),
            }
        ),
        encoding="utf-8",
    )

    groups = {}
    for group in EXPECTED_REPLICATE_GROUPS:
        adapter = tmp_path / "runs" / group / "seed_42" / "adapter"
        adapter.mkdir(parents=True)
        primary_metrics = {"samples": 2_974.0, **dict.fromkeys(METRICS, 0.50)}
        primary = tmp_path / "reports" / "m9" / f"{group}_seed_42.json"
        primary.parent.mkdir(parents=True, exist_ok=True)
        primary.write_text(
            json.dumps(
                {
                    "evaluation_mode": "trained_adapter",
                    "group": group,
                    "seed": 42,
                    "target": 2_974,
                    "completed": 2_974,
                    "metrics": primary_metrics,
                }
            ),
            encoding="utf-8",
        )
        by_kind = {
            kind: {"samples": 2_974.0, **dict.fromkeys(METRICS, score)}
            for kind, score in (
                ("asr_noise", 0.40),
                ("colloquial", 0.45),
                ("lexical", 0.48),
            )
        }
        deltas = {
            kind: {metric: values[metric] - primary_metrics[metric] for metric in METRICS}
            for kind, values in by_kind.items()
        }
        group_report = {
            "status": "complete",
            "evaluation_mode": "trained_adapter_robustness_probe",
            "group": group,
            "seed": 42,
            "adapter_dir": str(adapter),
            "target": 8_922,
            "completed": 8_922,
            "probe_kind_counts": dict.fromkeys(("asr_noise", "colloquial", "lexical"), 2_974),
            "metrics": {"samples": 8_922.0, **dict.fromkeys(METRICS, 0.44)},
            "metrics_by_probe_kind": by_kind,
            "primary_test_metrics": primary_metrics,
            "delta_vs_primary_by_probe_kind": deltas,
            "evaluation_only": True,
        }
        group_path = tmp_path / "reports" / "m10_robustness" / f"{group}_seed_42.json"
        group_path.parent.mkdir(parents=True, exist_ok=True)
        group_path.write_text(json.dumps(group_report), encoding="utf-8")
        groups[group] = group_report

    report = tmp_path / "reports" / "m10_robustness.json"
    payload = {
        "status": "complete",
        "groups": groups,
        "missing_groups": [],
        "evaluation_only": True,
    }
    report.write_text(json.dumps(payload), encoding="utf-8")
    assert _robustness_status(report, repo_root=tmp_path) == "complete"

    groups["real_only"]["delta_vs_primary_by_probe_kind"]["lexical"]["exact_match"] = 99.0
    group_path = tmp_path / "reports" / "m10_robustness" / "real_only_seed_42.json"
    group_path.write_text(json.dumps(groups["real_only"]), encoding="utf-8")
    report.write_text(json.dumps(payload), encoding="utf-8")
    assert (
        _robustness_status(report, repo_root=tmp_path)
        == "real_only_lexical_exact_match_delta_mismatch"
    )
