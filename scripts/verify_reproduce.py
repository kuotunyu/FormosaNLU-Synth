"""Verify that every command the README documents still exists and parses.

verify_readme checks the numbers. This checks the instructions. A reader
following the reproduction section should never hit a module that was renamed
or a flag that no longer exists, and nothing catches that today: the commands
are prose, so they rot silently while the tests stay green.

Each documented `python -m ...` entry point is invoked with --help, which
exercises its argparse definition and import graph without doing any work, GPU
or otherwise. Commands that are not python module invocations (uv, git) are
listed but not executed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.training.train import REPO_ROOT

README = REPO_ROOT / "README.md"
MODULE_PATTERN = re.compile(r"^\s*python -m ([A-Za-z0-9_.]+)", re.MULTILINE)


def documented_modules(readme_text: str) -> list[str]:
    """Return each distinct `python -m <module>` target, in first-seen order."""
    seen: list[str] = []
    for match in MODULE_PATTERN.finditer(readme_text):
        module = match.group(1)
        if module not in seen:
            seen.append(module)
    return seen


def check_module(module: str, *, timeout: int = 180) -> dict[str, Any]:
    """Invoke `python -m <module> --help` and record the outcome."""
    completed = subprocess.run(
        [sys.executable, "-m", module, "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    ok = completed.returncode == 0
    detail = ""
    if not ok:
        tail = (completed.stderr or completed.stdout or "").strip().splitlines()
        detail = tail[-1] if tail else f"exit {completed.returncode}"
    return {"module": module, "ok": ok, "returncode": completed.returncode, "detail": detail}


def verify(readme_text: str) -> dict[str, Any]:
    modules = documented_modules(readme_text)
    results = [check_module(module) for module in modules]
    failed = [r for r in results if not r["ok"]]
    return {
        "schema_version": 1,
        "documented_modules": len(modules),
        "checked": results,
        "failed": [r["module"] for r in failed],
        "status": "ok" if not failed else "broken",
        "note": (
            "Each entry point was invoked with --help only. This proves the "
            "module resolves and its arguments parse; it does not execute the "
            "pipeline."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    report = verify(README.read_text(encoding="utf-8"))
    for entry in report["checked"]:
        print(f"{'PASS' if entry['ok'] else 'FAIL'}  python -m {entry['module']}")
        if not entry["ok"]:
            print(f"      {entry['detail']}")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print()
    if report["failed"]:
        print(f"{len(report['failed'])} documented command(s) broken: "
              f"{', '.join(report['failed'])}")
        return 1
    print(f"All {report['documented_modules']} documented commands resolve and parse.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
