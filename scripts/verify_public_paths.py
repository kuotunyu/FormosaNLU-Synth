"""Reject personal machine identifiers in tracked UTF-8 text files."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_MARKERS = (
    "C:" "\\Users\\3Hml",
    "/Users/" "3Hml",
    "USER=" "tun2404",
)


def find_forbidden_paths(paths: Iterable[Path]) -> list[str]:
    """Return ``path:line: marker`` findings for UTF-8-decodable files."""
    findings: list[str] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            for marker in FORBIDDEN_MARKERS:
                if marker in line:
                    findings.append(f"{path}:{line_number}: {marker}")
    return findings


def tracked_files() -> list[Path]:
    """Return repository paths reported by ``git ls-files -z``."""
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    return [
        REPO_ROOT / raw_path.decode("utf-8")
        for raw_path in completed.stdout.split(b"\0")
        if raw_path
    ]


def main() -> int:
    findings = find_forbidden_paths(tracked_files())
    for finding in findings:
        print(finding)
    if findings:
        return 1
    print("Public path verification passed: no forbidden markers in tracked text files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
