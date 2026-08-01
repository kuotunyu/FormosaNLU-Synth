"""Guarded runner for the M19 equal-N per-recipe ablation.

Five groups, identical synthetic row counts, one seed. Design and the
preregistered detectability limits are in docs/M19_ABLATION_PROTOCOL.md; read
that before interpreting any output.

Training and evaluation reuse the frozen contract unchanged. Only the
composition of the synthetic rows differs between groups.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.gpu_safety import assert_safe_gpu_launch, safety_status
from src.training.ablation import ABLATION_GROUPS, build_plan
from src.training.train import DEFAULT_CONFIG, REPO_ROOT

SEED = 42
CONFIRMATION = "M19-ABLATION-5GROUPS-4090"
BATCH_REPORT = REPO_ROOT / "runs" / "m19" / "batch_report.json"


def run_dir(group: str) -> Path:
    return REPO_ROOT / "runs" / "m19" / group / f"seed_{SEED}"


def eval_paths(group: str) -> dict[str, Path]:
    return {
        "output": REPO_ROOT / "results" / "m19" / f"{group}_seed_{SEED}.jsonl",
        "report_json": REPO_ROOT / "reports" / "m19" / f"{group}_seed_{SEED}.json",
        "report_markdown": REPO_ROOT / "reports" / "m19" / f"{group}_seed_{SEED}.md",
    }


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _eval_complete(group: str) -> bool:
    report = eval_paths(group)["report_json"]
    if not report.is_file():
        return False
    payload = json.loads(report.read_text(encoding="utf-8"))
    return payload.get("status") == "complete" and payload.get("completed") == 2_974


def _train_complete(group: str) -> bool:
    return (run_dir(group) / "adapter").is_dir()


def _run(command: list[str], environment: dict[str, str]) -> int:
    return subprocess.run(
        command, cwd=REPO_ROOT, env=environment, check=False
    ).returncode


def execute(*, config: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "status": "running",
        "seed": SEED,
        "plan": build_plan(seed=SEED),
        "runs": [],
    }
    _write(BATCH_REPORT, payload)
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"

    for group in ABLATION_GROUPS:
        row: dict[str, Any] = {"group": group, "status": "pending"}
        payload["runs"].append(row)
        _write(BATCH_REPORT, payload)

        if not _train_complete(group):
            assert_safe_gpu_launch()
            row["status"] = "training"
            row["train_started_at"] = datetime.now(timezone.utc).isoformat()
            _write(BATCH_REPORT, payload)
            code = _run(
                [
                    sys.executable, "-m", "src.training.train",
                    "--group", group,
                    "--seed", str(SEED),
                    "--config", str(config),
                    "--output-dir", str(run_dir(group)),
                    "--resume",
                ],
                environment,
            )
            row["train_returncode"] = code
            if not _train_complete(group):
                row["status"] = "train_failed"
                _write(BATCH_REPORT, payload)
                break
        else:
            row["status"] = "train_skipped_complete"

        if not _eval_complete(group):
            assert_safe_gpu_launch()
            row["status"] = "evaluating"
            _write(BATCH_REPORT, payload)
            paths = eval_paths(group)
            code = _run(
                [
                    sys.executable, "-m", "src.evaluation.run_adapter",
                    "--group", group,
                    "--seed", str(SEED),
                    "--adapter-dir", str(run_dir(group) / "adapter"),
                    "--output", str(paths["output"]),
                    "--report-json", str(paths["report_json"]),
                    "--report-markdown", str(paths["report_markdown"]),
                    "--config", str(config),
                ],
                environment,
            )
            row["eval_returncode"] = code

        row["status"] = "completed" if _eval_complete(group) else "eval_failed"
        row["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write(BATCH_REPORT, payload)
        if row["status"] == "eval_failed":
            break

    payload["finished_at"] = datetime.now(timezone.utc).isoformat()
    payload["status"] = (
        "complete"
        if all(r["status"] == "completed" for r in payload["runs"])
        and len(payload["runs"]) == len(ABLATION_GROUPS)
        else "failed"
    )
    _write(BATCH_REPORT, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", help=f"Required with --execute: {CONFIRMATION}")
    args = parser.parse_args()

    plan = build_plan(seed=SEED)
    print(
        json.dumps(
            {
                "confirmation": CONFIRMATION,
                "equal_n": plan["equal_n"],
                "groups": {
                    group: {
                        "excluded_recipe": info["excluded_recipe"],
                        "share_removed": round(info["share_removed"], 4),
                        "trained": _train_complete(group),
                        "evaluated": _eval_complete(group),
                    }
                    for group, info in plan["groups"].items()
                },
                "gpu_safety": safety_status(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not args.execute:
        return 0
    if args.confirm != CONFIRMATION:
        raise RuntimeError(f"M19 execution requires exact --confirm {CONFIRMATION}")
    result = execute(config=args.config)
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
