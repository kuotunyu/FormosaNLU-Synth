from __future__ import annotations

import sys

import pytest

from scripts.check_gates import Gate, build_gates, run_gates

# The CI workflow that used to enforce these is no longer tracked, so the gate
# list itself is now the only thing standing between a regression and a push.
# These tests exist so a gate cannot be dropped quietly.
REQUIRED_GATES = {
    "ruff",
    "pytest",
    "verify_readme",
    "verify_contributors",
    "verify_reproduce",
    "verify_closeout",
}


def test_every_required_gate_is_present() -> None:
    assert {gate.name for gate in build_gates()} == REQUIRED_GATES


def test_gates_run_in_the_documented_order() -> None:
    """Lint first, then tests, then the evidence and instruction audits."""
    assert [gate.name for gate in build_gates()] == [
        "ruff",
        "pytest",
        "verify_readme",
        "verify_contributors",
        "verify_reproduce",
        "verify_closeout",
    ]


def test_gates_use_the_current_interpreter() -> None:
    """A gate must not silently run against some other Python on PATH."""
    for gate in build_gates():
        assert gate.command[0] == sys.executable
        assert gate.command[1] == "-m"


def test_every_gate_is_described() -> None:
    for gate in build_gates():
        assert gate.description.strip()


@pytest.mark.filterwarnings("error::pytest.PytestUnhandledThreadExceptionWarning")
def test_quiet_gate_output_is_decoded_as_utf8(monkeypatch) -> None:
    """UTF-8 child output must not be decoded with the Windows ANSI code page."""
    gate = Gate(
        name="unicode",
        description="Emit UTF-8 outside cp950",
        command=[sys.executable, "-c", "print('🚀正體中文')"],
    )
    monkeypatch.setattr("scripts.check_gates.build_gates", lambda: [gate])

    assert run_gates(quiet=True) == [(gate, 0)]
