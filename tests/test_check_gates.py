from __future__ import annotations

import sys

from scripts.check_gates import build_gates

# The CI workflow that used to enforce these is no longer tracked, so the gate
# list itself is now the only thing standing between a regression and a push.
# These tests exist so a gate cannot be dropped quietly.
REQUIRED_GATES = {"ruff", "pytest", "verify_readme", "verify_contributors"}


def test_every_required_gate_is_present() -> None:
    assert {gate.name for gate in build_gates()} == REQUIRED_GATES


def test_gates_run_in_the_documented_order() -> None:
    """Lint first, then tests, then the two evidence audits."""
    assert [gate.name for gate in build_gates()] == [
        "ruff",
        "pytest",
        "verify_readme",
        "verify_contributors",
    ]


def test_gates_use_the_current_interpreter() -> None:
    """A gate must not silently run against some other Python on PATH."""
    for gate in build_gates():
        assert gate.command[0] == sys.executable
        assert gate.command[1] == "-m"


def test_every_gate_is_described() -> None:
    for gate in build_gates():
        assert gate.description.strip()
