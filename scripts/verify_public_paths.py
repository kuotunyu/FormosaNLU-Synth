"""Reject known personal machine paths in every tracked UTF-8 text file."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_ACCOUNT_FRAGMENTS = ("3", "Hml")
_LOGIN_FRAGMENTS = ("tun", "2404")
_ANACONDA_FRAGMENTS = ("ana", "conda3")


class PublicPathScanError(RuntimeError):
    """Raised when complete tracked-tree coverage cannot be established."""


@dataclass(frozen=True)
class ScanResult:
    findings: tuple[str, ...]
    files_scanned: int
    skipped_binary: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not self.findings


def _marker_patterns() -> tuple[tuple[str, tuple[str, ...]], ...]:
    account = "".join(_ACCOUNT_FRAGMENTS).casefold()
    login = "".join(_LOGIN_FRAGMENTS).casefold()
    anaconda = "".join(_ANACONDA_FRAGMENTS).casefold()
    return (
        ("private-windows-home", (f"c:/users/{account}",)),
        ("private-anaconda-home", (f"d:/{anaconda}",)),
        (
            "private-posix-home",
            (
                f"/users/{account}",
                f"/home/{account}",
                f"/mnt/c/users/{account}",
                f"/c/users/{account}",
            ),
        ),
        ("private-user-marker", (f"user={login}",)),
    )


def _normalized(text: str) -> str:
    return re.sub(r"\\+", "/", text).casefold()


def _display_path(path: Path, root: Path | None) -> str:
    if root is not None:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            pass
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return path.name


def _read_utf8_text(path: Path) -> str | None:
    content = path.read_bytes()
    if b"\0" in content:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _find_in_text(display_path: str, text: str) -> list[str]:
    findings: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        normalized = _normalized(line)
        for marker, patterns in _marker_patterns():
            if any(pattern in normalized for pattern in patterns):
                findings.append(f"{display_path}:{line_number}: {marker}")
                break
    return findings


def find_forbidden_paths(
    paths: Iterable[Path], *, root: Path | None = None
) -> list[str]:
    """Return sanitized ``path:line: kind`` findings for UTF-8 text files."""

    findings: list[str] = []
    for path in paths:
        text = _read_utf8_text(path)
        if text is None:
            continue
        display_path = _display_path(path, root)
        findings.extend(_find_in_text(display_path, text))
    return findings


def tracked_files(root: Path = REPO_ROOT) -> list[Path]:
    """Return paths from Git's tracked-file index or fail closed."""

    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached"],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise PublicPathScanError("git ls-files failed; tracked-tree coverage is unknown")
    try:
        relative_paths = completed.stdout.decode("utf-8").split("\0")
    except UnicodeDecodeError as error:
        raise PublicPathScanError("git ls-files returned a non-UTF-8 tracked path") from error
    return [root / relative_path for relative_path in relative_paths if relative_path]


def scan_repository(root: Path = REPO_ROOT) -> ScanResult:
    paths = tracked_files(root)
    findings: list[str] = []
    skipped_binary: list[str] = []
    files_scanned = 0
    for path in paths:
        try:
            text = _read_utf8_text(path)
        except OSError as error:
            raise PublicPathScanError(
                f"tracked file could not be read: {_display_path(path, root)}"
            ) from error
        if text is None:
            skipped_binary.append(_display_path(path, root))
        else:
            files_scanned += 1
            findings.extend(_find_in_text(_display_path(path, root), text))
    return ScanResult(
        findings=tuple(findings),
        files_scanned=files_scanned,
        skipped_binary=tuple(skipped_binary),
    )


def main() -> int:
    try:
        result = scan_repository()
    except PublicPathScanError as error:
        print(f"FAIL: {error}")
        return 2
    for finding in result.findings:
        print(finding)
    if result.findings:
        print(f"FAIL: {len(result.findings)} tracked personal-path finding(s).")
        return 1
    print(
        "Public path verification passed: "
        f"{result.files_scanned} tracked UTF-8 files scanned; "
        f"{len(result.skipped_binary)} binary/non-UTF-8 files skipped."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
