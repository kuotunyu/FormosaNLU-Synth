"""Run every pre-push gate in one command.

GitHub Actions used to run these on a clean Linux checkout before each push.
That workflow is no longer part of the published repository, so this script is
the local replacement. Run it before every push; a non-zero exit means at
least one gate failed and the push should not happen.

The gates are deliberately the same four the CI job ran, in the same order:
lint, tests, README number traceability, and the sole-contributor audit.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass

from src.training.train import REPO_ROOT


@dataclass(frozen=True)
class Gate:
    name: str
    description: str
    command: list[str]


def build_gates() -> list[Gate]:
    python = sys.executable
    return [
        Gate(
            name="ruff",
            description="Lint the whole tree",
            command=[python, "-m", "ruff", "check", "."],
        ),
        Gate(
            name="pytest",
            description="Full test suite",
            command=[python, "-m", "pytest", "-q"],
        ),
        Gate(
            name="verify_readme",
            description="Every README number recomputes from tracked reports",
            command=[python, "-m", "scripts.verify_readme"],
        ),
        Gate(
            name="verify_contributors",
            description="Sole-contributor history and identity",
            command=[python, "-m", "scripts.verify_contributors"],
        ),
        Gate(
            name="verify_reproduce",
            description="Every command the README documents still resolves",
            command=[python, "-m", "scripts.verify_reproduce"],
        ),
    ]


def run_gates(*, quiet: bool = False) -> list[tuple[Gate, int]]:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    results: list[tuple[Gate, int]] = []
    for gate in build_gates():
        print(f"--- {gate.name}: {gate.description}")
        completed = subprocess.run(
            gate.command,
            cwd=REPO_ROOT,
            env=environment,
            check=False,
            capture_output=quiet,
            text=True,
        )
        if quiet and completed.returncode != 0:
            # Only surface output for the gate that actually failed.
            sys.stdout.write(completed.stdout or "")
            sys.stderr.write(completed.stderr or "")
        results.append((gate, completed.returncode))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress gate output unless a gate fails.",
    )
    args = parser.parse_args()

    results = run_gates(quiet=args.quiet)
    failed = [gate.name for gate, code in results if code != 0]

    print()
    for gate, code in results:
        print(f"{'PASS' if code == 0 else 'FAIL'}  {gate.name}")
    if failed:
        print(f"\n{len(failed)} gate(s) failed: {', '.join(failed)}. Do not push.")
        return 1
    print(f"\nAll {len(results)} gates passed. Safe to push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
