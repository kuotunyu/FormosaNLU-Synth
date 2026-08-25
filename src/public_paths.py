"""Portable serialization and resolution for repository artifact paths."""

from __future__ import annotations

from pathlib import Path

LOCAL_ONLY_NOT_PUBLISHED = "local_only_not_published"


def public_artifact_path(path: Path | str, *, project_root: Path | str) -> str:
    """Return a POSIX repository path, or mark an external local-only file."""

    root = Path(project_root).resolve()
    candidate = Path(path).resolve()
    try:
        return candidate.relative_to(root).as_posix()
    except (OSError, ValueError):
        return LOCAL_ONLY_NOT_PUBLISHED


def resolve_artifact_path(path: Path | str, *, project_root: Path | str) -> Path:
    """Resolve a public repository-relative path against its repository root."""

    candidate = Path(path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (Path(project_root) / candidate).resolve()
