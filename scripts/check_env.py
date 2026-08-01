"""Run non-destructive environment checks for FormosaNLU.

The shared ``../.env`` file is never opened. Only its existence is reported.
This keeps unattended diagnostics from exposing secrets in logs or model context.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MIN_FREE_DISK_GIB = 100.0
OLLAMA_VERSION_URL = "http://127.0.0.1:11434/api/version"


@dataclass(frozen=True)
class Check:
    """One environment check with machine-readable severity."""

    name: str
    status: str
    detail: str
    required: bool = True


def _command(*args: str, timeout: float = 10.0) -> subprocess.CompletedProcess[str] | None:
    """Run a diagnostic command without invoking a shell."""
    executable = shutil.which(args[0])
    if executable is None:
        return None
    try:
        return subprocess.run(
            [executable, *args[1:]],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _tool_check(name: str, *version_args: str) -> Check:
    result = _command(name, *version_args)
    if result is None:
        return Check(name, "fail", "not found")
    output = (result.stdout or result.stderr).strip().splitlines()
    detail = output[0] if output else f"exit code {result.returncode}"
    status = "pass" if result.returncode == 0 else "fail"
    return Check(name, status, detail)


def _python_check() -> Check:
    version = sys.version_info
    supported = (3, 10) <= version[:2] < (3, 13)
    non_anaconda = (
        "anaconda" not in sys.base_prefix.lower() and "anaconda" not in sys.version.lower()
    )
    detail = (
        f"{version.major}.{version.minor}.{version.micro}; "
        f"base={sys.base_prefix}; non-anaconda={non_anaconda}"
    )
    return Check("python", "pass" if supported and non_anaconda else "fail", detail)


def _torch_check() -> Check:
    try:
        import torch
    except (ImportError, OSError) as exc:
        return Check("torch_cuda", "fail", f"{type(exc).__name__}: {exc}")
    available = torch.cuda.is_available()
    device = torch.cuda.get_device_name(0) if available else "unavailable"
    detail = f"torch {torch.__version__}; CUDA {torch.version.cuda}; device={device}"
    return Check("torch_cuda", "pass" if available else "fail", detail)


def _gpu_check() -> Check:
    result = _command(
        "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    )
    if result is None or result.returncode != 0:
        return Check("gpu", "fail", "nvidia-smi unavailable")
    detail = result.stdout.strip()
    has_4090 = "RTX 4090" in detail
    return Check("gpu", "pass" if has_4090 else "fail", detail or "no GPU returned")


def _ollama_check() -> Check:
    if shutil.which("ollama") is None:
        return Check("ollama_service", "fail", "ollama CLI not found")
    try:
        with urllib.request.urlopen(OLLAMA_VERSION_URL, timeout=3) as response:
            payload: dict[str, Any] = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return Check("ollama_service", "fail", f"not reachable: {type(exc).__name__}")
    version = str(payload.get("version", "unknown"))
    return Check("ollama_service", "pass", f"reachable, version {version}")


def _disk_check() -> Check:
    usage = shutil.disk_usage(REPO_ROOT)
    free_gib = usage.free / (1024**3)
    status = "pass" if free_gib >= MIN_FREE_DISK_GIB else "fail"
    return Check("disk_free", status, f"{free_gib:.1f} GiB")


def _external_env_check() -> Check:
    exists = (REPO_ROOT.parent / ".env").is_file()
    detail = "present (contents not read)" if exists else "absent (contents not read)"
    return Check("external_env", "pass" if exists else "warn", detail, required=False)


def _git_identity_check() -> Check:
    """Report the repo-local commit identity without blocking a fresh clone.

    Sole contributorship is enforced by scripts/verify_contributors, which
    audits the commit history and runs as a pre-push gate. Requiring a matching
    local identity here would make the first documented step of the
    reproduction fail for everyone who is not the author, which is the wrong
    trade: the identity matters for committing to this repository, not for
    running the pipeline.
    """
    name_result = _command("git", "config", "--local", "--get", "user.name")
    email_result = _command("git", "config", "--local", "--get", "user.email")
    name = name_result.stdout.strip() if name_result and name_result.returncode == 0 else ""
    email = email_result.stdout.strip() if email_result and email_result.returncode == 0 else ""
    if name == "kuotunyu" and email:
        return Check("git_identity", "pass", f"{name} <{email}>", required=False)
    observed = f"{name or '<unset>'} <{email or 'unset'}>"
    detail = (
        f"{observed}; fine for reproducing. Committing to this repository "
        "additionally requires the maintainer identity, which "
        "verify_contributors enforces."
    )
    return Check("git_identity", "warn", detail, required=False)


def run_checks() -> list[Check]:
    """Collect all M0 environment checks."""
    return [
        _python_check(),
        _torch_check(),
        _tool_check("uv", "--version"),
        _tool_check("git", "--version"),
        _tool_check("git", "lfs", "version"),
        _gpu_check(),
        _ollama_check(),
        _disk_check(),
        _external_env_check(),
        _git_identity_check(),
    ]


def _print_human(checks: list[Check]) -> None:
    icons = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}
    width = max(len(check.name) for check in checks)
    for check in checks:
        print(f"[{icons[check.status]}] {check.name:<{width}}  {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args()
    checks = run_checks()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], ensure_ascii=False, indent=2))
    else:
        _print_human(checks)
    return int(any(check.required and check.status == "fail" for check in checks))


if __name__ == "__main__":
    raise SystemExit(main())
