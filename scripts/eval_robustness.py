"""Inspect or execute a two-group robustness evaluation batch.

The batch is parameterized by *target* (which student family's adapters to
probe) and *seed*. The defaults reproduce the original M10 Gemma seed-42 run
byte for byte, including its report paths and confirmation token.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.gpu_safety import assert_safe_gpu_launch, safety_status
from src.training.train import DEFAULT_CONFIG, REPO_ROOT

GROUPS = ("real_only", "real_syn_filtered")
SEED = 42
CONFIRMATION = "M10-ROBUSTNESS-8922-4090"
DEFAULT_BATCH_REPORT = REPO_ROOT / "results" / "m10_robustness_batch.json"
DEFAULT_COMBINED_REPORT = REPO_ROOT / "reports" / "m10_robustness.json"
PROBE_ROWS = 8_922


@dataclass(frozen=True)
class ProbeTarget:
    """Where one student family's adapters and primary reports live."""

    name: str
    runs_root: Path
    primary_report_root: Path
    results_dir: Path
    reports_dir: Path
    config: Path


GEMMA_TARGET = ProbeTarget(
    name="gemma",
    runs_root=REPO_ROOT / "runs",
    primary_report_root=REPO_ROOT / "reports" / "m9",
    results_dir=REPO_ROOT / "results" / "robustness",
    reports_dir=REPO_ROOT / "reports" / "m10_robustness",
    config=DEFAULT_CONFIG,
)

PHI4MINI_TARGET = ProbeTarget(
    name="phi4mini",
    runs_root=REPO_ROOT / "runs" / "m15" / "phi4mini",
    primary_report_root=REPO_ROOT / "reports" / "m15" / "phi4mini",
    results_dir=REPO_ROOT / "results" / "robustness_phi4mini",
    reports_dir=REPO_ROOT / "reports" / "m16_robustness_phi4mini",
    config=REPO_ROOT / "configs" / "train_phi4mini.yaml",
)

TARGETS: dict[str, ProbeTarget] = {
    GEMMA_TARGET.name: GEMMA_TARGET,
    PHI4MINI_TARGET.name: PHI4MINI_TARGET,
}


def confirmation_token(target: ProbeTarget, seed: int) -> str:
    """Distinct token per (target, seed) so a batch cannot be run by accident."""
    if target is GEMMA_TARGET and seed == SEED:
        return CONFIRMATION
    return f"M16-ROBUSTNESS-{target.name.upper()}-SEED{seed}-{PROBE_ROWS}-4090"


def default_batch_report(target: ProbeTarget, seed: int) -> Path:
    if target is GEMMA_TARGET and seed == SEED:
        return DEFAULT_BATCH_REPORT
    return (
        REPO_ROOT
        / "results"
        / f"m16_robustness_batch_{target.name}_seed_{seed}.json"
    )


def default_combined_report(target: ProbeTarget, seed: int) -> Path:
    if target is GEMMA_TARGET and seed == SEED:
        return DEFAULT_COMBINED_REPORT
    return REPO_ROOT / "reports" / f"m16_robustness_{target.name}_seed_{seed}.json"


@dataclass(frozen=True)
class ProbeSpec:
    group: str
    seed: int
    adapter_dir: Path
    output: Path
    primary_report: Path
    report_json: Path
    report_markdown: Path


def build_plan(
    *,
    target: ProbeTarget = GEMMA_TARGET,
    seed: int = SEED,
) -> list[ProbeSpec]:
    return [
        ProbeSpec(
            group=group,
            seed=seed,
            adapter_dir=target.runs_root / group / f"seed_{seed}" / "adapter",
            output=target.results_dir / f"{group}_seed_{seed}.jsonl",
            primary_report=(
                target.primary_report_root / f"{group}_seed_{seed}.json"
            ),
            report_json=target.reports_dir / f"{group}_seed_{seed}.json",
            report_markdown=target.reports_dir / f"{group}_seed_{seed}.md",
        )
        for group in GROUPS
    ]


def _report_complete(spec: ProbeSpec) -> bool:
    if not spec.report_json.is_file():
        return False
    payload = json.loads(spec.report_json.read_text(encoding="utf-8"))
    return (
        payload.get("status") == "complete"
        and payload.get("group") == spec.group
        and payload.get("seed") == spec.seed
        and payload.get("completed") == PROBE_ROWS
    )


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _command(spec: ProbeSpec, config: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "src.evaluation.run_probe",
        "--group",
        spec.group,
        "--seed",
        str(spec.seed),
        "--adapter-dir",
        str(spec.adapter_dir),
        "--output",
        str(spec.output),
        "--primary-report",
        str(spec.primary_report),
        "--report-json",
        str(spec.report_json),
        "--report-markdown",
        str(spec.report_markdown),
        "--config",
        str(config),
    ]


def _combined_report(specs: list[ProbeSpec]) -> dict[str, Any]:
    missing = [spec.group for spec in specs if not _report_complete(spec)]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending" if missing else "complete",
        "groups": {},
        "missing_groups": missing,
        "evaluation_only": True,
    }
    for spec in specs:
        if _report_complete(spec):
            payload["groups"][spec.group] = json.loads(
                spec.report_json.read_text(encoding="utf-8")
            )
    return payload


def execute(
    *,
    config: Path,
    batch_report: Path,
    combined_report: Path,
    target: ProbeTarget = GEMMA_TARGET,
    seed: int = SEED,
) -> dict[str, Any]:
    specs = build_plan(target=target, seed=seed)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "status": "running",
        "target": target.name,
        "seed": seed,
        "runs": [],
    }
    _write(batch_report, payload)
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    for spec in specs:
        row = {
            **asdict(spec),
            "adapter_dir": str(spec.adapter_dir),
            "output": str(spec.output),
            "primary_report": str(spec.primary_report),
            "report_json": str(spec.report_json),
            "report_markdown": str(spec.report_markdown),
            "status": "pending",
        }
        payload["runs"].append(row)
        if _report_complete(spec):
            row["status"] = "skipped_complete"
            _write(batch_report, payload)
            continue
        assert_safe_gpu_launch()
        row["status"] = "running"
        row["started_at"] = datetime.now(timezone.utc).isoformat()
        _write(batch_report, payload)
        completed = subprocess.run(
            _command(spec, config),
            cwd=REPO_ROOT,
            check=False,
            env=environment,
        )
        row["finished_at"] = datetime.now(timezone.utc).isoformat()
        row["returncode"] = completed.returncode
        row["status"] = "completed" if _report_complete(spec) else "failed"
        _write(batch_report, payload)
        if row["status"] == "failed":
            break
    combined = _combined_report(specs)
    _write(combined_report, combined)
    payload["finished_at"] = datetime.now(timezone.utc).isoformat()
    payload["status"] = "complete" if combined["status"] == "complete" else "failed"
    _write(batch_report, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=sorted(TARGETS), default=GEMMA_TARGET.name)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--batch-report", type=Path, default=None)
    parser.add_argument("--combined-report", type=Path, default=None)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--confirm",
        help="Required with --execute; the token is printed by a dry run.",
    )
    args = parser.parse_args()

    target = TARGETS[args.target]
    seed = args.seed
    config = args.config if args.config is not None else target.config
    batch_report = (
        args.batch_report
        if args.batch_report is not None
        else default_batch_report(target, seed)
    )
    combined_report = (
        args.combined_report
        if args.combined_report is not None
        else default_combined_report(target, seed)
    )
    expected_token = confirmation_token(target, seed)

    specs = build_plan(target=target, seed=seed)
    print(
        json.dumps(
            {
                "target": target.name,
                "seed": seed,
                "config": str(config),
                "confirmation": expected_token,
                "batch_report": str(batch_report),
                "combined_report": str(combined_report),
                "runs": [
                    {
                        "group": spec.group,
                        "seed": spec.seed,
                        "complete": _report_complete(spec),
                        "adapter_present": spec.adapter_dir.is_dir(),
                        "primary_report_present": spec.primary_report.is_file(),
                        "output": str(spec.output),
                    }
                    for spec in specs
                ],
                "gpu_safety": safety_status(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not args.execute:
        return 0
    if args.confirm != expected_token:
        raise RuntimeError(
            f"Robustness execution requires exact --confirm {expected_token}"
        )
    result = execute(
        config=config,
        batch_report=batch_report,
        combined_report=combined_report,
        target=target,
        seed=seed,
    )
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
