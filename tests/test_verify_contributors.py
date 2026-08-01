from __future__ import annotations

from scripts.verify_contributors import (
    CommitIdentity,
    audit_history,
    parse_git_log,
)


def _record(**overrides: str) -> CommitIdentity:
    values = {
        "commit": "a" * 40,
        "author_name": "kuotunyu",
        "author_email": "61350295+kuotunyu@users.noreply.github.com",
        "committer_name": "kuotunyu",
        "committer_email": "61350295+kuotunyu@users.noreply.github.com",
        "body": "M8: safe commit",
    }
    values.update(overrides)
    return CommitIdentity(**values)


def test_parse_and_audit_current_identity() -> None:
    record = _record()
    raw = "\x1f".join(
        [
            record.commit,
            record.author_name,
            record.author_email,
            record.committer_name,
            record.committer_email,
            record.body,
        ]
    )
    assert parse_git_log(raw + "\x1e") == [record]
    assert audit_history([record]) == []


def test_audit_rejects_other_identity_and_coauthor_trailer() -> None:
    errors = audit_history(
        [
            _record(
                author_name="someone-else",
                body="M8: unsafe\n\nCo-Authored-By: Other <other@example.com>",
            )
        ]
    )
    assert any("unexpected author name" in error for error in errors)
    assert any("co-author trailer" in error for error in errors)


def test_unset_local_config_returns_none_instead_of_raising(monkeypatch) -> None:
    """A fresh clone has no repo-local identity; that is an answer, not a crash.

    `git config --local --get` exits 1 when the key is unset, and treating that
    as an exception made the audit traceback for every third party.
    """
    import subprocess

    import scripts.verify_contributors as module

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 1, "", "not set"),
    )

    assert module._git_optional("config", "--local", "user.name") is None


def test_present_local_config_is_returned_stripped(monkeypatch) -> None:
    import subprocess

    import scripts.verify_contributors as module

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 0, "kuotunyu\n", ""),
    )

    assert module._git_optional("config", "--local", "user.name") == "kuotunyu"
