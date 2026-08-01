"""Fail unless Git history can attribute every commit only to kuotunyu."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass

ALLOWED_NAME = "kuotunyu"
ALLOWED_EMAILS = frozenset(
    {
        "61350295+kuotunyu@users.noreply.github.com",
        "03131047@gm.scu.edu.tw",
    }
)
REQUIRED_LOCAL_EMAIL = "61350295+kuotunyu@users.noreply.github.com"
TRAILER_PATTERN = re.compile(
    r"^(?:Co-Authored-By|Co-Author|Coauthor)\s*:",
    flags=re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class CommitIdentity:
    commit: str
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str
    body: str


def parse_git_log(raw: str) -> list[CommitIdentity]:
    records = []
    for raw_record in raw.split("\x1e"):
        if not raw_record.strip():
            continue
        fields = raw_record.strip("\r\n").split("\x1f", maxsplit=5)
        if len(fields) != 6:
            raise ValueError("Unexpected git log record")
        records.append(CommitIdentity(*fields))
    return records


def audit_history(records: list[CommitIdentity]) -> list[str]:
    errors = []
    for record in records:
        short = record.commit[:12]
        if record.author_name != ALLOWED_NAME:
            errors.append(f"{short}: unexpected author name {record.author_name!r}")
        if record.committer_name != ALLOWED_NAME:
            errors.append(f"{short}: unexpected committer name {record.committer_name!r}")
        if record.author_email not in ALLOWED_EMAILS:
            errors.append(f"{short}: unexpected author email {record.author_email!r}")
        if record.committer_email not in ALLOWED_EMAILS:
            errors.append(f"{short}: unexpected committer email {record.committer_email!r}")
        if TRAILER_PATTERN.search(record.body):
            errors.append(f"{short}: co-author trailer is forbidden")
    return errors


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout


def _git_optional(*args: str) -> str | None:
    """Run git where a non-zero exit is an expected answer, not a crash.

    `git config --local --get` exits 1 when the key is unset, which is the
    normal state of a fresh clone. Treating that as an exception turned a
    routine situation into a traceback.
    """
    completed = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--history-only",
        action="store_true",
        help="Audit committed identities and trailers without requiring local Git config.",
    )
    args = parser.parse_args()
    raw = _git(
        "log",
        "--all",
        "--format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e",
    )
    records = parse_git_log(raw)
    errors = audit_history(records)
    identity_checked = False
    if not args.history_only:
        local_name = _git_optional("config", "--local", "user.name")
        local_email = _git_optional("config", "--local", "user.email")
        if local_name is None and local_email is None:
            # A fresh clone has no repo-local identity, and a third party's
            # identity would never match this repository's. The history audit
            # above is the claim that matters to them; the local identity guard
            # exists to stop the maintainer committing under the wrong address.
            print(
                "note: no repo-local Git identity, so only the commit history "
                "was audited. Set user.name and user.email locally before "
                "committing to this repository."
            )
        else:
            identity_checked = True
            if local_name != ALLOWED_NAME:
                errors.append(
                    f"local user.name must be {ALLOWED_NAME!r}, got {local_name!r}"
                )
            if local_email != REQUIRED_LOCAL_EMAIL:
                errors.append(
                    f"local user.email must be {REQUIRED_LOCAL_EMAIL!r}, "
                    f"got {local_email!r}"
                )
    if errors:
        print("Contributor audit FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    scope = "history and local identity" if identity_checked else "history"
    print(
        f"Contributor audit passed ({scope}): {len(records)} commits, "
        f"author/committer {ALLOWED_NAME}, no co-author trailers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
