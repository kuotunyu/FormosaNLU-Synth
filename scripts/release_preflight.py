"""Run the CPU-only M13 release audit without publishing anything."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.training.train import REPO_ROOT

DEFAULT_JSON = REPO_ROOT / "runs" / "m13_release_preflight.json"
DEFAULT_MARKDOWN = REPO_ROOT / "logs" / "m13_release_preflight.md"
EXPECTED_NAME = "kuotunyu"
EXPECTED_EMAIL = "61350295+kuotunyu@users.noreply.github.com"


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    observed: str
    requirement: str
    blocking: bool = True


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args])


def _json_status(path: Path) -> str:
    if not path.is_file():
        return "missing"
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("status"))
    except (json.JSONDecodeError, OSError):
        return "invalid"


def _tracked_large_files(limit_bytes: int = 100 * 1024 * 1024) -> list[str]:
    tracked = _git("ls-files")
    if tracked.returncode != 0:
        raise RuntimeError(tracked.stderr.strip() or "git ls-files failed")
    large = []
    for relative in tracked.stdout.splitlines():
        path = REPO_ROOT / relative
        if path.is_file() and path.stat().st_size > limit_bytes:
            large.append(relative)
    return large


def _secret_pattern_count() -> int:
    patterns = r"(hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"
    result = _git("grep", "-I", "-E", patterns, "--", ".")
    if result.returncode not in {0, 1}:
        raise RuntimeError(result.stderr.strip() or "git grep failed")
    return len(result.stdout.splitlines()) if result.returncode == 0 else 0


def collect_checks(*, run_slow_checks: bool = True) -> list[Check]:
    name = _git("config", "--get", "user.name").stdout.strip()
    email = _git("config", "--get", "user.email").stdout.strip()
    contributors = _run(
        [sys.executable, str(REPO_ROOT / "scripts" / "verify_contributors.py")]
    )
    worktree = _git("status", "--porcelain=v1").stdout.strip()
    remotes = _git("remote").stdout.splitlines()
    large = _tracked_large_files()
    secret_count = _secret_pattern_count()

    checks = [
        Check(
            "git_identity",
            name == EXPECTED_NAME and email == EXPECTED_EMAIL,
            f"{name} <{email}>",
            f"{EXPECTED_NAME} <{EXPECTED_EMAIL}>",
        ),
        Check(
            "contributors",
            contributors.returncode == 0,
            (contributors.stdout or contributors.stderr).strip(),
            "only kuotunyu author/committer; no Co-Authored-By trailers",
        ),
        Check(
            "worktree_clean",
            not worktree,
            worktree if worktree else "clean",
            "no uncommitted source or report changes",
        ),
        Check(
            "tracked_file_size",
            not large,
            "all tracked files <= 100 MiB" if not large else ", ".join(large),
            "model weights and generated corpora remain outside Git",
        ),
        Check(
            "tracked_secret_patterns",
            secret_count == 0,
            f"{secret_count} token-like matches",
            "no HF, OpenAI, or GitHub token-shaped strings in tracked files",
        ),
        Check(
            "m10_primary",
            _json_status(REPO_ROOT / "reports" / "m10_main_results.json")
            == "complete",
            _json_status(REPO_ROOT / "reports" / "m10_main_results.json"),
            "primary seven-row report complete",
        ),
        Check(
            "m12_resource_ledger",
            _json_status(REPO_ROOT / "reports" / "m12_resource_ledger.json")
            == "complete_primary_seed_42",
            _json_status(REPO_ROOT / "reports" / "m12_resource_ledger.json"),
            "traceable primary GPU ledger complete",
        ),
        Check(
            "f7_judge",
            _json_status(REPO_ROOT / "reports" / "m6_f7_judge.json") == "complete",
            _json_status(REPO_ROOT / "reports" / "m6_f7_judge.json"),
            "376-row independent judge audit complete",
        ),
        Check(
            "three_seed_uncertainty",
            _json_status(REPO_ROOT / "reports" / "m9_replicate_summary.json")
            == "complete",
            _json_status(REPO_ROOT / "reports" / "m9_replicate_summary.json"),
            "real-only and filtered seeds 42/43/44 summarized",
        ),
        Check(
            "robustness_inference",
            _json_status(REPO_ROOT / "reports" / "m10_robustness.json")
            == "complete",
            _json_status(REPO_ROOT / "reports" / "m10_robustness.json"),
            "8,922-row robustness probe evaluated",
        ),
        Check(
            "real_demo_evidence",
            _json_status(REPO_ROOT / "reports" / "m11_demo_evidence.json")
            == "complete",
            _json_status(REPO_ROOT / "reports" / "m11_demo_evidence.json"),
            "real base-versus-adapter demo evidence captured",
        ),
        Check(
            "colab_portability",
            (
                _json_status(
                    REPO_ROOT
                    / "results"
                    / "colab"
                    / "real_only"
                    / "seed_42"
                    / "run_report.json"
                )
                == "completed"
            ),
            _json_status(
                REPO_ROOT
                / "results"
                / "colab"
                / "real_only"
                / "seed_42"
                / "run_report.json"
            ),
            "one user-operated Colab portability run complete",
        ),
        Check(
            "remote_not_created_early",
            not remotes,
            "none" if not remotes else ", ".join(remotes),
            "no GitHub remote before user approval",
            blocking=False,
        ),
    ]
    if run_slow_checks:
        for check_name, command, requirement in (
            (
                "ruff",
                [sys.executable, "-m", "ruff", "check", "."],
                "all source lint checks pass",
            ),
            (
                "pytest",
                [sys.executable, "-m", "pytest", "-q"],
                "all repository tests pass",
            ),
            (
                "readme_reproducibility",
                [sys.executable, "-m", "scripts.verify_readme"],
                "README numbers reproduce from tracked artifacts",
            ),
        ):
            result = _run(command)
            output = (result.stdout or result.stderr).strip().splitlines()
            checks.append(
                Check(
                    check_name,
                    result.returncode == 0,
                    output[-1] if output else f"returncode={result.returncode}",
                    requirement,
                )
            )
    return checks


def build_report(*, run_slow_checks: bool = True) -> dict[str, Any]:
    checks = collect_checks(run_slow_checks=run_slow_checks)
    blocking = [check for check in checks if check.blocking and not check.passed]
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_user_release_review" if not blocking else "blocked",
        "external_actions_performed": False,
        "checks": [asdict(check) for check in checks],
        "blocking_checks": [check.name for check in blocking],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# M13 release preflight",
        "",
        f"Status: **{payload['status']}**",
        "",
        "| Check | Result | Observed |",
        "| --- | --- | --- |",
    ]
    for check in payload["checks"]:
        result = "PASS" if check["passed"] else "BLOCK"
        if not check["blocking"] and not check["passed"]:
            result = "INFO"
        observed = str(check["observed"]).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{check['name']}` | {result} | {observed} |")
    lines.extend(
        [
            "",
            "No repository, model, or dataset was published by this audit.",
            "",
        ]
    )
    return "\n".join(lines)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--fast", action="store_true", help="Skip Ruff, pytest, README")
    args = parser.parse_args()
    payload = build_report(run_slow_checks=not args.fast)
    _write(args.json, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    _write(args.markdown, render_markdown(payload))
    print(
        f"M13 preflight status={payload['status']}; "
        f"blocking={payload['blocking_checks']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
