from __future__ import annotations

import subprocess

import scripts.check_env as check_env


def _fake_config(values: dict[str, str]):
    """Stand in for `git config --local --get <key>`."""

    def runner(*command: str):
        key = command[-1]
        if key in values:
            return subprocess.CompletedProcess(command, 0, values[key], "")
        return subprocess.CompletedProcess(command, 1, "", "")

    return runner


def test_fresh_clone_without_local_identity_does_not_fail(monkeypatch) -> None:
    """The first documented reproduction step must work for a third party.

    A clone has no repo-local git identity, and a stranger's identity will never
    match the maintainer's. Failing here would block everyone but the author
    from step one.
    """
    monkeypatch.setattr(check_env, "_command", _fake_config({}))

    result = check_env._git_identity_check()

    assert result.status == "warn"
    assert result.required is False
    assert "verify_contributors" in result.detail


def test_someone_elses_identity_is_reported_but_not_fatal(monkeypatch) -> None:
    monkeypatch.setattr(
        check_env,
        "_command",
        _fake_config({"user.name": "someone", "user.email": "a@example.com"}),
    )

    result = check_env._git_identity_check()

    assert result.status == "warn"
    assert result.required is False
    assert "someone" in result.detail


def test_maintainer_identity_passes(monkeypatch) -> None:
    monkeypatch.setattr(
        check_env,
        "_command",
        _fake_config(
            {"user.name": "kuotunyu", "user.email": "61350295+kuotunyu@users.noreply.github.com"}
        ),
    )

    result = check_env._git_identity_check()

    assert result.status == "pass"
    assert "kuotunyu" in result.detail


def test_environment_checks_do_not_hard_fail_on_a_clean_checkout() -> None:
    """No check that a fresh clone cannot satisfy may be marked required."""
    optional_by_design = {"external_env", "git_identity"}
    for check in check_env.run_checks():
        if check.name in optional_by_design:
            assert check.required is False, f"{check.name} must not block a clone"
