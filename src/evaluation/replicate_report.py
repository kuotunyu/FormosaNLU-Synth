"""Aggregate the preregistered three-seed real-only versus filtered comparison."""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any

from src.evaluation.report import METRICS
from src.training.train import REPO_ROOT

GROUPS = ("real_only", "real_syn_filtered")
SEEDS = (42, 43, 44)
T_CRITICAL_95_DF2 = 4.302652729696142
DEFAULT_JSON = REPO_ROOT / "reports" / "m9_replicate_summary.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports" / "m9_replicate_summary.md"


def _report_path(group: str, seed: int) -> Path:
    return REPO_ROOT / "reports" / "m9" / f"{group}_seed_{seed}.json"


def _load_complete_report(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        payload.get("evaluation_mode") != "trained_adapter"
        or payload.get("completed") != payload.get("target")
    ):
        return None
    return payload


def _summary(values: list[float]) -> dict[str, float | int]:
    if len(values) != len(SEEDS):
        raise ValueError(f"Three values required for uncertainty summary: {values}")
    mean = statistics.mean(values)
    sample_std = statistics.stdev(values)
    half_width = T_CRITICAL_95_DF2 * sample_std / math.sqrt(len(values))
    return {
        "n": len(values),
        "mean": mean,
        "sample_std": sample_std,
        "ci95_low": mean - half_width,
        "ci95_high": mean + half_width,
    }


def build_replicate_summary() -> dict[str, Any]:
    reports: dict[tuple[str, int], dict[str, Any]] = {}
    missing = []
    for group in GROUPS:
        for seed in SEEDS:
            path = _report_path(group, seed)
            report = _load_complete_report(path)
            if report is None:
                missing.append({"group": group, "seed": seed, "path": str(path)})
            else:
                reports[(group, seed)] = report

    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "pending" if missing else "complete",
        "groups": list(GROUPS),
        "seeds": list(SEEDS),
        "missing": missing,
        "metrics": {},
        "paired_filtered_minus_real_only": {},
        "interpretation_note": (
            "n=3 per group; 95% intervals use Student's t with df=2 and are "
            "descriptive uncertainty estimates, not a broad generalization claim."
        ),
    }
    if missing:
        return payload

    for group in GROUPS:
        payload["metrics"][group] = {}
        for metric in METRICS:
            values = [
                float(reports[(group, seed)]["metrics"][metric]) for seed in SEEDS
            ]
            payload["metrics"][group][metric] = {
                "by_seed": dict(zip((str(seed) for seed in SEEDS), values, strict=True)),
                **_summary(values),
            }
    for metric in METRICS:
        deltas = [
            float(reports[("real_syn_filtered", seed)]["metrics"][metric])
            - float(reports[("real_only", seed)]["metrics"][metric])
            for seed in SEEDS
        ]
        payload["paired_filtered_minus_real_only"][metric] = {
            "by_seed": dict(zip((str(seed) for seed in SEEDS), deltas, strict=True)),
            **_summary(deltas),
        }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# M9 three-seed uncertainty summary",
        "",
        f"Status: **{payload['status']}**",
        "",
    ]
    if payload["status"] != "complete":
        lines.extend(
            [
                "Missing evaluations:",
                "",
                *(
                    f"- `{row['group']}` seed {row['seed']}"
                    for row in payload["missing"]
                ),
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "| Metric | real-only mean ± SD | filtered mean ± SD | "
            "paired Δ mean ± SD | paired Δ 95% CI |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for metric in METRICS:
        real = payload["metrics"]["real_only"][metric]
        filtered = payload["metrics"]["real_syn_filtered"][metric]
        paired = payload["paired_filtered_minus_real_only"][metric]
        lines.append(
            f"| `{metric}` | {real['mean']:.2%} ± {real['sample_std']:.2%} | "
            f"{filtered['mean']:.2%} ± {filtered['sample_std']:.2%} | "
            f"{paired['mean']:+.2%} ± {paired['sample_std']:.2%} | "
            f"[{paired['ci95_low']:+.2%}, {paired['ci95_high']:+.2%}] |"
        )
    lines.extend(["", payload["interpretation_note"], ""])
    return "\n".join(lines)


def write_replicate_summary(
    payload: dict[str, Any],
    *,
    json_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MARKDOWN,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
